"""
Multi-run drift detection for Phase J (opt-in, additive-only).
"""

from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List


def _slope(series: List[float]) -> float:
    if len(series) < 2:
        return 0.0
    return series[-1] - series[0]


def detect_drift(run_history: List[Dict[str, Any]], trend_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Structured drift detection output.
    """
    if not run_history or len(run_history) < 3:
        return {
            "drift_detected": False,
            "severity": 0.0,
            "metrics": {
                "reward_slope": 0.0,
                "evaluator_slope": 0.0,
                "anomaly_rate": 0.0,
            },
            "details": "insufficient_history",
        }

    scores: List[float] = []
    rewards: List[float] = []
    anomalies: List[int] = []
    for entry in run_history:
        if not isinstance(entry, dict):
            continue
        score = entry.get("score")
        if score is None:
            score = (entry.get("payload") or {}).get("evaluator", {}).get("score")
        if isinstance(score, (int, float)):
            scores.append(float(score))
        reward_val = (entry.get("payload") or {}).get("reward")
        if isinstance(reward_val, (int, float)):
            rewards.append(float(reward_val))
        diag = entry.get("diagnostics", {}).get("anomalies")
        if diag is None:
            diag = (entry.get("payload") or {}).get("diagnostics", {}).get("anomalies")
        anomalies.append(len(diag) if isinstance(diag, list) else 0)

    evaluator_slope = _slope(scores)
    reward_slope = _slope(rewards)
    anomaly_rate = mean(anomalies) if anomalies else 0.0

    drift_detected = any(
        [
            evaluator_slope < 0,
            reward_slope < 0,
            anomaly_rate > 0,
        ]
    )
    severity = 0.0
    if drift_detected:
        severity = min(1.0, (abs(evaluator_slope) + abs(reward_slope) + anomaly_rate) / 10.0)

    details = []
    if evaluator_slope < 0:
        details.append("evaluator_down")
    if reward_slope < 0:
        details.append("reward_down")
    if anomaly_rate > 0:
        details.append("anomalies_present")

    return {
        "drift_detected": drift_detected,
        "severity": float(severity),
        "metrics": {
            "reward_slope": float(reward_slope),
            "evaluator_slope": float(evaluator_slope),
            "anomaly_rate": float(anomaly_rate),
        },
        "details": ", ".join(details) if details else "stable",
    }
