"""Integrity reporter for Phase U (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_integrity_report(report: dict, base_dir: str | Path = ".pipeline/safety_integrity/reports/") -> Path:
    """
    Write a timestamped JSON report using normalized schema:
    {
      "id": "...",
      "timestamp": "...",
      "summary": "...",
      "signals": {...},
      "details": {...},
      "notes": "...",
      "version": "phaseU"
    }
    Never overwrite existing files.
    """
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id = report.get("id") or f"integrity_{ts}"
    path = base / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = base / f"{report_id}_{counter}.json"
        counter += 1

    signals = report.get("signals", {})
    integrity = report.get("integrity", {})

    payload = {
        "id": report_id,
        "timestamp": report.get("created_at", ts),
        "summary": report.get("summary", "Phase U integrity signals"),
        "signals": signals or {"integrity": integrity},
        "details": {
            "run_id": report.get("run_id"),
            "summary": report.get("summary") or {},
            "signals": signals,
            "integrity": integrity,
        },
        "notes": report.get("notes", "Phase U integrity report (read-only)."),
        "version": "phaseU",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
