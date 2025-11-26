"""
Utilities for Phase 2 Extraction

Provides:
- Thread-safe pipeline.json updates
- File type detection
- Retry logic for transient errors
- Helper functions
"""

from __future__ import annotations

import logging
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml
from pipeline_common import (
    PipelineState,
    StateError,
    ensure_phase_and_file,
    ensure_phase_block,
    ensure_phase_file_entry,
)
from pipeline_common.state_manager import StateTransaction

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {"use_nemo": False}
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


def _install_update_phase_api() -> None:
    """Ensure transactions expose update_phase for schema-first writes."""

    if hasattr(StateTransaction, "update_phase"):
        return

    def update_phase(  # type: ignore[override]
        self,
        file_id: str,
        phase_name: str,
        status: Optional[str] = None,
        timestamps: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Any] = None,
        metrics: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Any]] = None,
        *,
        chunks: Optional[List[Dict[str, Any]]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        phase_block, file_entry = ensure_phase_and_file(
            self.data, phase_name, file_id
        )
        envelope = file_entry
        if status is not None:
            envelope["status"] = status
        else:
            envelope.setdefault("status", "pending")
        if timestamps is not None:
            envelope["timestamps"] = dict(timestamps)
        else:
            envelope.setdefault("timestamps", {})
        if artifacts is not None:
            envelope["artifacts"] = artifacts
        else:
            envelope.setdefault("artifacts", {})
        if metrics is not None:
            envelope["metrics"] = dict(metrics)
        else:
            envelope.setdefault("metrics", {})
        if errors is not None:
            envelope["errors"] = list(errors)
        else:
            envelope.setdefault("errors", [])
        if chunks is not None:
            envelope["chunks"] = list(chunks)
        else:
            envelope.setdefault("chunks", [])
        if extra_fields:
            envelope.update(extra_fields)
        return envelope

    setattr(StateTransaction, "update_phase", update_phase)


_install_update_phase_api()


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load Phase 2 configuration from YAML with sane defaults.

    Args:
        config_path: Optional explicit path to a YAML config file.

    Returns:
        Dict of configuration values with defaults applied.
    """
    config: Dict[str, Any] = DEFAULT_CONFIG.copy()
    path = config_path or DEFAULT_CONFIG_PATH

    if path and path.exists():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                config.update(loaded)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to read config from {path}: {exc}")
    else:
        logger.debug(f"No config file found at {path}, using defaults.")

    return config


def _deep_merge_inplace(base: Any, new_data: Any) -> Any:
    """Recursively merge ``new_data`` into ``base``."""
    if isinstance(base, dict) and isinstance(new_data, dict):
        for key, value in new_data.items():
            if key in base:
                base[key] = _deep_merge_inplace(base[key], value)
            else:
                base[key] = deepcopy(value)
        return base
    if isinstance(base, list) and isinstance(new_data, list):
        base.extend(deepcopy(item) for item in new_data)
        return base
    return deepcopy(new_data)


def merge_phase_state(
    pipeline_path: Path,
    phase_name: str,
    data: Dict[str, Any],
    *,
    operation: str = "phase_update",
) -> Dict[str, Any]:
    """
    Merge ``data`` into ``pipeline_path`` under ``phase_name`` using PipelineState.
    """
    files = data.get("files") or {}
    status = data.get("status")
    timestamps = data.get("timestamps")
    artifacts = data.get("artifacts")
    metrics = data.get("metrics")
    errors = data.get("errors")
    chunks = data.get("chunks")

    state = PipelineState(pipeline_path, validate_on_read=False)
    with state.transaction(operation=operation) as txn:
        phase_block = ensure_phase_block(txn.data, phase_name)
        if status:
            phase_block["status"] = status
        if timestamps:
            phase_block.setdefault("timestamps", {}).update(timestamps)
        if artifacts is not None:
            existing_artifacts = phase_block.get("artifacts")
            if isinstance(existing_artifacts, dict) and isinstance(
                artifacts, dict
            ):
                existing_artifacts.update(artifacts)
            elif isinstance(existing_artifacts, list) and isinstance(
                artifacts, list
            ):
                existing_artifacts.extend(artifacts)
            else:
                phase_block["artifacts"] = artifacts
        if metrics:
            phase_block.setdefault("metrics", {}).update(metrics)
        if errors:
            phase_errors = phase_block.setdefault("errors", [])
            phase_errors.extend(errors)
        if chunks is not None:
            if isinstance(chunks, list):
                phase_block["chunks"] = list(chunks)
            else:
                phase_block["chunks"] = []

        for file_id, entry in files.items():
            entry_status = entry.get("status", status or "pending")
            txn.update_phase(
                file_id,
                phase_name,
                entry_status,
                entry.get("timestamps"),
                entry.get("artifacts"),
                entry.get("metrics"),
                entry.get("errors"),
                chunks=entry.get("chunks"),
                extra_fields=entry,
            )
        return txn.data


def with_retry(
    func: Callable[[], Any], max_attempts: int = 3, delay: float = 1.0
) -> Any:
    """
    Retry function on transient errors.

    Args:
        func: Function to retry (should take no arguments)
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds

    Returns:
        Result of successful function call

    Raises:
        Last exception if all attempts fail

    Reason: Handles transient errors like file locks, network issues,
    temporary permission problems. Exponential backoff gives system
    time to recover.
    """
    for attempt in range(max_attempts):
        try:
            return func()
        except (IOError, OSError, PermissionError) as e:
            if attempt == max_attempts - 1:
                logger.error(f"Failed after {max_attempts} attempts: {e}")
                raise

            wait_time = delay * (2**attempt)  # Exponential backoff
            logger.warning(
                f"Attempt {attempt+1} failed: {e}, retrying in {wait_time}s..."
            )
            time.sleep(wait_time)


def detect_format(path: Path) -> str:
    """
    Detect file format using extension and MIME type.

    Args:
        path: Path to file

    Returns:
        Format string: 'pdf', 'docx', 'epub', 'html', 'txt'

    Strategy:
    1. Check file extension
    2. Validate with MIME type if python-magic available
    3. Fall back to extension only if MIME fails

    Reason: Combining extension and MIME detection prevents
    misidentification from renamed files or missing extensions.
    """
    ext = path.suffix.lower()

    # Try MIME detection if available
    if MAGIC_AVAILABLE:
        try:
            mime = magic.from_file(str(path), mime=True)
            logger.debug(f"MIME type detected: {mime}")

            # MIME-based detection (more reliable)
            if "pdf" in mime:
                return "pdf"
            elif "word" in mime or "officedocument" in mime:
                return "docx"
            elif "epub" in mime:
                return "epub"
            elif "html" in mime:
                return "html"
            elif "text" in mime or "plain" in mime:
                return "txt"

        except Exception as e:
            logger.debug(
                f"MIME detection failed: {e}, falling back to extension"
            )

    # Extension-based detection (fallback)
    if ext == ".pdf":
        return "pdf"
    elif ext in (".docx", ".doc"):
        return "docx"
    elif ext == ".epub":
        return "epub"
    elif ext in (".html", ".htm"):
        return "html"
    elif ext in (".txt", ".md", ".text"):
        return "txt"

    # Default to txt with warning
    logger.warning(
        f"Ambiguous format for {path.name} (ext={ext}) - "
        f"defaulting to 'txt'. Consider using a standard extension."
    )
    return "txt"


def calculate_yield(original_size: int, extracted_length: int) -> float:
    """
    Calculate text yield percentage.

    Args:
        original_size: Original file size in bytes
        extracted_length: Length of extracted text in characters

    Returns:
        Yield as a float between 0.0 and 1.0+

    Reason: Yield helps detect extraction problems. Very low yield
    suggests OCR needed or extraction failure. Very high yield may
    indicate duplicate content or extraction artifacts.
    """
    if original_size == 0:
        return 0.0

    # Rough approximation: 1 char ≈ 1 byte for text content
    # This is imperfect but useful for detecting major issues
    yield_pct = extracted_length / original_size

    if yield_pct < 0.5:
        logger.warning(
            f"Low text yield ({yield_pct:.1%}) - "
            f"file may be scanned or extraction may have failed"
        )
    elif yield_pct > 2.0:
        logger.warning(
            f"High text yield ({yield_pct:.1%}) - "
            f"extracted text may contain duplicates or artifacts"
        )

    return yield_pct


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def log_error(
    pipeline_path: Path,
    phase_name: str,
    file_id: str,
    message: str,
    severity: str = "blocking",
) -> None:
    """
    Log an error to pipeline.json in standardized format.

    Args:
        pipeline_path: Path to pipeline.json
        phase_name: Phase where error occurred
        file_id: File identifier related to the error
        message: Human-readable message
        severity: 'blocking' or 'warning'

    Reason: Standardized error format makes debugging easier and
    ensures users get actionable fix instructions.
    """
    error_entry = {
        "file_id": file_id,
        "message": message,
        "phase": phase_name,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    try:
        state = PipelineState(pipeline_path, validate_on_read=False)
        with state.transaction(operation=f"{phase_name}_log_error") as txn:
            phase_block = ensure_phase_block(txn.data, phase_name)
            phase_block.setdefault("errors", []).append(error_entry)
            if file_id:
                file_entry = ensure_phase_file_entry(phase_block, file_id)
                file_entry.setdefault("errors", []).append(dict(error_entry))
                file_entry.setdefault("status", "error")
        logger.error(f"[{phase_name}:{file_id}] {message}")
    except StateError as exc:
        logger.error(f"Failed to log error to pipeline.json: {exc}")
        logger.error(f"Original error: [{phase_name}:{file_id}] {message}")
