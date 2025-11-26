"""Meta reporter for Phase Z (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_meta_report(kernel: dict, invariants: dict, deps: dict, health: dict, base_dir: Path = Path(".pipeline/meta/reports")) -> Path:
    """
    Write meta report to .pipeline/meta/reports/<id>.json with normalized schema:
    {
      "id": "...",
      "timestamp": "...",
      "summary": "...",
      "signals": {...},
      "details": {...},
      "notes": "...",
      "version": "phaseZ"
    }
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id = f"phaseZ_{ts}"
    path = base_dir / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{report_id}_{counter}.json"
        counter += 1

    payload = {
        "id": report_id,
        "timestamp": ts,
        "summary": "Phase Z meta diagnostics report",
        "signals": {
            "invariants": invariants,
            "dependencies": deps,
            "health": health,
        },
        "details": {
            "meta_summary": kernel,
            "invariants": invariants,
            "dependencies": deps,
            "phase_health": health,
        },
        "notes": "Meta diagnostics (read-only, additive).",
        "version": "phaseZ",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
