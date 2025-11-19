"""Robust file helpers for Phase 3 chunking."""

from __future__ import annotations

from pathlib import Path


def ensure_absolute_path(path: str | Path) -> Path:
    """Resolve a path and expand user/home markers."""
    return Path(path).expanduser().resolve()
