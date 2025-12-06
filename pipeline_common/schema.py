"""
Canonical pipeline.json schema helpers and migration utilities.

This module provides:
- Schema loading from schema.json (v4.0.0)
- State canonicalization (normalizes arbitrary layouts)
- Lightweight validation (structural checks)
- Optional Pydantic-based strict validation

Schema v4.0.0 introduces phase-specific definitions:
- Each phase has its own block schema (phase1Block, phase2Block, etc.)
- Per-phase file schemas with required fields
- Per-phase chunk schemas (Phase 4/5 specific)
- Rich field descriptions and enums

Usage:
    from pipeline_common.schema import canonicalize_state, validate_pipeline_schema

    # Normalize and validate
    data = canonicalize_state(raw_data)
    validate_pipeline_schema(data)

    # Optional: Strict Pydantic validation
    from pipeline_common.schema import validate_with_pydantic
    validate_with_pydantic(data, strict=True)
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PipelineSchema

SCHEMA_PATH = Path(__file__).with_name("schema.json")


def _load_schema() -> Dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


CANONICAL_JSON_SCHEMA: Dict[str, Any] = _load_schema()
CANONICAL_SCHEMA_VERSION: str = CANONICAL_JSON_SCHEMA.get("version", "3.0.0")

PHASE_KEYS: Tuple[str, ...] = (
    "phase1",
    "phase2",
    "phase3",
    "phase4",
    "phase5",
    "phase5_5",
    "phase6",
    "phase7",
)

VALID_PHASE_STATUSES: Tuple[str, ...] = tuple(
    CANONICAL_JSON_SCHEMA.get("definitions", {})
    .get("status", {})
    .get(
        "enum",
        [
            "pending",
            "running",
            "success",
            "partial",
            "partial_success",
            "failed",
            "error",
            "skipped",
            "unknown",
        ],
    )
)

_STATUS_FALLBACKS = {
    "complete": "success",
    "completed": "success",
    "ok": "success",
    "ready": "success",
    "in_progress": "running",
}

_PHASE_WRAPPER_KEYS = {
    "status",
    "timestamps",
    "artifacts",
    "metrics",
    "errors",
    "files",
}
_FILE_LIKE_KEYS = {
    "file_path",
    "hash",
    "sha256",
    "classification",
    "chunk_paths",
    "chunks",
    "chunk_id",
    "chunk_audio_paths",
    "voice_id",
    "extracted_text_path",
    "wav_path",
    "enhanced_path",
    "artifacts_path",
    "repair_status",
    "status",
    "errors",
    "metrics",
    "timestamps",
}
_CHUNK_KEY_RE = re.compile(r"^chunk[_-]?\d+$", re.IGNORECASE)
_PHASES_EXPECTING_FILES = {
    "phase1",
    "phase2",
    "phase3",
    "phase4",
    "phase5",
    "phase5_5",
}
_PHASE_REQUIRED_FIELDS = (
    "status",
    "timestamps",
    "artifacts",
    "metrics",
    "errors",
)
_BATCH_REQUIRED_FIELDS = (
    "run_id",
    "status",
    "timestamps",
    "metrics",
    "errors",
    "files",
)
_PHASE_PAYLOAD_EXCLUSIONS = set(_PHASE_WRAPPER_KEYS) | {"files"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize_state(
    raw: Dict[str, Any],
    *,
    schema_version: Optional[str] = None,
    touch_timestamps: bool = True,
) -> Dict[str, Any]:
    """Convert arbitrary layouts into the canonical phase-first shape."""
    if not isinstance(raw, dict):
        raise ValueError("Pipeline state must be a JSON object.")

    data = deepcopy(raw)
    now = _now_iso()
    if schema_version is not None:
        data["pipeline_version"] = schema_version
    else:
        data.setdefault("pipeline_version", CANONICAL_SCHEMA_VERSION)

    if touch_timestamps:
        data.setdefault("created_at", now)
        data["last_updated"] = now

    _lift_file_first_layout(data)
    _normalize_batch_runs(data)

    primary_file_id = data.get("file_id")
    for phase_key in PHASE_KEYS:
        block = data.get(phase_key)
        if block is None:
            continue
        data[phase_key] = _normalize_phase_block(
            phase_key, block, primary_file_id=primary_file_id
        )

    data["phases"] = {
        phase: data[phase]["status"]
        for phase in PHASE_KEYS
        if isinstance(data.get(phase), dict) and "status" in data[phase]
    }
    data.setdefault("batch_runs", [])
    return data


def _lift_file_first_layout(data: Dict[str, Any]) -> None:
    """Promote legacy {file_id: {phase1: {...}}} layouts into phase-first maps."""
    file_first_candidates = {
        key: value
        for key, value in list(data.items())
        if isinstance(value, dict)
        and any(phase in value for phase in PHASE_KEYS)
    }
    if not file_first_candidates:
        return

    for file_id, payload in file_first_candidates.items():
        for phase_key in PHASE_KEYS:
            block = payload.get(phase_key)
            if isinstance(block, dict):
                phase_section = data.setdefault(phase_key, {})
                files = phase_section.setdefault("files", {})
                files[file_id] = deepcopy(block)
        data.pop(file_id, None)


def _normalize_phase_block(
    phase_key: str,
    block: Dict[str, Any],
    *,
    primary_file_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized = deepcopy(block) if isinstance(block, dict) else {}
    normalized["status"] = _coerce_status(normalized.get("status"))
    normalized["timestamps"] = _ensure_dict(normalized.get("timestamps"))
    normalized["artifacts"] = _ensure_artifacts_container(
        normalized.get("artifacts")
    )
    normalized["metrics"] = _ensure_dict(normalized.get("metrics"))
    normalized["errors"] = _ensure_list(normalized.get("errors"))

    files = normalized.get("files")
    if not isinstance(files, dict):
        files = {}
    normalized_files: Dict[str, Dict[str, Any]] = {}

    # Support legacy phase[file_id] payloads by pulling non-wrapper dict entries into files
    for candidate_key, candidate_value in list(normalized.items()):
        if candidate_key in _PHASE_WRAPPER_KEYS or candidate_key == "files":
            continue
        if isinstance(candidate_value, dict) and _looks_like_file_entry(
            candidate_value
        ):
            files[candidate_key] = candidate_value

    for file_id, entry in files.items():
        normalized_files[file_id] = _normalize_phase_entry(phase_key, entry)

    # Special-case Phase 5.5 legacy payloads that were written without files
    if phase_key == "phase5_5" and not normalized_files:
        payload = {
            key: deepcopy(value)
            for key, value in normalized.items()
            if key not in _PHASE_PAYLOAD_EXCLUSIONS
        }
        if payload:
            inferred_id = (
                primary_file_id or payload.get("file_id") or "default"
            )
            normalized_files[inferred_id] = _normalize_phase_entry(
                phase_key, payload
            )

    if normalized_files or phase_key in _PHASES_EXPECTING_FILES:
        normalized["files"] = normalized_files
    return normalized


def _normalize_phase_entry(
    phase_key: str, entry: Dict[str, Any]
) -> Dict[str, Any]:
    normalized = deepcopy(entry) if isinstance(entry, dict) else {}
    normalized["status"] = _coerce_status(normalized.get("status"))
    normalized["timestamps"] = _ensure_dict(normalized.get("timestamps"))
    normalized["artifacts"] = _ensure_artifacts_container(
        normalized.get("artifacts")
    )
    normalized["metrics"] = _ensure_dict(normalized.get("metrics"))
    normalized["errors"] = _ensure_list(normalized.get("errors"))
    normalized["chunks"] = _ensure_chunk_collection(normalized)
    return normalized


def _ensure_chunk_collection(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collapse chunk_0001 style keys into the canonical chunks list."""
    chunks: List[Dict[str, Any]] = []
    existing_chunks = entry.get("chunks")
    if isinstance(existing_chunks, list):
        chunks.extend(
            [
                deepcopy(chunk)
                for chunk in existing_chunks
                if isinstance(chunk, dict)
            ]
        )

    chunk_keys = [
        key
        for key in list(entry.keys())
        if _CHUNK_KEY_RE.match(key) and isinstance(entry[key], dict)
    ]
    for key in sorted(chunk_keys, key=_chunk_key_sort):
        chunk = deepcopy(entry.pop(key))
        chunk.setdefault("chunk_id", key)
        chunk.setdefault("status", _coerce_status(chunk.get("status")))
        chunk.setdefault("errors", _ensure_list(chunk.get("errors")))
        chunks.append(chunk)

    if chunks:
        entry["chunks"] = chunks
    else:
        entry["chunks"] = []
    return entry["chunks"]


