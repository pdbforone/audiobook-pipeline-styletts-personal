"""
Readiness assessment for future autonomous mode (reporting only, opt-in).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def assess_readiness(
    evaluator_summary: Dict[str, Any],
    diagnostics_summary: Dict[str, Any],
    benchmark_history: Any,
    recent_rewards: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Returns readiness report without enabling autonomy.
    """
    reasons: List[str] = []
    ready = True

    if config.get("require_recent_success", True):
        score = evaluator_summary.get("score")
        if not isinstance(score, (int, float)) or score < 60:
            ready = False
            reasons.append("Insufficient evaluator score")

    if config.get("require_no_anomalies", True):
        anomalies = diagnostics_summary.get("diagnostics", {}).get("anomalies") if isinstance(diagnostics_summary, dict) else None
        if anomalies:
            ready = False
            reasons.append("Diagnostics anomalies present")

    if config.get("require_stable_benchmarks", True):
        if not benchmark_history:
            ready = False
            reasons.append("No benchmark history")

    if config.get("require_positive_reward", False):
        if recent_rewards:
            latest = recent_rewards[0].get("reward")
            if latest is not None and latest < 0:
                ready = False
                reasons.append("Latest reward is negative")

    return {
        "ready": ready,
        "reasons": reasons,
        "metrics": {
            "evaluator_score": evaluator_summary.get("score"),
            "reward_samples": [r.get("reward") for r in recent_rewards],
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def check_readiness(
    evaluator_summary: Dict[str, Any],
    diagnostics_summary: Dict[str, Any],
    rewards: List[Dict[str, Any]],
    benchmark_history: Any,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Readiness check for Phase L safety (reporting only).
    """
    reasons: List[str] = []
    ready = True

    min_reward_avg = config.get("min_reward_avg", 0.0)
    if config.get("require_no_anomalies", True):
        anomalies = diagnostics_summary.get("diagnostics", {}).get("anomalies") if isinstance(diagnostics_summary, dict) else None
        if anomalies:
            ready = False
            reasons.append("Anomalies detected")

    if config.get("require_stable_benchmarks", True):
        if not benchmark_history:
            ready = False
            reasons.append("Missing benchmark history")

    if rewards:
        avg_reward = sum(r.get("reward", 0.0) for r in rewards if isinstance(r.get("reward"), (int, float))) / max(
            1, len(rewards)
        )
        if avg_reward < min_reward_avg:
            ready = False
            reasons.append("Reward average below threshold")
    else:
        if config.get("require_positive_reward", False):
            ready = False
            reasons.append("No rewards available to assess")

    return {
        "ready": ready,
        "reasons": reasons,
        "metrics": {
            "evaluator_score": evaluator_summary.get("score"),
            "reward_count": len(rewards),
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
