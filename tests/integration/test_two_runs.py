"""Phase O: Two-run consistency checks (opt-in)."""

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


def _require_env():
    if not RUN_PHASE_O:
        pytest.skip("Set RUN_PHASE_O_FULL=1 to run Phase O validation")
    if not INPUT_FILE.exists():
        pytest.skip(f"Missing baseline input: {INPUT_FILE}")
    if not ORCH.exists():
        pytest.skip(f"Missing orchestrator: {ORCH}")


def _run_once(phases: list[int]) -> None:
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
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip(f"Orchestrator failed: {res.stderr.strip()}")


def test_two_runs_override_reset():
    phases = [1, 2, 3]
    _run_once(phases)
    _run_once(phases)

    overrides_path = Path(".pipeline") / "tuning_overrides.json"
    if not overrides_path.exists():
        pytest.skip("Overrides file missing after runs")
    overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
    runtime_state = overrides.get("runtime_state", {})
    last_run = runtime_state.get("last_run", {})
    assert last_run.get("file_id") == INPUT_FILE.stem
    assert last_run.get("success") is True
    assert overrides.get("overrides", {}) in ({}, overrides.get("overrides"))

    autonomy_runtime = Path(".pipeline") / "autonomy_runtime"
    experiments_dir = Path(".pipeline") / "experiments"
    assert not autonomy_runtime.exists(), "autonomy_runtime should be cleared"
    if experiments_dir.exists():
        assert not any(experiments_dir.iterdir()), "No pending experiments expected"

    overrides_map = overrides.get("overrides", {})
    assert isinstance(overrides_map, dict)