def _chunk_key_sort(key: str) -> Tuple[int, str]:
    digits = re.findall(r"\d+", key)
    return (int(digits[-1]) if digits else 0, key)


def _normalize_batch_runs(data: Dict[str, Any]) -> None:
    runs: List[Dict[str, Any]] = []
    existing_runs = data.get("batch_runs")
    if isinstance(existing_runs, list):
        for idx, run in enumerate(existing_runs):
            if isinstance(run, dict):
                runs.append(
                    _normalize_batch_run(run, default_id=f"batch_{idx + 1}")
                )

    legacy_batch = data.pop("batch", None)
    if isinstance(legacy_batch, dict):
        runs.append(
            _convert_legacy_batch(legacy_batch, hint=f"batch_{len(runs) + 1}")
        )

    data["batch_runs"] = runs


def _normalize_batch_run(
    run: Dict[str, Any], *, default_id: str
) -> Dict[str, Any]:
    normalized = deepcopy(run)
    normalized["run_id"] = str(normalized.get("run_id") or default_id)
    normalized["status"] = _coerce_status(normalized.get("status"))
    normalized["timestamps"] = _ensure_dict(normalized.get("timestamps"))
    if not normalized["timestamps"]:
        summary = normalized.get("summary")
        if isinstance(summary, dict):
            normalized["timestamps"] = _summary_timestamps(summary)
    normalized["metrics"] = _ensure_dict(normalized.get("metrics"))
    normalized["errors"] = _ensure_list(normalized.get("errors"))
    normalized["artifacts"] = _ensure_artifacts_container(
        normalized.get("artifacts")
    )

    files = normalized.get("files")
    if not isinstance(files, dict):
        files = {}
    normalized["files"] = {
        file_id: _normalize_batch_file_entry(entry)
        for file_id, entry in files.items()
        if isinstance(entry, dict)
    }
    return normalized


