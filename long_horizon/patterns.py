"""
Cross-run pattern extraction for Phase I (additive, opt-in).
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any, Dict, List, Optional


def _extract_series(summaries: List[Dict[str, Any]], key_path: List[str]) -> List[float]:
    series: List[float] = []
    for entry in summaries:
        current = entry
        for key in key_path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if isinstance(current, (int, float)):
            series.append(float(current))
    return series


def _slope(series: List[float]) -> Optional[float]:
    if len(series) < 2:
        return None
    return series[-1] - series[0]


def compute_evaluator_trend(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build trend line of evaluator scores across N runs.
    Outputs slope, moving average, and stability index.
    """
    scores = _extract_series(summaries, ["score"])
    if not scores:
        scores = _extract_series(summaries, ["payload", "evaluator", "score"])
    moving_avg = mean(scores) if scores else None
    slope_val = _slope(scores)
    volatility = pstdev(scores) if len(scores) > 1 else None
    stability = 1.0 / (1.0 + volatility) if volatility else (1.0 if scores else None)
    return {"slope": slope_val, "moving_avg": moving_avg, "stability": stability}


def compute_reward_trend(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Derive long-run reward trend: slope, variance, volatility.
    """
    rewards = _extract_series(summaries, ["payload", "reward"])
    moving_avg = mean(rewards) if rewards else None
    slope_val = _slope(rewards)
    volatility = pstdev(rewards) if len(rewards) > 1 else None
    variance = volatility**2 if volatility is not None else None
    return {"slope": slope_val, "moving_avg": moving_avg, "variance": variance, "volatility": volatility}


def compute_anomaly_pattern(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Frequency of diagnostics anomalies per run.
    """
    counts: List[int] = []
    for entry in summaries:
        anomalies = None
        if isinstance(entry, dict):
            anomalies = entry.get("diagnostics", {}).get("anomalies")
            if anomalies is None:
                anomalies = (entry.get("payload") or {}).get("diagnostics", {}).get("anomalies")
        counts.append(len(anomalies) if isinstance(anomalies, list) else 0)
    freq = mean(counts) if counts else None
    return {"average_anomalies": freq, "samples": len(counts)}


def build_cross_run_patterns(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "evaluator_trend": compute_evaluator_trend(summaries),
        "reward_trend": compute_reward_trend(summaries),
        "anomaly_pattern": compute_anomaly_pattern(summaries),
    }
