"""
Compatibility shims for legacy Phase 3 tests and integrations.

These helpers provide thin wrappers around the current chunking APIs without
changing behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ChunkMetadata:
    """Legacy-compatible metadata wrapper with dot-notation access."""

    id: str
    text: str
    start: float
    end: float
    duration: float
    extra: Dict[str, Any]

    @classmethod
    def from_new_chunk(cls, chunk: Dict[str, Any]) -> "ChunkMetadata":
        """Create a shim instance from the current chunk dictionary."""
        return cls(
            id=chunk.get("id"),
            text=chunk.get("text"),
            start=chunk.get("start", 0.0),
            end=chunk.get("end", 0.0),
            duration=chunk.get(
                "duration", chunk.get("end", 0.0) - chunk.get("start", 0.0)
            ),
            extra={
                k: v
                for k, v in chunk.items()
                if k not in {"id", "text", "start", "end", "duration"}
            },
        )


def _split_oversized_sentence(sentence: str, max_chars: int) -> List[str]:
    """
    Legacy wrapper that delegates to the current word-based splitter.

    Behavior is unchanged; this simply exposes the modern splitter under the
    historical function name expected by older tests.
    """
    from .utils import split_by_words

    return split_by_words(sentence, max_chars=max_chars)
