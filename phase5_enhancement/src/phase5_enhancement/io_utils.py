"""IO helpers for Phase 5 enhancement."""

from __future__ import annotations

import logging
from pathlib import Path

import soundfile as sf
from mutagen import File as MutagenFile

logger = logging.getLogger(__name__)


def ensure_absolute_path(path: str | Path) -> Path:
    """Return an absolute resolved path."""
    return Path(path).expanduser().resolve()


def validate_audio_file(path: Path) -> None:
    """
    Best-effort audio validation for WAV/MP3 outputs.

    Raises FileNotFoundError or ValueError on invalid audio.
    """
    path = ensure_absolute_path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    try:
        info = sf.info(path)
        if info.frames <= 0 or info.duration <= 0:
            raise ValueError(f"Audio at {path} is empty or corrupt.")
        return
    except Exception as exc:  # noqa: BLE001
        logger.debug("soundfile fallback for %s failed: %s", path, exc)

    audio = MutagenFile(path)
    length = getattr(audio.info, "length", 0) if audio else 0
    if not audio or length <= 0:
        raise ValueError(
            f"Audio validation failed for {path}: unreadable or zero length."
        )


def atomic_replace(target: Path, temp_source: Path) -> None:
    """Move temp_source into target atomically."""
    target = ensure_absolute_path(target)
    temp_source.replace(target)
