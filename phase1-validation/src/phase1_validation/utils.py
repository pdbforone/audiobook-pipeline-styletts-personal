import hashlib
import json
import logging
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from pipeline_common import canonicalize_state, validate_pipeline_schema
except Exception:  # pragma: no cover - fallback when pipeline_common is unavailable
    canonicalize_state = lambda data, **kwargs: data  # type: ignore

    def validate_pipeline_schema(data, **kwargs):  # type: ignore
        return None

try:
    import msvcrt

    _WINDOWS = True
except ImportError:  # pragma: no cover - non-Windows platforms
    import fcntl  # type: ignore

    _WINDOWS = False


def compute_sha256(path: Path) -> str:
    """
    Compute a sha256 hash for the given file path.

    This helper is placed in utils so Phase 1 and Phase 2 can share the
    implementation without diverging hash behavior.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _acquire_lock(lock_path: Path):
    lock_file = open(lock_path, "a+b")
    if _WINDOWS:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
    else:  # pragma: no cover - non-Windows platforms
        fcntl.flock(lock_file, fcntl.LOCK_EX)
    return lock_file


def _release_lock(lock_file):
    try:
        if _WINDOWS:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:  # pragma: no cover - non-Windows platforms
            fcntl.flock(lock_file, fcntl.LOCK_UN)
    finally:
        lock_file.close()


def _deep_merge(base: Any, new: Any) -> Any:
    """Recursively merge dictionaries/lists while preserving unrelated content."""
    if isinstance(base, dict) and isinstance(new, dict):
        merged: Dict[str, Any] = {key: deepcopy(value) for key, value in base.items()}
        for key, value in new.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    if isinstance(base, list) and isinstance(new, list):
        combined = [*base, *new]
        deduped = []
        seen = set()
        for item in combined:
            try:
                marker = json.dumps(item, sort_keys=True)
            except TypeError:
                marker = str(item)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(deepcopy(item))
        return deduped
    return deepcopy(new)


def safe_update_json(json_path: Path, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Atomically deep-merge updates into a JSON file with cross-platform locking.

    - Uses .lock file with msvcrt on Windows or fcntl on Unix.
    - Performs a deep merge so unrelated phases are preserved.
    - Writes via a temp file then os.replace for atomicity.
    """
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = json_path.with_suffix(json_path.suffix + ".lock")

    lock_file = _acquire_lock(lock_path)
    try:
        if json_path.exists():
            try:
                existing = json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Invalid JSON encountered; recreating %s", json_path)
                existing = {}
        else:
            existing = {}

        merged = _deep_merge(existing, updates)
        try:
            merged = canonicalize_state(merged)
            validate_pipeline_schema(merged)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Skipped canonical schema enforcement: %s", exc)
        tmp_path = json_path.with_suffix(json_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        os.replace(tmp_path, json_path)
        return merged
    finally:
        _release_lock(lock_file)


def log_error(json_path: Path, phase: str, file_id: str, message: str, category: str = "general") -> None:
    """Log and persist a validation error in a consistent format."""
    logger.error("[%s] %s: %s", phase, category, message)
    json_path = Path(json_path)
    safe_update_json(
        json_path,
        {
            phase: {
                "errors": [
                    {
                        "file": file_id,
                        "category": category,
                        "message": message,
                    }
                ]
            }
        },
    )
