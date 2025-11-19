"""File-system helpers for Phase 4."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict

import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from pipeline_common import canonicalize_state, validate_pipeline_schema
except Exception:  # pragma: no cover - defensive fallback when pipeline_common is unavailable
    canonicalize_state = lambda payload, **kwargs: payload  # type: ignore

    def validate_pipeline_schema(payload, **kwargs):  # type: ignore
        return None

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


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> Path:
    """Atomically write JSON data to disk."""
    dest = ensure_absolute_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = canonicalize_state(payload)
        validate_pipeline_schema(payload)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Phase 4 schema normalization skipped: %s", exc)
    with NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=dest.parent) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(dest)
    logger.debug("Wrote %s atomically (via %s)", dest, tmp_path)
    return dest
