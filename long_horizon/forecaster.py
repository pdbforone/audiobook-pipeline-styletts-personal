"""
Forecasting utilities for Phase I (opt-in, informational only).
"""

from __future__ import annotations

from typing import Any, Dict


def _prob_from_slope(slope: float | None) -> float:
    if slope is None:
        return 0.5
    if slope > 0:
        return min(1.0, 0.5 + min(abs(slope), 1.0) * 0.25)
    if slope < 0:
        return max(0.0, 0.5 - min(abs(slope), 1.0) * 0.25)
    return 0.5


def forecast_improvement_probability(patterns: Dict[str, Any]) -> float:
    """
    Produces a scalar probability (0–1) representing likelihood of
    evaluator improvement over next N runs based on trend slope/volatility.
    """
    evaluator = (patterns or {}).get("evaluator_trend", {}) or {}
    slope = evaluator.get("slope")
    base = _prob_from_slope(slope)
    return float(base)


def forecast_risk_of_regression(patterns: Dict[str, Any]) -> float:
    """
    Probability (0–1) that evaluator or reward drops given negative trends.
    """
    evaluator = (patterns or {}).get("evaluator_trend", {}) or {}
    reward = (patterns or {}).get("reward_trend", {}) or {}
    slope_eval = evaluator.get("slope")
    slope_reward = reward.get("slope")
    risk = 0.5
    if isinstance(slope_eval, (int, float)) and slope_eval < 0:
        risk += min(abs(slope_eval), 1.0) * 0.25
    if isinstance(slope_reward, (int, float)) and slope_reward < 0:
        risk += min(abs(slope_reward), 1.0) * 0.25
    return float(max(0.0, min(1.0, risk)))


def build_forecast(patterns: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns:
    {
      "prob_improvement": float,
      "prob_regression": float,
      "notes": str
    }
    """
    prob_improve = forecast_improvement_probability(patterns)
    prob_regress = forecast_risk_of_regression(patterns)
    notes = "Forecast is informational only; does not alter pipeline behavior."
    return {
        "prob_improvement": prob_improve,
        "prob_regression": prob_regress,
        "notes": notes,
    }
