"""Consistency checker for Phase T (opt-in, read-only)."""

from __future__ import annotations

from typing import Any, Dict


def _check_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> str:
    if not schema:
        return "pass"
    if not isinstance(payload, dict):
        return "fail"
    required = schema.get("required") or []
    allowed = schema.get("allowed") or []
    for req in required:
        if req not in payload:
            return "fail"
    for key in payload.keys():
        if allowed and key not in allowed:
            return "fail"
    return "pass"


def check_consistency(run_output: dict, schema_registry) -> dict:
    """
    Produce:
    {
      "schema_results": { "phase1": "pass|fail", ... },
      "cross_phase": {
            "id_stability": true|false,
            "chunk_counts_match": true|false,
            "engine_metadata_valid": true|false
      },
      "warnings": [...],
      "errors": [...]
    }
    """
    out = run_output or {}
    schema_results: Dict[str, str] = {}
    warnings = []
    errors = []

    phase_map = {
        "phase1": ("phase1_validation", out.get("phase1") or {}),
        "phase2": ("phase2_extraction", out.get("phase2") or {}),
        "phase3": ("phase3_chunking", out.get("phase3") or {}),
        "phase4": ("phase4_tts", out.get("phase4") or {}),
        "phase5": ("phase5_enhancement", out.get("phase5") or {}),
        "phase6": ("phase6_summary", out.get("phase6") or {}),
    }
    for key, (schema_name, payload) in phase_map.items():
        schema = schema_registry.get_expected_schema(schema_name)
        schema_results[key] = _check_schema(payload, schema)

    run_ids = {v.get("run_id") for v in out.values() if isinstance(v, dict) and v.get("run_id")}
    id_stability = len(run_ids) <= 1
    if not id_stability and run_ids:
        warnings.append("run_id_mismatch")

    # Cross-phase simple checks
    chunks = ((out.get("phase3") or {}).get("chunks") or []) if isinstance(out.get("phase3"), dict) else []
    tts_outputs = ((out.get("phase4") or {}).get("tts_outputs") or []) if isinstance(out.get("phase4"), dict) else []
    enhanced_outputs = ((out.get("phase5") or {}).get("enhanced_outputs") or []) if isinstance(out.get("phase5"), dict) else []

    chunk_counts_match = len(chunks) == len(tts_outputs) if chunks or tts_outputs else True
    engine_metadata_valid = True
    for entry in tts_outputs:
        if not isinstance(entry, dict):
            continue
        if entry.get("engine") not in {None, "xtts", "kokoro"}:
            engine_metadata_valid = False
            warnings.append("unexpected_engine_metadata")
            break

    if enhanced_outputs and tts_outputs and len(enhanced_outputs) != len(tts_outputs):
        warnings.append("enhancement_count_mismatch")
        chunk_counts_match = False

    cross_phase = {
        "id_stability": id_stability,
        "chunk_counts_match": chunk_counts_match,
        "engine_metadata_valid": engine_metadata_valid,
    }

    # Basic negative value check
    for phase in ("phase3", "phase4", "phase5"):
        data = out.get(phase) or {}
        if isinstance(data, dict):
            for val in data.values():
                if isinstance(val, (int, float)) and val < 0:
                    warnings.append(f"negative_value_in_{phase}")
                    break

    return {
        "schema_results": schema_results,
        "cross_phase": cross_phase,
        "warnings": warnings,
        "errors": errors,
    }
