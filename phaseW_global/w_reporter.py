"""Reporter for Phase W (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_phaseW_report(report: dict, base_dir: Path = Path(".pipeline/phaseW/reports")) -> Path:
    """
    Write Phase W report to .pipeline/phaseW/reports/phaseW_<timestamp>.json without overwriting existing files.
    Output schema is normalized:
    {
      "id": "...",
      "timestamp": "...",
      "summary": "...",
      "signals": {...},
      "details": {...},
      "notes": "...",
      "version": "phaseW"
    }
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id = report.get("id") or f"phaseW_{ts}"
    path = base_dir / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{report_id}_{counter}.json"
        counter += 1

    lint = report.get("lint", {})
    consistency = report.get("consistency", {})
    global_analysis = report.get("global_analysis", {})

    payload = {
        "id": report_id,
        "timestamp": report.get("timestamp", ts),
        "summary": report.get("summary", "Phase W global consistency report"),
        "signals": {
            "lint": lint,
            "consistency": consistency,
        },
        "details": {
            "lint": lint,
            "consistency": consistency,
            "global_analysis": global_analysis,
        },
        "notes": report.get("notes", "Phase W global consistency layer"),
        "version": "phaseW",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
