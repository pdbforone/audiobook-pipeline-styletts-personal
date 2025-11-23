"""
Repair Loop - Orchestrates self-healing for pipeline failures.

Provides:
- Automated failure detection
- Strategy-based repair attempts
- Dead chunk recovery
- Patch suggestion and staging

IMPORTANT: No changes are auto-applied. All fixes require human approval.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .log_parser import LogParser, FailureEvent

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_STAGING_DIR = Path(".pipeline/staged_patches")
DEFAULT_ERROR_REGISTRY = Path(".pipeline/error_registry.json")


@dataclass
class RepairAttempt:
    """Record of a repair attempt."""

    strategy: str
    success: bool
    chunk_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ErrorRegistryEntry:
    """Persistent record of a chunk failure."""

    chunk_id: str
    file_id: str
    failure_category: str
    failure_message: str
    attempts: List[RepairAttempt] = field(default_factory=list)
    resolved: bool = False
    resolution: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ErrorRegistry:
    """
    Persistent registry of chunk failures and repair attempts.

    Tracks:
    - Which chunks have failed
    - What repair strategies were tried
    - Which succeeded/failed
    """

    def __init__(self, path: Path = DEFAULT_ERROR_REGISTRY):
        self.path = path
        self.entries: Dict[str, ErrorRegistryEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                for chunk_id, entry_data in data.get("entries", {}).items():
                    self.entries[chunk_id] = ErrorRegistryEntry(
                        chunk_id=entry_data.get("chunk_id", chunk_id),
                        file_id=entry_data.get("file_id", ""),
                        failure_category=entry_data.get("failure_category", "unknown"),
                        failure_message=entry_data.get("failure_message", ""),
                        attempts=[
                            RepairAttempt(**a) for a in entry_data.get("attempts", [])
                        ],
                        resolved=entry_data.get("resolved", False),
                        resolution=entry_data.get("resolution"),
                        created_at=entry_data.get("created_at", ""),
                        updated_at=entry_data.get("updated_at", ""),
                    )
            except Exception as e:
                logger.warning(f"Failed to load error registry: {e}")

    def save(self) -> None:
        """Save registry to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "entries": {
                chunk_id: {
                    "chunk_id": e.chunk_id,
                    "file_id": e.file_id,
                    "failure_category": e.failure_category,
                    "failure_message": e.failure_message,
                    "attempts": [
                        {
                            "strategy": a.strategy,
                            "success": a.success,
                            "chunk_id": a.chunk_id,
                            "timestamp": a.timestamp,
                            "details": a.details,
                            "error": a.error,
                        }
                        for a in e.attempts
                    ],
                    "resolved": e.resolved,
                    "resolution": e.resolution,
                    "created_at": e.created_at,
                    "updated_at": e.updated_at,
                }
                for chunk_id, e in self.entries.items()
            },
        }
        self.path.write_text(json.dumps(data, indent=2))

    def add_failure(
        self,
        chunk_id: str,
        file_id: str,
        category: str,
        message: str,
    ) -> ErrorRegistryEntry:
        """Add or update a failure entry."""
        if chunk_id in self.entries:
            entry = self.entries[chunk_id]
            entry.updated_at = datetime.now().isoformat()
        else:
            entry = ErrorRegistryEntry(
                chunk_id=chunk_id,
                file_id=file_id,
                failure_category=category,
                failure_message=message,
            )
            self.entries[chunk_id] = entry

        self.save()
        return entry

    def add_attempt(
        self,
        chunk_id: str,
        attempt: RepairAttempt,
    ) -> None:
        """Add a repair attempt to an entry."""
        if chunk_id in self.entries:
            self.entries[chunk_id].attempts.append(attempt)
            self.entries[chunk_id].updated_at = datetime.now().isoformat()
            if attempt.success:
                self.entries[chunk_id].resolved = True
                self.entries[chunk_id].resolution = attempt.strategy
            self.save()

    def get_unresolved(self) -> List[ErrorRegistryEntry]:
        """Get all unresolved failures."""
        return [e for e in self.entries.values() if not e.resolved]

    def get_by_category(self, category: str) -> List[ErrorRegistryEntry]:
        """Get failures by category."""
        return [e for e in self.entries.values() if e.failure_category == category]


