"""Health reporter for Phase T (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_consistency_report(
    *,
    run_id: str,
    consistency: dict,
    drift: dict,
    base_dir: Path = Path(".pipeline/consistency/reports"),
) -> Path:
    """
    Writes a normalized consistency report; never overwrites existing files.
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = f"consistency_{run_id}_{ts}"
    path = base_dir / f"{base_name}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{base_name}_{counter}.json"
        counter += 1

    payload = {
        "id": base_name,
        "timestamp": ts,
        "summary": "Phase T consistency and drift report",
        "signals": {
            "consistency": consistency,
            "drift": drift,
        },
        "details": {
            "run_id": run_id,
            "consistency": consistency,
            "drift": drift,
        },
        "notes": "Read-only consistency layer; no decisions altered.",
        "version": "phaseT",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
