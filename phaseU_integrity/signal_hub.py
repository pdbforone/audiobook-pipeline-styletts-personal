"""Signal hub for Phase U (opt-in, read-only)."""

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


def collect_signals(run_id: str | None, base_dir: str | Path = ".pipeline") -> dict:
    """
    Gather safety-related signals across the pipeline.
    Schema:
    {
      "run_id": "...",
      "signals": {
        "readiness": {...},
        "stability": {...},
        "drift": {...},
        "self_eval": {...},
        "retrospection": {...},
        "review": {...},
        "audit": {...},
        "planner": {...},
        "policy_kernel": {...},
        "engine_capabilities": {...}
      }
    }
    """
    base = Path(base_dir)
    signals = {
        "readiness": _load_json(base / "readiness" / "readiness.json"),
        "stability": _load_json(base / "stability_profiles" / "latest.json"),
        "drift": _load_json(base / "drift" / "drift.json"),
        "self_eval": _load_json(base / "self_eval" / "reports" / "latest.json"),
        "retrospection": _load_json(base / "research" / "retro_reports" / "latest.json"),
        "review": _load_json(base / "review" / "reports" / "latest.json"),
        "audit": _load_json(base / "audit" / "reports" / "latest.json"),
        "planner": _load_json(base / "policy_logs" / "latest.json"),
        "policy_kernel": _load_json(base / "policy_runtime" / "last_run_summary.json"),
        "engine_capabilities": _load_json(base / "engine_capabilities.json"),
    }
    return {"run_id": run_id, "signals": signals}
