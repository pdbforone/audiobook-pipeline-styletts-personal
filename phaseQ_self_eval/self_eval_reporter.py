"""Phase Q: self-evaluation reporter (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

BASE_DIR = Path(".pipeline") / "self_eval" / "reports"


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def write_self_eval_report(
    run_id: str,
    kernel_result: Dict,
    overall_rating: float,
    fusion_result: Dict,
    explanation: Dict,
    *,
    output_dir: Path | None = None,
) -> Path:
    """
    Write normalized self-evaluation report.
    Schema:
    {
      "id": "...",
      "timestamp": "...",
      "summary": "...",
      "signals": {...},
      "details": {...},
      "notes": "...",
      "version": "phaseQ"
    }
    """
    base = Path(output_dir) if output_dir else BASE_DIR
    base.mkdir(parents=True, exist_ok=True)

    ts = _timestamp()
    base_name = f"self_eval_{run_id}_{ts}"
    path = base / f"{base_name}.json"
    counter = 1
    while path.exists():
        path = base / f"{base_name}_{counter}.json"
        counter += 1

    dims = (kernel_result or {}).get("dimensions") if isinstance(kernel_result, dict) else None
    overall = overall_rating
    # Backward compatibility: if overall not provided separately, derive from kernel_result
    if overall is None and isinstance(kernel_result, dict):
        overall = kernel_result.get("overall_rating")

    signals = (fusion_result or {}).get("signals", {})

    payload = {
        "id": base_name,
        "timestamp": ts,
        "summary": f"Self-evaluation for run {run_id}",
        "signals": signals,
        "details": {
            "run_id": run_id,
            "dimensions": dims,
            "overall_rating": overall,
            "kernel": kernel_result,
            "fusion": fusion_result,
            "explanation": explanation.get("explanation") if explanation else None,
            "dimension_breakdown": (explanation or {}).get("dimension_breakdown"),
        },
        "notes": "Phase Q self-evaluation (informational only).",
        "version": "phaseQ",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
