"""
Cross-phase validation helpers for integration tests.

These helpers are additive-only and rely on public data structures.
They perform structural/schema checks without mutating runtime state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


def _require_keys(mapping: Mapping, keys: Iterable[str]) -> None:
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise AssertionError(f"Missing required keys: {missing}")


# Minimal schemas for cross-phase structural validation (additive-only).
SCHEMA_PHASE1 = {"file_id", "validated", "metadata"}
SCHEMA_PHASE2 = {"file_id", "text", "extracted_text"}
SCHEMA_PHASE3 = {"id", "text"}
SCHEMA_PHASE4 = {"chunk_id", "audio_path"}
SCHEMA_PHASE5 = {"file_id", "phases", "status"}
SCHEMA_PHASE6 = {"file_id", "phases", "status"}


def validate_phase1_to_phase2_handshake(phase1_output: Mapping, phase2_input: Mapping) -> None:
    """
    Validate that Phase 1 output is well-formed for Phase 2 consumption.
    Checks are structural only and do not mutate inputs.
    """
    _require_keys(phase1_output, ["file_id", "validated", "metadata"])
    _require_keys(phase2_input, ["file_id", "text"])
    if phase1_output["file_id"] != phase2_input["file_id"]:
        raise AssertionError("Phase1/Phase2 file_id mismatch")
    if not isinstance(phase2_input.get("text", ""), str):
        raise AssertionError("Phase2 text must be a string")


def validate_phase2_to_phase3_structure(phase2_output: Mapping, phase3_input: Mapping) -> None:
    """
    Ensure Phase 2 extraction output is compatible with Phase 3 chunking input.
    """
    _require_keys(phase2_output, ["file_id", "extracted_text"])
    _require_keys(phase3_input, ["file_id", "text"])
    if phase2_output["file_id"] != phase3_input["file_id"]:
        raise AssertionError("Phase2/Phase3 file_id mismatch")
    if not isinstance(phase3_input.get("text", ""), str):
        raise AssertionError("Phase3 text must be a string")


def validate_phase3_to_phase4_chunks(chunks: Sequence[Mapping]) -> None:
    """
    Validate chunk structures handed off to Phase 4 TTS.
    """
    if not isinstance(chunks, (list, tuple)):
        raise AssertionError("Chunks must be a list/tuple")
    for chunk in chunks:
        _require_keys(chunk, ["id", "text"])
        if not isinstance(chunk["text"], str):
            raise AssertionError("Chunk text must be string")


def validate_phase4_to_phase5_audio(segments: Sequence[Mapping]) -> None:
    """
    Validate Phase 4 outputs before enhancement (Phase 5).
    Ensures audio paths are present and point to existing files.
    """
    for seg in segments:
        _require_keys(seg, ["audio_path", "chunk_id"])
        audio_path = Path(seg["audio_path"])
        if not audio_path.exists():
            raise AssertionError(f"Missing audio segment: {audio_path}")


def validate_phase5_to_phase6_outputs(run_summary_path: Path) -> Dict:
    """
    Validate that Phase 5 outputs feed Phase 6 orchestrator correctly.
    Reads a summary JSON and returns its parsed content for further checks.
    """
    if not run_summary_path.exists():
        raise AssertionError(f"Run summary missing: {run_summary_path}")
    data = json.loads(run_summary_path.read_text(encoding="utf-8"))
    _require_keys(data, ["file_id", "phases", "status"])
    return data


def validate_schema(obj: Mapping, required: Iterable[str]) -> None:
    """Generic schema validator used by integration tests."""
    _require_keys(obj, required)
    extras = set(obj.keys()) - set(required)
    if extras:
        raise AssertionError(f"Unexpected fields present: {extras}")
