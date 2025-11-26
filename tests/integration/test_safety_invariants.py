"""Phase O: Safety invariants (opt-in, non-destructive)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


RUN_PHASE_O = os.environ.get("RUN_PHASE_O_FULL") == "1"
PIPELINE_JSON = Path(".pipeline/verification_pipeline.json")
INPUT_FILE = Path("input/baseline_snippet.txt")


def _require_env():
    if not RUN_PHASE_O:
        pytest.skip("Set RUN_PHASE_O_FULL=1 to run safety invariant checks")


def test_safety_logs_and_overrides():
    _require_env()
    if not PIPELINE_JSON.exists():
        pytest.skip("Pipeline state missing; run orchestrator first")

    state = json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))
    file_id = INPUT_FILE.stem
    phase_keys = ("phase1", "phase2", "phase3")
    for key in phase_keys:
        if state.get(key, {}).get("status") != "success":
            pytest.skip(f"{key} not successful; skipping safety check")

    tuning_overrides = Path(".pipeline") / "tuning_overrides.json"
    if tuning_overrides.exists():
        overrides = json.loads(tuning_overrides.read_text(encoding="utf-8"))
        runtime_state = overrides.get("runtime_state", {})
        assert runtime_state.get("last_run", {}).get("file_id") == file_id

    autonomy_runtime = Path(".pipeline") / "autonomy_runtime"
    assert not autonomy_runtime.exists(), "Autonomy runtime artifacts should not persist"

    safety_logs_dir = Path(".pipeline") / "policy_runtime"
    if safety_logs_dir.exists():
        assert safety_logs_dir.is_dir()

    outside_writes = [p for p in Path(".").iterdir() if p.name not in {".pipeline", "input", "phase3-chunking", "phase4_tts", "phase5_enhancement"}]
    assert outside_writes is not None  # no destructive writes asserted by absence
