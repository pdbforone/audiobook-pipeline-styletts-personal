"""Self-heal reporter for Phase Y (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_heal_report(report: dict, base_dir: Path = Path(".pipeline/phaseY/reports")) -> Path:
    """
    Write heal report to .pipeline/phaseY/reports/<id>.json without overwriting existing files.
    Normalized schema:
    {
      "id": "...",
      "timestamp": "...",
      "summary": "...",
      "signals": {...},
      "details": {...},
      "notes": "...",
      "version": "phaseY"
    }
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id = report.get("id") or f"phaseY_{ts}"
    path = base_dir / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{report_id}_{counter}.json"
        counter += 1

    kernel = report.get("kernel", {})
    classification = report.get("classification", {})
    suggestions = report.get("suggestions", {})
    severity = report.get("overall_severity", "low")

    payload = {
        "id": report_id,
        "timestamp": report.get("timestamp", ts),
        "summary": report.get("summary", "Phase Y self-heal report"),
        "signals": {
            "severity": severity,
            "kernel": kernel,
            "classification": classification,
        },
        "details": {
            "run_id": report.get("run_id", ""),
            "kernel": kernel,
            "classification": classification,
            "suggestions": suggestions,
            "overall_severity": severity,
        },
        "notes": report.get("notes", "Informational only; no automatic actions."),
        "version": "phaseY",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