def _convert_legacy_batch(
    batch: Dict[str, Any], *, hint: str
) -> Dict[str, Any]:
    summary = batch.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    run = {
        "run_id": str(summary_dict.get("run_id") or hint),
        "status": _coerce_status(
            batch.get("status") or summary_dict.get("status")
        ),
        "timestamps": _summary_timestamps(summary_dict),
        "metrics": _legacy_summary_metrics(summary_dict),
        "errors": _ensure_list(summary_dict.get("errors")),
        "artifacts": _ensure_artifacts_container(
            summary_dict.get("artifacts")
        ),
        "files": {},
    }
    files = batch.get("files")
    if isinstance(files, dict):
        for file_id, entry in files.items():
            if isinstance(entry, dict):
                run["files"][file_id] = _normalize_batch_file_entry(entry)
    return run


def _summary_timestamps(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "start": summary.get("started_at"),
        "end": summary.get("completed_at"),
        "duration": summary.get("duration_sec"),
    }


def _legacy_summary_metrics(summary: Dict[str, Any]) -> Dict[str, Any]:
    omit = {
        "run_id",
        "status",
        "started_at",
        "completed_at",
        "duration_sec",
        "errors",
        "artifacts",
    }
    metrics = {
        key: deepcopy(value)
        for key, value in summary.items()
        if key not in omit
    }
    if "duration_sec" in summary:
        metrics.setdefault("duration_sec", summary["duration_sec"])
    return metrics


def _normalize_batch_file_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(entry)
    normalized["status"] = _coerce_status(normalized.get("status"))
    normalized["timestamps"] = _ensure_dict(normalized.get("timestamps"))
    if not normalized["timestamps"]:
        normalized["timestamps"] = {
            "start": normalized.get("started_at"),
            "end": normalized.get("completed_at"),
            "duration": normalized.get("duration_sec"),
        }
    normalized["artifacts"] = _ensure_artifacts_container(
        normalized.get("artifacts")
        or {"source_path": normalized.get("source_path")}
    )
    metrics = _ensure_dict(normalized.get("metrics"))
    if normalized.get("duration_sec") is not None:
        metrics.setdefault("duration_sec", normalized["duration_sec"])
    if normalized.get("cpu_avg") is not None:
        metrics.setdefault("cpu_avg", normalized["cpu_avg"])
    normalized["metrics"] = metrics
    errors = _ensure_list(normalized.get("errors"))
    if normalized.get("error_message"):
        errors.append(normalized["error_message"])
    normalized["errors"] = errors
    return normalized


def _ensure_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    if value is None or value == "":
        return []
    return [value]


