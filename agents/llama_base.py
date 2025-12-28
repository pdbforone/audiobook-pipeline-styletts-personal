"""
Llama Base Agent - Foundation for all local LLM agents.

Provides:
- Ollama client wrapper
- Resource management (RAM awareness)
- Response caching
- Error handling with graceful degradation

Recommended Models (CPU, 16GB RAM):
- llama3.1:8b-instruct-q4_K_M (4.9GB) - Default, excellent quality (RECOMMENDED)
- llama3.2:3b (2.0GB) - Balanced quality/speed, fallback option
- tinyllama (1.1GB) - Ultra-fast, simple tasks only

Usage:
    from agents import LlamaAgent

    agent = LlamaAgent(model="llama3.1:8b-instruct-q4_K_M")
    response = agent.query("Explain quantum physics in one sentence.")
"""

from __future__ import annotations

import atexit
import hashlib
import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_MODEL = os.getenv("LLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
CACHE_DIR = Path(".pipeline") / "llm_cache"
CACHE_TTL_HOURS = 24
DEFAULT_TIMEOUT_SECONDS = 120  # Timeout for LLM queries

# Resource thresholds
MIN_RAM_MB = 4000  # Minimum RAM to start LLM
TTS_RAM_RESERVE_MB = 5000  # Reserve for TTS engines
RAM_BUFFER_MB = 500  # Buffer to account for race conditions


@dataclass
class LlamaResponse:
    """Response from Llama agent."""

    content: str
    model: str
    tokens_used: int = 0
    duration_ms: int = 0
    cached: bool = False
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.content)


@dataclass
class ResourceStatus:
    """Current resource availability."""

    available_ram_mb: int
    llm_can_run: bool
    tts_can_run: bool
    recommended_action: str


class LlamaResourceManager:
    """
    Manages Ollama lifecycle to avoid memory conflicts with TTS.

    Key principle: LLM and TTS never run simultaneously.

    Features:
    - Thread-safe resource checking with locking
    - Automatic cleanup via atexit hook
    - Context manager support for scoped usage
    - Race condition prevention with RAM buffer
    """

    _instances: List["LlamaResourceManager"] = []  # Track all instances for cleanup

    def __init__(self, min_ram_mb: int = MIN_RAM_MB) -> None:
        self.min_ram = min_ram_mb
        self._ollama_process = None
        self._lock = threading.Lock()
        self._started_by_us = False

        # Register for cleanup
        LlamaResourceManager._instances.append(self)

    def __enter__(self) -> "LlamaResourceManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup resources."""
        self.stop_ollama()
        return None

    def get_available_ram_mb(self) -> int:
        """Get available RAM in MB."""
        try:
            import psutil
            return int(psutil.virtual_memory().available / (1024 * 1024))
        except ImportError:
            # Fallback: try reading /proc/meminfo on Linux
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemAvailable:"):
                            return int(line.split()[1]) // 1024  # Convert KB to MB
            except (FileNotFoundError, PermissionError):
                pass
            logger.warning("psutil not available and /proc/meminfo unreadable, assuming 8GB RAM")
            return 8000

    def check_resources(self) -> ResourceStatus:
        """Check if LLM can run given current resources."""
        available = self.get_available_ram_mb()
        # Add buffer to account for RAM changes between check and actual use
        effective_available = available - RAM_BUFFER_MB
        llm_ok = effective_available >= self.min_ram
        tts_ok = effective_available >= TTS_RAM_RESERVE_MB

        if llm_ok and tts_ok:
            action = "both_available"
        elif llm_ok:
            action = "llm_only"
        elif tts_ok:
            action = "tts_only"
        else:
            action = "low_memory"

        return ResourceStatus(
            available_ram_mb=available,
            llm_can_run=llm_ok,
            tts_can_run=tts_ok,
            recommended_action=action,
        )

    def is_ollama_running(self) -> bool:
        """Check if Ollama server is running."""
        try:
            import ollama
            ollama.list()
            return True
        except Exception:
            return False

    def ensure_ollama_ready(self) -> bool:
        """
        Atomically check resources AND start Ollama if needed.

        This prevents race conditions between resource check and startup.
        Thread-safe via internal locking.

        Returns:
            True if Ollama is ready for queries, False otherwise
        """
        with self._lock:
            # Already running? Great!
            if self.is_ollama_running():
                return True

            # Check resources with buffer for safety
            status = self.check_resources()
            if not status.llm_can_run:
                logger.warning(
                    f"Insufficient RAM for LLM: {status.available_ram_mb}MB available, "
                    f"need {self.min_ram + RAM_BUFFER_MB}MB (including {RAM_BUFFER_MB}MB buffer)"
                )
                return False

            # Start Ollama
            return self._start_ollama_locked()

    def _start_ollama_locked(self) -> bool:
        """Internal: Start Ollama (must be called with lock held)."""
        try:
            # Start Ollama in background
            self._ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._started_by_us = True

            # Wait for server to start
            for attempt in range(15):
                time.sleep(0.5)
                if self.is_ollama_running():
                    logger.info("Ollama server started successfully")
                    return True
                # Check if process died
                if self._ollama_process.poll() is not None:
                    logger.error(f"Ollama process exited with code {self._ollama_process.returncode}")
                    self._ollama_process = None
                    return False

            logger.error("Ollama server failed to start within timeout")
            self._force_stop_process()
            return False

        except FileNotFoundError:
            logger.error("Ollama not installed. Run: curl -fsSL https://ollama.ai/install.sh | sh")
            return False
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False

    def start_ollama(self) -> bool:
        """Start Ollama server if not running (legacy method, prefer ensure_ollama_ready)."""
        return self.ensure_ollama_ready()

    def _force_stop_process(self) -> None:
        """Force-stop the Ollama process with escalation."""
        if not self._ollama_process:
            return

        # Try graceful termination first
        try:
            self._ollama_process.terminate()
            try:
                self._ollama_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Escalate to SIGKILL
                logger.warning("Ollama did not terminate gracefully, forcing kill")
                self._ollama_process.kill()
                self._ollama_process.wait(timeout=5)
        except Exception as e:
            logger.warning(f"Error stopping Ollama process: {e}")
        finally:
            self._ollama_process = None

    def stop_ollama(self) -> None:
        """Stop Ollama server to free memory for TTS."""
        with self._lock:
            if self._ollama_process and self._started_by_us:
                self._force_stop_process()
                self._started_by_us = False
                logger.info("Ollama server stopped to free memory for TTS")
            elif self._ollama_process:
                logger.debug("Ollama was not started by us, not stopping")

    @classmethod
    def cleanup_all(cls) -> None:
        """Cleanup all resource manager instances (called on exit)."""
        for instance in cls._instances:
            try:
                instance.stop_ollama()
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")
        cls._instances.clear()


