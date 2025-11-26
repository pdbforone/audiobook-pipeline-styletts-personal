"""Meta reporter for Phase X (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_meta_report(report: dict, base_dir: Path = Path(".pipeline/meta/reports")) -> Path:
    """
    Write meta report to .pipeline/meta/reports/<id>.json with normalized schema:
    {
      "id": "...",
      "timestamp": "...",
      "summary": "...",
      "signals": {...},
      "details": {...},
      "notes": "...",
      "version": "phaseX"
    }
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id = report.get("id") or f"phaseX_{ts}"
    path = base_dir / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{report_id}_{counter}.json"
        counter += 1

    kernel = report.get("kernel", {})
    fusion = report.get("fusion", {})
    ranking = report.get("ranking", {})

    payload = {
        "id": report_id,
        "timestamp": report.get("timestamp", ts),
        "summary": report.get("summary", "Phase X meta report"),
        "signals": {
            "kernel": kernel,
            "fusion": fusion,
            "ranking": ranking,
        },
        "details": {
            "kernel": kernel,
            "fusion": fusion,
            "ranking": ranking,
        },
        "notes": report.get("notes", "Meta-evaluator outputs (read-only)."),
        "version": "phaseX",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
