"""IO helpers for Phase 5 enhancement."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict

import soundfile as sf
from mutagen import File as MutagenFile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from pipeline_common import canonicalize_state, validate_pipeline_schema
except Exception:  # pragma: no cover - defensive fallback when pipeline_common unavailable
    canonicalize_state = lambda payload, **kwargs: payload  # type: ignore

    def validate_pipeline_schema(payload, **kwargs):  # type: ignore
        return None

logger = logging.getLogger(__name__)


def ensure_absolute_path(path: str | Path) -> Path:
    """Return an absolute resolved path."""
    return Path(path).expanduser().resolve()


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> Path:
    """Atomically write JSON to avoid partial updates."""
    dest = ensure_absolute_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = canonicalize_state(payload)
        validate_pipeline_schema(payload)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Phase 5 schema normalization skipped: %s", exc)
    with NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=dest.parent) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(dest)
    logger.debug("Wrote JSON atomically to %s (via %s)", dest, tmp_path)
    return dest


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
        raise ValueError(f"Audio validation failed for {path}: unreadable or zero length.")


def atomic_replace(target: Path, temp_source: Path) -> None:
    """Move temp_source into target atomically."""
    target = ensure_absolute_path(target)
    temp_source.replace(target)