# Register cleanup on interpreter exit
atexit.register(LlamaResourceManager.cleanup_all)


class ResponseCache:
    """
    File-based cache for LLM responses with atomic writes.

    Features:
    - Atomic file writes via temp file + rename
    - Graceful handling of corrupted cache entries
    - Thread-safe operations
    """

    def __init__(self, cache_dir: Path = CACHE_DIR, ttl_hours: int = CACHE_TTL_HOURS) -> None:
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self._lock = threading.Lock()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model."""
        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, prompt: str, model: str) -> Optional[LlamaResponse]:
        """Get cached response if available and fresh."""
        key = self._hash_key(prompt, model)
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with self._lock:
                data = json.loads(cache_file.read_text())

            cached_at = datetime.fromisoformat(data["cached_at"])

            if datetime.now() - cached_at > self.ttl:
                try:
                    cache_file.unlink()
                except OSError:
                    pass
                return None

            return LlamaResponse(
                content=data["content"],
                model=data["model"],
                tokens_used=data.get("tokens_used", 0),
                duration_ms=data.get("duration_ms", 0),
                cached=True,
            )

        except json.JSONDecodeError as e:
            # Corrupted cache - remove and log at WARNING level
            logger.warning(f"Corrupted cache entry {cache_file.name}, removing: {e}")
            try:
                cache_file.unlink()
            except OSError:
                pass
            return None
        except Exception as e:
            logger.debug(f"Cache read error for {key}: {e}")
            return None

    def set(self, prompt: str, response: LlamaResponse) -> None:
        """
        Cache a response using atomic write.

        Uses temp file + rename pattern to prevent partial writes
        that could corrupt the cache.
        """
        key = self._hash_key(prompt, response.model)
        cache_file = self.cache_dir / f"{key}.json"

        try:
            data = {
                "content": response.content,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "duration_ms": response.duration_ms,
                "cached_at": datetime.now().isoformat(),
            }
            json_content = json.dumps(data)

            # Atomic write: write to temp file, then rename
            with self._lock:
                # Create temp file in same directory for atomic rename
                fd, temp_path = tempfile.mkstemp(
                    suffix=".tmp",
                    prefix=f"{key}_",
                    dir=self.cache_dir,
                )
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(json_content)
                    # Atomic rename (on POSIX systems)
                    os.replace(temp_path, cache_file)
                except Exception:
                    # Clean up temp file on error
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                    raise

        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")


class LlamaAgent:
    """
    Base agent for local LLM interactions via Ollama.

    Features:
    - Automatic Ollama server management
    - Response caching
    - Graceful degradation on errors
    - Resource-aware execution
    - Query timeout protection (prevents indefinite hangs)
    - Retry logic with exponential backoff
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        cache_enabled: bool = True,
        resource_manager: Optional[LlamaResourceManager] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = 2,
    ) -> None:
        self.model = model
        self.cache = ResponseCache() if cache_enabled else None
        self.resource_manager = resource_manager or LlamaResourceManager()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llama_query")

    def _get_client(self) -> Any:
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                import ollama
                self._client = ollama
            except ImportError:
                raise RuntimeError(
                    "Ollama not installed. Run: pip install ollama"
                )
        return self._client

    def _execute_query(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """Execute the actual Ollama query (runs in thread pool)."""
        client = self._get_client()
        return client.chat(
            model=self.model,
            messages=messages,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        )

    def query(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        use_cache: bool = True,
        timeout: Optional[int] = None,
    ) -> LlamaResponse:
        """
        Query the LLM with a prompt.

        Args:
            prompt: The question or instruction
            max_tokens: Maximum response length
            temperature: Creativity (0.0=deterministic, 1.0=creative)
            system_prompt: Optional system message
            use_cache: Whether to use response cache
            timeout: Query timeout in seconds (defaults to self.timeout_seconds)

        Returns:
            LlamaResponse with content or error
        """
        effective_timeout = timeout or self.timeout_seconds

        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(prompt, self.model)
            if cached:
                logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return cached

        # Ensure Ollama is ready (atomic resource check + startup)
        if not self.resource_manager.ensure_ollama_ready():
            status = self.resource_manager.check_resources()
            return LlamaResponse(
                content="",
                model=self.model,
                error=f"Ollama not available. RAM: {status.available_ram_mb}MB, need {self.resource_manager.min_ram}MB",
            )

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Query Ollama with timeout and retry
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()

                # Execute query with timeout protection
                future = self._executor.submit(
                    self._execute_query,
                    messages,
                    max_tokens,
                    temperature,
                )

                try:
                    response = future.result(timeout=effective_timeout)
                except FuturesTimeoutError:
                    future.cancel()
                    error_msg = f"Query timed out after {effective_timeout}s"
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.max_retries + 1})")
                    last_error = error_msg
                    # Exponential backoff before retry
                    if attempt < self.max_retries:
                        backoff = min(2 ** attempt, 8)  # Cap at 8 seconds
                        time.sleep(backoff)
                    continue

                duration_ms = int((time.time() - start_time) * 1000)
                content = response["message"]["content"]
                tokens = response.get("eval_count", 0)

                result = LlamaResponse(
                    content=content,
                    model=self.model,
                    tokens_used=tokens,
                    duration_ms=duration_ms,
                )

                # Cache successful response
                if use_cache and self.cache and result.success:
                    self.cache.set(prompt, result)

                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Ollama query failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                # Exponential backoff before retry
                if attempt < self.max_retries:
                    backoff = min(2 ** attempt, 8)
                    time.sleep(backoff)

        # All retries exhausted
        logger.error(f"Ollama query failed after {self.max_retries + 1} attempts: {last_error}")
        return LlamaResponse(
            content="",
            model=self.model,
            error=f"Query failed after {self.max_retries + 1} attempts: {last_error}",
        )

    def query_json(
        self,
        prompt: str,
        max_tokens: int = 1000,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Query LLM and parse response as JSON.

        Returns empty dict on parse failure.
        """
        # Add JSON instruction to prompt
        json_prompt = f"{prompt}\n\nRespond with valid JSON only, no markdown or explanation."

        response = self.query(json_prompt, max_tokens=max_tokens, **kwargs)

        if not response.success:
            return {"error": response.error}

        try:
            # Try to extract JSON from response
            content = response.content.strip()

            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return {"error": f"JSON parse failed: {e}", "raw": response.content}

    def is_available(self) -> bool:
        """Check if the agent is available for queries."""
        status = self.resource_manager.check_resources()
        if not status.llm_can_run:
            return False

        try:
            client = self._get_client()
            models = client.list()
            return any(m["name"].startswith(self.model.split(":")[0]) for m in models.get("models", []))
        except Exception:
            return False


# Singleton instances
_resource_manager: Optional[LlamaResourceManager] = None
_agents: Dict[str, LlamaAgent] = {}


def get_resource_manager() -> LlamaResourceManager:
    """Get shared resource manager instance."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = LlamaResourceManager()
    return _resource_manager


def get_agent(
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = 2,
) -> LlamaAgent:
    """Get or create an agent for the specified model."""
    if model not in _agents:
        _agents[model] = LlamaAgent(
            model=model,
            resource_manager=get_resource_manager(),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
    return _agents[model]


def release_llm_resources() -> None:
    """
    Release LLM resources to free RAM for TTS.

    Call this before starting TTS synthesis to ensure
    Ollama is stopped and memory is freed.
    """
    resource_manager = get_resource_manager()
    resource_manager.stop_ollama()
    logger.info("LLM resources released for TTS")
