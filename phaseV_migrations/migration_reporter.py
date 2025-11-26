"""Report writers for Phase V migrations (opt-in)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def write_plan_report(plan: Dict[str, Any], base_dir: Path = Path(".pipeline/migrations")) -> Path:
    """
    Write a normalized migration plan report under .pipeline/migrations/reports, while also persisting
    the legacy plan artifact under .pipeline/migrations/plans for backward compatibility.
    """
    base_dir = Path(base_dir)
    reports_dir = base_dir / "reports"
    plans_dir = base_dir / "plans"
    reports_dir.mkdir(parents=True, exist_ok=True)
    plans_dir.mkdir(parents=True, exist_ok=True)
    ts = _timestamp()

    report_id = f"plan_{ts}"
    normalized_path = reports_dir / f"{report_id}.json"
    counter = 1
    while normalized_path.exists():
        normalized_path = reports_dir / f"{report_id}_{counter}.json"
        counter += 1

    payload = {
        "id": report_id,
        "timestamp": ts,
        "summary": "Planned migrations (dry-run safe).",
        "signals": {"targets": [entry.get("target") for entry in plan.get("plans", [])] if isinstance(plan, dict) else []},
        "details": plan,
        "notes": "Phase V migration plan (non-destructive).",
        "version": "phaseV",
    }
    normalized_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    legacy_path = plans_dir / f"{report_id}.json"
    counter = 1
    while legacy_path.exists():
        legacy_path = plans_dir / f"{report_id}_{counter}.json"
        counter += 1
    legacy_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return normalized_path


def write_apply_report(result: Dict[str, Any], base_dir: Path = Path(".pipeline/migrations")) -> Path:
    base_dir = Path(base_dir)
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = _timestamp()

    report_id = f"apply_{ts}"
    path = reports_dir / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = reports_dir / f"{report_id}_{counter}.json"
        counter += 1

    payload = {
        "id": report_id,
        "timestamp": ts,
        "summary": "Migration apply results (non-destructive).",
        "signals": {"applied": [entry.get("target") for entry in result.get("applied", [])] if isinstance(result, dict) else []},
        "details": result,
        "notes": "Phase V migration apply summary.",
        "version": "phaseV",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