def _ensure_artifacts_container(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return deepcopy(value)
    return {}


def _coerce_status(value: Any) -> str:
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in VALID_PHASE_STATUSES:
            return lowered
        if lowered in _STATUS_FALLBACKS:
            return _STATUS_FALLBACKS[lowered]
    return "pending"


def _looks_like_file_entry(entry: Dict[str, Any]) -> bool:
    if not isinstance(entry, dict):
        return False
    return any(key in entry for key in _FILE_LIKE_KEYS)


def validate_pipeline_schema(
    data: Dict[str, Any], *, required_phases: Optional[Iterable[str]] = None
) -> None:
    """Lightweight schema validation used before writes."""
    if not isinstance(data, dict):
        raise ValueError("pipeline.json root must be an object.")

    errors: List[str] = []
    for meta_key in ("pipeline_version", "created_at", "last_updated"):
        if (
            meta_key in data
            and data[meta_key] is not None
            and not isinstance(data[meta_key], str)
        ):
            errors.append(f"{meta_key} must be a string when present")

    for phase_key in PHASE_KEYS:
        block = data.get(phase_key)
        if block is None:
            continue
        _validate_phase_block(phase_key, block, errors)

    runs = data.get("batch_runs")
    if runs is not None:
        if not isinstance(runs, list):
            errors.append("batch_runs must be an array when present")
        else:
            for idx, run in enumerate(runs):
                _validate_batch_run(idx, run, errors)

    if required_phases:
        for phase in required_phases:
            if data.get(phase) is None:
                errors.append(f"Missing required phase block '{phase}'")

    if errors:
        raise ValueError("; ".join(errors))


def _validate_phase_block(
    phase_key: str, block: Any, errors: List[str]
) -> None:
    if not isinstance(block, dict):
        errors.append(f"{phase_key} must be an object")
        return

    for field in _PHASE_REQUIRED_FIELDS:
        if field not in block:
            errors.append(f"{phase_key} missing required field '{field}'")

    status = block.get("status")
    if status is not None and status not in VALID_PHASE_STATUSES:
        errors.append(f"{phase_key}.status has invalid value '{status}'")

    timestamps = block.get("timestamps")
    if timestamps is not None and not isinstance(timestamps, dict):
        errors.append(f"{phase_key}.timestamps must be an object")

    artifacts = block.get("artifacts")
    if artifacts is not None and not isinstance(artifacts, (dict, list)):
        errors.append(f"{phase_key}.artifacts must be an object or array")

    metrics = block.get("metrics")
    if metrics is not None and not isinstance(metrics, dict):
        errors.append(f"{phase_key}.metrics must be an object")

    errors_field = block.get("errors")
    if errors_field is not None and not isinstance(errors_field, list):
        errors.append(f"{phase_key}.errors must be an array")

    files = block.get("files")
    if files is not None:
        if not isinstance(files, dict):
            errors.append(f"{phase_key}.files must be an object when present")
        else:
            for file_id, entry in files.items():
                _validate_phase_file_entry(phase_key, file_id, entry, errors)


def _validate_phase_file_entry(
    phase_key: str, file_id: str, entry: Any, errors: List[str]
) -> None:
    if not isinstance(entry, dict):
        errors.append(f"{phase_key}.files['{file_id}'] must be an object")
        return
    for field in _PHASE_REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"{phase_key}.files['{file_id}'] missing '{field}'")

    status = entry.get("status")
    if status is not None and status not in VALID_PHASE_STATUSES:
        errors.append(
            f"{phase_key}.files['{file_id}'].status has invalid value '{status}'"
        )

    timestamps = entry.get("timestamps")
    if timestamps is not None and not isinstance(timestamps, dict):
        errors.append(
            f"{phase_key}.files['{file_id}'].timestamps must be an object"
        )

    artifacts = entry.get("artifacts")
    if artifacts is not None and not isinstance(artifacts, (dict, list)):
        errors.append(
            f"{phase_key}.files['{file_id}'].artifacts must be an object or array"
        )

    metrics = entry.get("metrics")
    if metrics is not None and not isinstance(metrics, dict):
        errors.append(
            f"{phase_key}.files['{file_id}'].metrics must be an object"
        )

    errors_field = entry.get("errors")
    if errors_field is not None and not isinstance(errors_field, list):
        errors.append(
            f"{phase_key}.files['{file_id}'].errors must be an array"
        )

    chunks = entry.get("chunks")
    if chunks is not None and not isinstance(chunks, list):
        errors.append(
            f"{phase_key}.files['{file_id}'].chunks must be an array when present"
        )