class DeadChunkRepair:
    """
    Attempts to recover failed chunks through multiple strategies.

    Strategies (tried in order):
    1. Try smaller sub-chunks
    2. Switch to different engine
    3. Rewrite text via LLM
    4. Simplify text (remove complex punctuation)
    """

    def __init__(
        self,
        engine_manager=None,
        llama_rewriter=None,
        error_registry: Optional[ErrorRegistry] = None,
    ):
        self.engine_manager = engine_manager
        self.llama_rewriter = llama_rewriter
        self.registry = error_registry or ErrorRegistry()

    def repair(
        self,
        chunk_id: str,
        file_id: str,
        text: str,
        original_engine: str,
        reference_audio: Optional[Path] = None,
        max_attempts: int = 4,
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to repair a failed chunk.

        Args:
            chunk_id: Chunk identifier
            file_id: Parent file identifier
            text: Chunk text content
            original_engine: Engine that originally failed
            reference_audio: Voice reference audio
            max_attempts: Maximum repair strategies to try

        Returns:
            Dict with audio_path and metadata if successful, None otherwise
        """
        strategies = [
            ("smaller_splits", self._try_smaller_splits),
            ("different_engine", self._try_different_engine),
            ("text_rewrite", self._try_text_rewrite),
            ("simplify_text", self._try_simplify_text),
        ]

        for strategy_name, strategy_fn in strategies[:max_attempts]:
            try:
                logger.info(f"Trying repair strategy '{strategy_name}' for {chunk_id}")

                result = strategy_fn(
                    text=text,
                    original_engine=original_engine,
                    reference_audio=reference_audio,
                )

                attempt = RepairAttempt(
                    strategy=strategy_name,
                    success=result is not None,
                    chunk_id=chunk_id,
                    details=result or {},
                )

                self.registry.add_attempt(chunk_id, attempt)

                if result:
                    logger.info(f"Repair successful: {strategy_name}")
                    return {
                        "audio": result.get("audio"),
                        "audio_path": result.get("audio_path"),
                        "strategy": strategy_name,
                        "engine_used": result.get("engine_used"),
                    }

            except Exception as e:
                logger.warning(f"Strategy '{strategy_name}' failed: {e}")
                self.registry.add_attempt(
                    chunk_id,
                    RepairAttempt(
                        strategy=strategy_name,
                        success=False,
                        chunk_id=chunk_id,
                        error=str(e),
                    ),
                )

        # All strategies failed
        self.registry.add_failure(
            chunk_id=chunk_id,
            file_id=file_id,
            category="unrecoverable",
            message="All repair strategies exhausted",
        )

        return None

    def _try_smaller_splits(
        self,
        text: str,
        original_engine: str,
        reference_audio: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Split chunk into smaller pieces."""
        if not self.engine_manager:
            return None

        # Split into 2-4 smaller chunks
        words = text.split()
        if len(words) < 10:
            return None  # Too small to split

        mid = len(words) // 2
        chunks = [
            " ".join(words[:mid]),
            " ".join(words[mid:]),
        ]

        # Synthesize each sub-chunk
        audios = []
        for sub_text in chunks:
            audio = self.engine_manager.synthesize(
                text=sub_text,
                reference_audio=reference_audio,
                engine=original_engine,
            )
            if audio is None:
                return None
            audios.append(audio)

        # Return combined (caller will concatenate)
        return {
            "audio": audios,
            "engine_used": original_engine,
            "sub_chunks": len(chunks),
        }

    def _try_different_engine(
        self,
        text: str,
        original_engine: str,
        reference_audio: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Try synthesis with a different engine."""
        if not self.engine_manager:
            return None

        # Get fallback engines
        fallbacks = self.engine_manager._get_fallback_order(original_engine)

        for engine in fallbacks:
            try:
                audio = self.engine_manager.synthesize(
                    text=text,
                    reference_audio=reference_audio,
                    engine=engine,
                    fallback=False,  # Don't cascade further
                )
                if audio is not None:
                    return {
                        "audio": audio,
                        "engine_used": engine,
                    }
            except Exception:
                continue

        return None

    def _try_text_rewrite(
        self,
        text: str,
        original_engine: str,
        reference_audio: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Rewrite problematic text using LLM."""
        if not self.llama_rewriter or not self.engine_manager:
            return None

        # Get engine's max chars
        max_chars = self.engine_manager.get_max_chars(original_engine)

        # Use LLM to rewrite
        rewritten = self.llama_rewriter.rewrite_for_tts(
            text=text,
            max_chars=max_chars,
            issues=["synthesis failure", "possible truncation"],
        )

        if not rewritten or len(rewritten) >= len(text):
            return None

        # Try synthesis with rewritten text
        audio = self.engine_manager.synthesize(
            text=rewritten,
            reference_audio=reference_audio,
            engine=original_engine,
        )

        if audio is not None:
            return {
                "audio": audio,
                "engine_used": original_engine,
                "rewritten": True,
            }

        return None

    def _try_simplify_text(
        self,
        text: str,
        original_engine: str,
        reference_audio: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Simplify text by removing complex punctuation."""
        if not self.engine_manager:
            return None

        import re

        # Remove complex punctuation that might confuse TTS
        simplified = text
        simplified = re.sub(r'["""''„‚«»]', '"', simplified)  # Normalize quotes
        simplified = re.sub(r'[—–]', '-', simplified)  # Normalize dashes
        simplified = re.sub(r'\.{3,}', '...', simplified)  # Normalize ellipsis
        simplified = re.sub(r'\s+', ' ', simplified)  # Collapse whitespace

        if simplified == text:
            return None  # No changes made

        audio = self.engine_manager.synthesize(
            text=simplified,
            reference_audio=reference_audio,
            engine=original_engine,
        )

        if audio is not None:
            return {
                "audio": audio,
                "engine_used": original_engine,
                "simplified": True,
            }

        return None


class RepairLoop:
    """
    Main orchestrator for self-healing pipeline repairs.

    Monitors logs, detects failures, and coordinates repair attempts.
    All suggestions require human approval before application.
    """

    def __init__(
        self,
        log_parser: Optional[LogParser] = None,
        dead_chunk_repair: Optional[DeadChunkRepair] = None,
        staging_dir: Path = DEFAULT_STAGING_DIR,
    ):
        self.log_parser = log_parser or LogParser()
        self.dead_chunk_repair = dead_chunk_repair or DeadChunkRepair()
        self.staging_dir = staging_dir
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def scan_logs(
        self,
        log_paths: List[Path],
        max_lines: int = 500,
    ) -> List[FailureEvent]:
        """Scan multiple log files for failures."""
        all_events = []
        for path in log_paths:
            events = self.log_parser.parse_file(path, max_lines=max_lines)
            all_events.extend(events)
        return all_events

    def analyze_and_suggest(
        self,
        events: List[FailureEvent],
        reasoner=None,
    ) -> List[Dict[str, Any]]:
        """
        Analyze failures and generate patch suggestions.

        Returns list of suggestions (not applied, just staged).
        """
        suggestions = []

        for event in events:
            if reasoner:
                # Use LLM-based analysis
                analysis = reasoner.analyze_failure(
                    log_content=event.message,
                    chunk_data={"chunk_id": event.chunk_id},
                    context={"phase": event.phase, "category": event.category},
                )

                patch = reasoner.suggest_patch(analysis)
                patch_file = reasoner.stage_patch(patch, self.staging_dir)

                suggestions.append({
                    "event": event,
                    "analysis": analysis,
                    "patch_file": str(patch_file),
                })
            else:
                # Basic suggestion without LLM
                suggestions.append({
                    "event": event,
                    "suggestion": f"Review {event.category} failure in {event.phase}",
                })

        return suggestions

    def get_repair_summary(self) -> Dict[str, Any]:
        """Get summary of repair attempts and outcomes."""
        registry = self.dead_chunk_repair.registry

        return {
            "total_failures": len(registry.entries),
            "resolved": sum(1 for e in registry.entries.values() if e.resolved),
            "unresolved": len(registry.get_unresolved()),
            "by_category": {
                cat: len(registry.get_by_category(cat))
                for cat in ["oom", "timeout", "truncation", "quality", "unknown"]
            },
            "staged_patches": len(list(self.staging_dir.glob("*.json"))),
        }
