"""Master Pipeline Test Harness runner (Phase V harness)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from . import orchestration_runner
from . import snapshot_comparator


def run_master_harness(input_path: Path) -> Dict:
    """
    Execute two runs in an isolated tmp pipeline dir and compare snapshots.
    """
    tmp_pipeline_dir = Path(".pipeline_harness_tmp")
    tmp_pipeline_dir.mkdir(parents=True, exist_ok=True)

    initial_run = orchestration_runner.run_full_pipeline(input_path, tmp_pipeline_dir)
    second_run = orchestration_runner.run_full_pipeline(input_path, tmp_pipeline_dir)

    snapshot_before = {
        "phases": [p.get("phase") for p in initial_run["output_json"].get("phases", [])],
        "engine": "xtts_kokoro",
        "chunk_count": len(initial_run["output_json"].get("phases", [])),
    }
    snapshot_after = {
        "phases": [p.get("phase") for p in second_run["output_json"].get("phases", [])],
        "engine": "xtts_kokoro",
        "chunk_count": len(second_run["output_json"].get("phases", [])),
    }
    comparison = snapshot_comparator.compare_snapshots(snapshot_before, snapshot_after)

    overall_status = "pass" if (
        initial_run.get("status") == "success"
        and second_run.get("status") == "success"
        and comparison.get("schema_valid")
    ) else "fail"

    return {
        "initial_run": initial_run,
        "second_run": second_run,
        "comparison": comparison,
        "overall_status": overall_status,
    }
