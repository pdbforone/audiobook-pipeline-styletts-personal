"""Master Pipeline Test Harness: orchestration runner (Phase V harness).

This runner simulates phase execution in an isolated temp pipeline directory
without mutating the real `.pipeline/`. It is intentionally lightweight and
non-destructive.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Union


def _run_command(cmd: List[str], cwd: Path | None = None) -> Dict[str, Union[str, int]]:
    """Execute a command and capture stdout/stderr/returncode."""
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }
    except Exception as exc:  # noqa: BLE001
        return {"stdout": "", "stderr": str(exc), "returncode": 1}


def run_phase(phase_number: int, input_path: Path, tmp_pipeline_dir: Path) -> Dict:
    """
    Run a single phase in isolation using a temp pipeline dir.
    This harness does not mutate the real `.pipeline/`.
    """
    tmp_pipeline_dir.mkdir(parents=True, exist_ok=True)
    # Simulate execution; prefer a lightweight python -c for portability.
    cmd = ["python", "-c", f"print('phase {phase_number} executed')"]
    result = _run_command(cmd, cwd=tmp_pipeline_dir)
    status = "success" if result["returncode"] == 0 else "failure"
    output_json = {
        "phase": phase_number,
        "input": str(input_path),
        "tmp_pipeline_dir": str(tmp_pipeline_dir),
    }
    return {
        "status": status,
        "phase": phase_number,
        "returncode": result["returncode"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "output_json": output_json,
    }


def run_full_pipeline(input_path: Path, tmp_pipeline_dir: Path) -> Dict:
    """
    Run phases 1-6 sequentially within the harness.
    """
    phases: List[Dict] = []
    overall_status = "success"
    for ph in range(1, 7):
        res = run_phase(ph, input_path, tmp_pipeline_dir)
        phases.append(res)
        if res["status"] != "success":
            overall_status = "failure"
            break
    return {
        "status": overall_status,
        "phase": "full",
        "returncode": 0 if overall_status == "success" else 1,
        "stdout": "\n".join([p.get("stdout", "") for p in phases]),
        "stderr": "\n".join([p.get("stderr", "") for p in phases if p.get("stderr")]),
        "output_json": {"phases": phases, "input": str(input_path), "tmp_pipeline_dir": str(tmp_pipeline_dir)},
    }
