"""Phase O: Cross-phase schema alignment checks (opt-in)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


RUN_PHASE_O = os.environ.get("RUN_PHASE_O_FULL") == "1"
PIPELINE_JSON = Path(".pipeline/verification_pipeline.json")
INPUT_FILE = Path("input/baseline_snippet.txt")


@pytest.fixture(scope="session")
def pipeline_state():
    if not RUN_PHASE_O:
        pytest.skip("Set RUN_PHASE_O_FULL=1 to run Phase O validation")
    if not PIPELINE_JSON.exists():
        pytest.skip("Pipeline state missing; run full pipeline first")
    return json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))


def test_phase2_to_phase3_alignment(pipeline_state):
    file_id = INPUT_FILE.stem
    phase2_files = pipeline_state.get("phase2", {}).get("files", {})
    phase3_files = pipeline_state.get("phase3", {}).get("files", {})
    if file_id not in phase2_files or file_id not in phase3_files:
        pytest.skip("Phase2/Phase3 entries missing for baseline_snippet")
    phase2_hash = phase2_files[file_id].get("sha256") or phase2_files[file_id].get("hash")
    phase3_hash = phase3_files[file_id].get("input_hash") or phase3_files[file_id].get("sha256")
    assert phase2_hash is None or phase3_hash is None or phase2_hash == phase3_hash
    chunk_paths = phase3_files[file_id].get("chunk_paths") or []
    assert chunk_paths == sorted(chunk_paths)
    assert chunk_paths, "Phase3 chunk_paths should not be empty"


def test_phase3_to_phase4_alignment(pipeline_state):
    file_id = INPUT_FILE.stem
    phase3_chunks = pipeline_state.get("phase3", {}).get("files", {}).get(file_id, {}).get("chunk_paths") or []
    phase4_chunks = pipeline_state.get("phase4", {}).get("files", {}).get(file_id, {}).get("chunks") or []
    if not phase3_chunks or not phase4_chunks:
        pytest.skip("Phase3 or Phase4 chunk data missing")
    phase4_ids = [c.get("chunk_id") or Path(c.get("audio_path", "")).stem for c in phase4_chunks]
    assert len(phase3_chunks) == len(phase4_ids)
    assert phase4_ids == sorted(phase4_ids)
    engines = {c.get("engine_used") for c in phase4_chunks if c.get("engine_used")}
    disallowed = {e for e in engines if e and e.lower() == "piper"}
    assert not disallowed, "Piper engine must remain disabled"
    allowed = {"xtts", "kokoro"}
    assert engines <= allowed or not engines


def test_phase4_to_phase5_alignment(pipeline_state):
    file_id = INPUT_FILE.stem
    phase4_chunks = pipeline_state.get("phase4", {}).get("files", {}).get(file_id, {}).get("chunks") or []
    phase5_entry = pipeline_state.get("phase5", {}).get("files", {}).get(file_id, {})
    if not phase4_chunks or not phase5_entry:
        pytest.skip("Phase4 or Phase5 data missing")
    processed = phase5_entry.get("processed_chunks") or phase5_entry.get("chunks") or []
    if not processed:
        pytest.skip("No Phase5 processed chunk metadata to validate")
    phase4_ids = [c.get("chunk_id") for c in phase4_chunks if c.get("chunk_id")]
    phase5_ids = [c.get("chunk_id") for c in processed if c.get("chunk_id")]
    assert phase4_ids == phase5_ids
    assert processed == sorted(processed, key=lambda c: c.get("chunk_id", ""))
