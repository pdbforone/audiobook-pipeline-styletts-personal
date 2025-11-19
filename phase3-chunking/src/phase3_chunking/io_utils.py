"""Robust file helpers for Phase 3 chunking."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict

logger = logging.getLogger(__name__)


def ensure_absolute_path(path: str | Path) -> Path:
    """Resolve a path and expand user/home markers."""
    resolved = Path(path).expanduser().resolve()
    return resolved


def safe_read_json(path: Path) -> Dict[str, Any]:
    """
    Read JSON returning an empty dict on missing file.

    Raises JSONDecodeError for corrupt payloads so callers can recover.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        logger.debug("JSON file not found at %s; returning empty payload.", path)
        return {}


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> Path:
    """
    Atomically write JSON to disk to avoid partial pipeline writes.

    Returns the absolute destination path.
    """
    dest = ensure_absolute_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=dest.parent) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(dest)
    logger.debug("Wrote JSON atomically to %s (via %s)", dest, tmp_path)
    return dest
