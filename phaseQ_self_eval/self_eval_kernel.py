"""Phase Q self-evaluation kernel (heuristic, read-only, opt-in)."""

from __future__ import annotations

from typing import Dict


def _clamp(val: float) -> float:
    try:
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return 0.0


def score_dimensions(run_metrics: Dict) -> Dict[str, float]:
    """Return {coherence, alignment, stability, efficiency} as floats 0–1."""
    metrics = run_metrics or {}
    return {
        "coherence": _clamp(metrics.get("coherence", 0.75)),
        "alignment": _clamp(metrics.get("alignment", 0.75)),
        "stability": _clamp(metrics.get("stability", 0.7)),
        "efficiency": _clamp(metrics.get("efficiency", 0.7)),
    }


def generate_overall_rating(dimensions: Dict[str, float]) -> float:
    """Return weighted average rating 0–1."""
    dims = dimensions or {}
    if not dims:
        return 0.0
    weights = {
        "coherence": 0.3,
        "alignment": 0.25,
        "stability": 0.25,
        "efficiency": 0.2,
    }
    total = 0.0
    weight_sum = 0.0
    for key, weight in weights.items():
        total += weight * _clamp(dims.get(key, 0.0))
        weight_sum += weight
    return total / weight_sum if weight_sum else 0.0


def evaluate_run(phase_outputs: Dict) -> Dict:
    """
    Produce:
    {
      "dimensions": {...},
      "overall_rating": float,
      "notes": str
    }
    """
    metrics = phase_outputs or {}
    dimensions = score_dimensions(metrics.get("metrics", metrics))
    overall = generate_overall_rating(dimensions)
    notes = "Informational self-evaluation; does not affect pipeline execution."
    return {
        "dimensions": dimensions,
        "overall_rating": overall,
        "notes": notes,
    }
