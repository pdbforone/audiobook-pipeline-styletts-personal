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

import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_MODEL = os.getenv("LLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
CACHE_DIR = Path(".pipeline") / "llm_cache"
CACHE_TTL_HOURS = 24

# Resource thresholds
MIN_RAM_MB = 4000  # Minimum RAM to start LLM
TTS_RAM_RESERVE_MB = 5000  # Reserve for TTS engines


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
    """

    def __init__(self, min_ram_mb: int = MIN_RAM_MB):
        self.min_ram = min_ram_mb
        self._ollama_process = None

    def get_available_ram_mb(self) -> int:
        """Get available RAM in MB."""
        try:
            import psutil
            return int(psutil.virtual_memory().available / (1024 * 1024))
        except ImportError:
            logger.warning("psutil not available, assuming 8GB RAM")
            return 8000

    def check_resources(self) -> ResourceStatus:
        """Check if LLM can run given current resources."""
        available = self.get_available_ram_mb()
        llm_ok = available >= self.min_ram
        tts_ok = available >= TTS_RAM_RESERVE_MB

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

    def start_ollama(self) -> bool:
        """Start Ollama server if not running."""
        if self.is_ollama_running():
            return True

        status = self.check_resources()
        if not status.llm_can_run:
            logger.warning(
                f"Insufficient RAM for LLM: {status.available_ram_mb}MB < {self.min_ram}MB"
            )
            return False

        try:
            # Start Ollama in background
            self._ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Wait for server to start
            for _ in range(10):
                time.sleep(0.5)
                if self.is_ollama_running():
                    logger.info("Ollama server started")
                    return True

            logger.error("Ollama server failed to start")
            return False

        except FileNotFoundError:
            logger.error("Ollama not installed. Run: curl -fsSL https://ollama.ai/install.sh | sh")
            return False
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False

    def stop_ollama(self) -> None:
        """Stop Ollama server to free memory for TTS."""
        if self._ollama_process:
            self._ollama_process.terminate()
            self._ollama_process = None
            logger.info("Ollama server stopped")


class ResponseCache:
    """Simple file-based cache for LLM responses."""

    def __init__(self, cache_dir: Path = CACHE_DIR, ttl_hours: int = CACHE_TTL_HOURS):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
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
            data = json.loads(cache_file.read_text())
            cached_at = datetime.fromisoformat(data["cached_at"])

            if datetime.now() - cached_at > self.ttl:
                cache_file.unlink()
                return None

            return LlamaResponse(
                content=data["content"],
                model=data["model"],
                tokens_used=data.get("tokens_used", 0),
                duration_ms=data.get("duration_ms", 0),
                cached=True,
            )

        except Exception as e:
            logger.debug(f"Cache read error: {e}")
            return None

    def set(self, prompt: str, response: LlamaResponse) -> None:
        """Cache a response."""
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
            cache_file.write_text(json.dumps(data))

        except Exception as e:
            logger.debug(f"Cache write error: {e}")


class LlamaAgent:
    """
    Base agent for local LLM interactions via Ollama.

    Features:
    - Automatic Ollama server management
    - Response caching
    - Graceful degradation on errors
    - Resource-aware execution
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        cache_enabled: bool = True,
        resource_manager: Optional[LlamaResourceManager] = None,
    ):
        self.model = model
        self.cache = ResponseCache() if cache_enabled else None
        self.resource_manager = resource_manager or LlamaResourceManager()
        self._client = None

    def _get_client(self):
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

    def query(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        use_cache: bool = True,
    ) -> LlamaResponse:
        """
        Query the LLM with a prompt.

        Args:
            prompt: The question or instruction
            max_tokens: Maximum response length
            temperature: Creativity (0.0=deterministic, 1.0=creative)
            system_prompt: Optional system message
            use_cache: Whether to use response cache

        Returns:
            LlamaResponse with content or error
        """
        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(prompt, self.model)
            if cached:
                logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return cached

        # Check resources
        status = self.resource_manager.check_resources()
        if not status.llm_can_run:
            return LlamaResponse(
                content="",
                model=self.model,
                error=f"Insufficient RAM: {status.available_ram_mb}MB available",
            )

        # Ensure Ollama is running
        if not self.resource_manager.is_ollama_running():
            if not self.resource_manager.start_ollama():
                return LlamaResponse(
                    content="",
                    model=self.model,
                    error="Failed to start Ollama server",
                )

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Query Ollama
        try:
            client = self._get_client()
            start_time = time.time()

            response = client.chat(
                model=self.model,
                messages=messages,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            )

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
            logger.error(f"Ollama query failed: {e}")
            return LlamaResponse(
                content="",
                model=self.model,
                error=str(e),
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


def get_agent(model: str = DEFAULT_MODEL) -> LlamaAgent:
    """Get or create an agent for the specified model."""
    if model not in _agents:
        _agents[model] = LlamaAgent(
            model=model,
            resource_manager=get_resource_manager(),
        )
    return _agents[model]
