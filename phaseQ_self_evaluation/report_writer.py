"""Phase Q: self-evaluation report writer (opt-in, non-blocking)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


def _status_from_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    scores = [
        metrics.get("run_health_score", 0.0),
        metrics.get("stability_score", 0.0),
        metrics.get("repair_effectiveness_score", 0.0),
        metrics.get("autonomy_boundedness_score", 0.0),
    ]
    status = "success"
    if any(s < 0.2 for s in scores):
        status = "critical"
    elif any(s < 0.5 for s in scores):
        status = "warning"
    return {
        "status": status,
        "notes": [],
    }


def write_report(run_id: str, metrics: Dict[str, Any], output_dir: str) -> str:
    """
    Writes metrics to:
      output_dir/reports/self_eval_<run_id>.json
    Returns filepath.
    """
    base = Path(output_dir)
    reports_dir = base / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().isoformat()
    status_block = _status_from_metrics(metrics)
    payload = {
        "id": f"self_eval_{run_id}",
        "timestamp": ts,
        "summary": "Phase Q self-evaluation metrics",
        "signals": status_block,
        "details": {"run_id": run_id, "metrics": metrics},
        "notes": "Informational metrics (no runtime impact).",
        "version": "phaseQ",
    }
    path = reports_dir / f"self_eval_{run_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
