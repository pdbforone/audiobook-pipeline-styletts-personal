import hashlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_common import (
    PipelineState,
    StateError,
    ensure_phase_and_file,
    ensure_phase_block,
)


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


def _state_for_path(json_path: Path) -> PipelineState:
    return PipelineState(Path(json_path), validate_on_read=False)


def log_error(
    json_path: Path,
    phase: str,
    file_id: str,
    message: str,
    category: str = "general",
) -> None:
    """Log and persist a validation error in a consistent format."""
    logger.error("[%s] %s: %s", phase, category, message)
    error_entry = {
        "file": file_id,
        "category": category,
        "message": message,
    }
    try:
        state = _state_for_path(json_path)
        with state.transaction(operation=f"{phase}_log_error") as txn:
            phase_block = ensure_phase_block(txn.data, phase)
            phase_block.setdefault("errors", []).append(error_entry)
            if file_id:
                file_entry = ensure_phase_and_file(txn.data, phase, file_id)[1]
                file_entry.setdefault("errors", []).append(dict(error_entry))
                file_entry.setdefault("status", "error")
    except StateError as exc:
        logger.warning("Failed to record pipeline error: %s", exc)
