"""Review reporter for Phase S (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_review_report(run_id: str, review: dict, aggregate: dict, base_dir: Path = Path(".pipeline/review/reports")) -> Path:
    """
    Persist review outputs using the normalized schema and never overwrite existing files.
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id = f"review_{run_id or ts}"
    path = base_dir / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{report_id}_{counter}.json"
        counter += 1

    payload = {
        "id": report_id,
        "timestamp": ts,
        "summary": f"Phase S review for run {run_id}",
        "signals": {
            "rating": aggregate.get("rating") if isinstance(aggregate, dict) else None,
            "status": aggregate.get("status") if isinstance(aggregate, dict) else None,
        },
        "details": {
            "run_id": run_id,
            "review": review,
            "aggregate": aggregate,
        },
        "notes": "Review aggregation (read-only).",
        "version": "phaseS",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
