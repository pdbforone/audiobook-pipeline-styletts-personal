import hashlib
import logging
import sys
from pathlib import Path
from typing import Any, Tuple

logger = logging.getLogger(__name__)


def _load_pipeline_common() -> Tuple[Any, Any, Any, Any]:
    """
    Import pipeline_common after ensuring the repo root is on sys.path.

    The test runner sometimes executes from the phase1-validation folder,
    which omits the repo root from sys.path by default.
    """
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from pipeline_common import (  # local import keeps ruff E402 satisfied
        PipelineState,
        StateError,
        ensure_phase_and_file,
        ensure_phase_block,
    )

    return PipelineState, StateError, ensure_phase_and_file, ensure_phase_block


PipelineState, StateError, ensure_phase_and_file, ensure_phase_block = (
    _load_pipeline_common()
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
