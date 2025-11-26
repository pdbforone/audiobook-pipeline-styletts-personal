"""Evidence ingestion for Phase R (opt-in, read-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ingest_all(run_id: str, base_dir: str | Path = ".pipeline") -> dict:
    base = Path(base_dir)
    policy_logs = []
    bench = []
    observations = []
    self_eval = []

    policy_dir = base / "policy_logs"
    bench_dir = base / "benchmark_history"
    obs_dir = base / "research" / "observations"
    self_eval_dir = base / "self_eval" / "reports"
    error_registry = _load_json(base / "error_registry.json")

    if policy_dir.exists():
        for p in sorted(policy_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            policy_logs.append({"path": str(p), "data": _load_json(p)})

    if bench_dir.exists():
        for p in sorted(bench_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            bench.append({"path": str(p), "data": _load_json(p)})

    if obs_dir.exists():
        for p in sorted(obs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            observations.append({"path": str(p), "data": _load_json(p)})

    if self_eval_dir.exists():
        for p in sorted(self_eval_dir.glob("self_eval_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            self_eval.append({"path": str(p), "data": _load_json(p)})

    return {
        "run_id": run_id,
        "policy_logs": policy_logs,
        "benchmark_history": bench,
        "error_registry": error_registry,
        "self_eval_reports": self_eval,
        "observations": observations,
        "runs_analyzed": len(policy_logs) + len(self_eval),
    }
