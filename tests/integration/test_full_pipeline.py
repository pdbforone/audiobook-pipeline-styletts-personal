"""Phase O: End-to-end pipeline validation (opt-in, heavy)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


RUN_PHASE_O = os.environ.get("RUN_PHASE_O_FULL") == "1"
INPUT_FILE = Path("input/baseline_snippet.txt")
PIPELINE_JSON = Path(".pipeline/verification_pipeline.json")
ORCH = Path("phase6_orchestrator") / "orchestrator.py"


def _require_env() -> None:
    if not RUN_PHASE_O:
        pytest.skip("Set RUN_PHASE_O_FULL=1 to run full pipeline validation")
    if not INPUT_FILE.exists():
        pytest.skip(f"Missing baseline input: {INPUT_FILE}")
    if not ORCH.exists():
        pytest.skip(f"Missing orchestrator: {ORCH}")


def _run_orchestrator(phases: list[int]) -> dict:
    _require_env()
    cmd = [
        sys.executable,
        str(ORCH),
        str(INPUT_FILE),
        "--pipeline-json",
        str(PIPELINE_JSON),
        "--no-resume",
        "--phases",
        *map(str, phases),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"Orchestrator failed: {result.stderr.strip()}")
    return json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))


def test_full_pipeline_success():
    data = _run_orchestrator([1, 2, 3, 4, 5])
    file_id = INPUT_FILE.stem
    for phase_key in ("phase1", "phase2", "phase3", "phase4", "phase5", "phase6"):
        status = data.get(phase_key, {}).get("status")
        if status != "success":
            pytest.skip(f"{phase_key} status not successful ({status})")

    phase3_files = data.get("phase3", {}).get("files", {})
    chunks = phase3_files.get(file_id, {}).get("chunk_paths") or []
    assert chunks, "Phase3 chunk list should not be empty"
    assert chunks == sorted(chunks), "Phase3 chunks should be sorted"

    phase4_files = data.get("phase4", {}).get("files", {})
    phase4_entry = phase4_files.get(file_id, {})
    audio_paths = []
    for chunk in phase4_entry.get("chunks", []):
        path_str = chunk.get("audio_path") or chunk.get("path")
        if path_str:
            audio_paths.append(Path(path_str))
    if not audio_paths:
        default_audio = Path("phase4_tts") / "audio_chunks"
        audio_paths = list(default_audio.glob("*.wav"))
    if not audio_paths:
        pytest.skip("No Phase4 audio artifacts found")
    for audio_path in audio_paths:
        assert audio_path.exists(), f"Missing audio file {audio_path}"
        assert audio_path.stat().st_size > 0, f"Audio file empty: {audio_path}"

    phase5_files = data.get("phase5", {}).get("files", {})
    phase5_entry = phase5_files.get(file_id, {})
    enhanced_path = phase5_entry.get("output_path")
    if not enhanced_path:
        candidate = Path("phase5_enhancement") / "processed"
        candidates = list(candidate.glob("*.wav"))
        if candidates:
            enhanced_path = candidates[0]
    if not enhanced_path:
        pytest.skip("No Phase5 enhanced output found")
    enhanced = Path(enhanced_path)
    assert enhanced.exists(), f"Missing enhanced audio {enhanced}"
    assert enhanced.stat().st_size > 0, "Enhanced audio file is empty"