def _validate_batch_run(index: int, run: Any, errors: List[str]) -> None:
    if not isinstance(run, dict):
        errors.append(f"batch_runs[{index}] must be an object")
        return
    for field in _BATCH_REQUIRED_FIELDS:
        if field not in run:
            errors.append(f"batch_runs[{index}] missing '{field}'")

    status = run.get("status")
    if status is not None and status not in VALID_PHASE_STATUSES:
        errors.append(
            f"batch_runs[{index}].status has invalid value '{status}'"
        )

    timestamps = run.get("timestamps")
    if timestamps is not None and not isinstance(timestamps, dict):
        errors.append(f"batch_runs[{index}].timestamps must be an object")

    metrics = run.get("metrics")
    if metrics is not None and not isinstance(metrics, dict):
        errors.append(f"batch_runs[{index}].metrics must be an object")

    errors_field = run.get("errors")
    if errors_field is not None and not isinstance(errors_field, list):
        errors.append(f"batch_runs[{index}].errors must be an array")

    artifacts = run.get("artifacts")
    if artifacts is not None and not isinstance(artifacts, (dict, list)):
        errors.append(
            f"batch_runs[{index}].artifacts must be an object or array"
        )

    files = run.get("files")
    if files is None:
        return
    if not isinstance(files, dict):
        errors.append(f"batch_runs[{index}].files must be an object")
        return
    for file_id, entry in files.items():
        if not isinstance(entry, dict):
            errors.append(
                f"batch_runs[{index}].files['{file_id}'] must be an object"
            )
            continue
        for field in _PHASE_REQUIRED_FIELDS:
            if field not in entry:
                errors.append(
                    f"batch_runs[{index}].files['{file_id}'] missing '{field}'"
                )


# =============================================================================
# Pydantic Integration (Optional)
# =============================================================================


def validate_with_pydantic(
    data: Dict[str, Any],
    *,
    strict: bool = True,
    raise_on_error: bool = True,
) -> Tuple[bool, List[str]]:
    """
    Validate pipeline data using Pydantic models for stricter type checking.

    This provides deeper validation than validate_pipeline_schema():
    - Type checking for all fields
    - Enum validation for status, engines, profiles
    - Nested model validation for chunks
    - Range validation (e.g., 0 <= quality_score <= 1)

    Args:
        data: Pipeline state dictionary
        strict: If True, use full PipelineSchema; if False, minimal validation
        raise_on_error: If True, raise ValueError on validation failure

    Returns:
        Tuple of (is_valid, list_of_errors)

    Raises:
        ValueError: If raise_on_error=True and validation fails
        ImportError: If pydantic is not installed

    Example:
        >>> from pipeline_common.schema import validate_with_pydantic
        >>> is_valid, errors = validate_with_pydantic(data, raise_on_error=False)
        >>> if not is_valid:
        ...     print(f"Validation errors: {errors}")
    """
    try:
        from .models import (
            PipelineSchema,
            MinimalPipelineSchema,
            PYDANTIC_AVAILABLE,
        )
    except ImportError as e:
        if raise_on_error:
            raise ImportError(
                "Pydantic models not available. Install pydantic>=2.0"
            ) from e
        return False, ["Pydantic models not available"]

    if not PYDANTIC_AVAILABLE:
        # Pydantic not installed, fall back to lightweight validation
        try:
            validate_pipeline_schema(data)
            return True, []
        except ValueError as e:
            if raise_on_error:
                raise
            return False, [str(e)]

    schema_class = PipelineSchema if strict else MinimalPipelineSchema
    errors: List[str] = []

    try:
        schema_class.model_validate(data)
        return True, []
    except Exception as e:
        error_msg = str(e)
        errors.append(error_msg)
        if raise_on_error:
            raise ValueError(f"Pydantic validation failed: {error_msg}") from e
        return False, errors


def get_schema_version() -> str:
    """Return the current schema version from schema.json."""
    return CANONICAL_SCHEMA_VERSION


def get_phase_definitions() -> Dict[str, Dict[str, Any]]:
    """
    Extract phase-specific definitions from the schema.

    Returns:
        Dictionary mapping phase names to their schema definitions

    Example:
        >>> defs = get_phase_definitions()
        >>> phase4_chunk_schema = defs.get("phase4Chunk", {})
    """
    definitions = CANONICAL_JSON_SCHEMA.get("definitions", {})
    return {
        key: value
        for key, value in definitions.items()
        if key.startswith("phase") or key.endswith("Block") or key.endswith("Chunk")
    }
