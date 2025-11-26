"""
Probabilistic predictions for Phase J (opt-in, informational only).
"""

from __future__ import annotations

from typing import Any, Dict, List


def _prob_from_trend(trend: Dict[str, Any]) -> float:
    slope = trend.get("slope")
    if not isinstance(slope, (int, float)):
        return 0.5
    if slope > 0:
        return min(1.0, 0.5 + min(abs(slope), 1.0) * 0.25)
    if slope < 0:
        return max(0.0, 0.5 - min(abs(slope), 1.0) * 0.25)
    return 0.5


def forecast_outcomes(history: List[Dict[str, Any]], trends: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce soft forecasts:
    - probability of improvement
    - probability of regression
    - stability risk
    - anomaly risk
    Returns:
    {
      "prob_improve": float,
      "prob_regress": float,
      "stability_risk": float,
      "anomaly_risk": float,
      "notes": [...]
    }
    """
    score_trend = trends.get("score_trend", {}) if isinstance(trends, dict) else {}
    reward_trend = trends.get("reward_trend", {}) if isinstance(trends, dict) else {}
    anomaly_trend = trends.get("anomaly_trend", {}) if isinstance(trends, dict) else {}

    prob_improve = _prob_from_trend(score_trend)
    prob_regress = 1.0 - prob_improve if prob_improve is not None else 0.5

    stability_risk = max(0.0, min(1.0, abs(score_trend.get("slope") or 0.0) * 0.1))
    anomaly_risk = _prob_from_trend({"slope": anomaly_trend.get("slope")}) if anomaly_trend else 0.5

    return {
        "prob_improve": prob_improve,
        "prob_regress": prob_regress,
        "stability_risk": stability_risk,
        "anomaly_risk": anomaly_risk,
        "notes": ["Forecast is informational only; no automatic actions are taken."],
    }
