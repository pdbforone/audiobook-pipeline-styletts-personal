"""File-system helpers for Phase 4."""

from __future__ import annotations

import logging
from pathlib import Path

import soundfile as sf

logger = logging.getLogger(__name__)


def ensure_absolute_path(path: str | Path) -> Path:
    """Return a resolved absolute path."""
    return Path(path).expanduser().resolve()


def validate_audio_file(path: Path) -> None:
    """
    Validate that an audio file exists and is readable.

    Raises:
        FileNotFoundError: When the file is missing
        ValueError: When the file is unreadable or empty
    """
    path = ensure_absolute_path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio output missing: {path}")
    try:
        info = sf.info(path)
        if info.frames <= 0 or info.duration <= 0:
            raise ValueError(f"Audio at {path} is empty or corrupt.")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Audio validation failed for {path}: {exc}") from exc
