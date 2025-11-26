"""
Trend and regression modeling for Phase J (opt-in, informational only).
"""

from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional


def _extract_series(history: List[Dict[str, Any]], keys: List[str]) -> List[float]:
    out: List[float] = []
    for entry in history:
        current: Any = entry
        for key in keys:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if isinstance(current, (int, float)):
            out.append(float(current))
    return out


def _compute_trend(series: List[float]) -> Dict[str, Any]:
    if len(series) < 2:
        return {"trend_direction": "flat", "slope": 0.0, "confidence": 0.0}
    slope = series[-1] - series[0]
    direction = "flat"
    if slope > 0:
        direction = "up"
    elif slope < 0:
        direction = "down"
    confidence = min(1.0, len(series) / 10.0)
    return {"trend_direction": direction, "slope": slope, "confidence": confidence}


def compute_score_trend(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fits a simple regression (slope, intercept)
    or fallback finite diff.
    Returns:
    {
      "trend_direction": "up" | "down" | "flat",
      "slope": float,
      "confidence": float
    }
    """
    series = _extract_series(history, ["score"])
    if not series:
        series = _extract_series(history, ["payload", "evaluator", "score"])
    return _compute_trend(series)


def compute_reward_trend(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Same as score trend but based on reward logs.
    """
    series = _extract_series(history, ["payload", "reward"])
    return _compute_trend(series)


def compute_anomaly_frequency_trend(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Returns anomaly frequency over rolling windows.
    """
    counts: List[int] = []
    for entry in history:
        anomalies = None
        if isinstance(entry, dict):
            anomalies = entry.get("diagnostics", {}).get("anomalies")
            if anomalies is None:
                anomalies = (entry.get("payload") or {}).get("diagnostics", {}).get("anomalies")
        counts.append(len(anomalies) if isinstance(anomalies, list) else 0)
    if not counts:
        return {"trend_direction": "flat", "slope": 0.0, "confidence": 0.0}
    slope = counts[-1] - counts[0] if len(counts) > 1 else 0.0
    direction = "flat"
    if slope > 0:
        direction = "up"
    elif slope < 0:
        direction = "down"
    confidence = min(1.0, len(counts) / 10.0)
    return {"trend_direction": direction, "slope": slope, "confidence": confidence, "avg": mean(counts)}


def build_combined_trends(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "score_trend": compute_score_trend(history),
        "reward_trend": compute_reward_trend(history),
        "anomaly_trend": compute_anomaly_frequency_trend(history),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
