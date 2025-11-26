"""Audit reporter for Phase T (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_audit_report(report: dict, base_dir: Path = Path(".pipeline/audit/reports")) -> Path:
    """
    Write audit report with normalized schema; never overwrite existing files.
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id = report.get("id") or f"T_{ts}"
    path = base_dir / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{report_id}_{counter}.json"
        counter += 1

    kernel = report.get("kernel", {})
    synthesized = report.get("synthesized", {})
    risk = report.get("risk", {})

    payload = {
        "id": report_id,
        "timestamp": report.get("created_at", ts),
        "summary": report.get("summary", "Phase T audit"),
        "signals": {
            "risk": risk,
        },
        "details": {
            "run_id": report.get("run_id"),
            "kernel": kernel,
            "synthesized": synthesized,
            "risk": risk,
        },
        "notes": report.get("notes", "Audit report (read-only)."),
        "version": "phaseT",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
