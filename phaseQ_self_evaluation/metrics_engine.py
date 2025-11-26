"""Phase Q: self-evaluation metrics engine (pure, opt-in)."""

from __future__ import annotations

from typing import Dict, Any


def _safe_float(value, default=0.5) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def compute_metrics(run_summary: Dict[str, Any], long_horizon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns:
      {
        "run_health_score": float,
        "stability_score": float,
        "repair_effectiveness_score": float,
        "autonomy_boundedness_score": float,
        "raw": {...all inputs normalized...}
      }
    """
    raw = {
        "run_summary": run_summary or {},
        "long_horizon": long_horizon or {},
    }

    health = _safe_float(run_summary.get("health", 0.8) if isinstance(run_summary, dict) else 0.8)
    stability = _safe_float(long_horizon.get("stability", 0.7) if isinstance(long_horizon, dict) else 0.7)
    repair = _safe_float(run_summary.get("repairs", {}).get("success_rate", 0.5) if isinstance(run_summary, dict) else 0.5)
    autonomy = _safe_float(long_horizon.get("autonomy", {}).get("boundedness", 0.9) if isinstance(long_horizon, dict) else 0.9)

    return {
        "run_health_score": health,
        "stability_score": stability,
        "repair_effectiveness_score": repair,
        "autonomy_boundedness_score": autonomy,
        "raw": raw,
    }
