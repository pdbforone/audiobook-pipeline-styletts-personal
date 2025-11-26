"""
Phase J: Long-horizon memory aggregation (opt-in, informational only).
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional


def aggregate_multi_run_history(run_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Produces multi-run aggregated statistics:
    - avg evaluator score over 10+ runs
    - avg reward trend
    - anomaly frequency
    - stability drift
    - rolling windows (last 5, last 10)
    - evaluator variance bands
    """
    if not run_history:
        return {
            "scores": {},
            "rewards": {},
            "anomaly_rate": None,
            "variance": None,
            "drift": None,
            "sample_size": 0,
        }

    scores = []
    rewards = []
    anomalies = []
    for entry in run_history:
        eval_score = (entry.get("payload") or {}).get("evaluator", {}).get("score") if isinstance(entry, dict) else None
        if eval_score is None:
            eval_score = entry.get("score") if isinstance(entry, dict) else None
        if isinstance(eval_score, (int, float)):
            scores.append(float(eval_score))

        reward_val = (entry.get("payload") or {}).get("reward") if isinstance(entry, dict) else None
        if isinstance(reward_val, (int, float)):
            rewards.append(float(reward_val))

        diag = None
        if isinstance(entry, dict):
            diag = entry.get("diagnostics", {}).get("anomalies")
            if diag is None:
                diag = (entry.get("payload") or {}).get("diagnostics", {}).get("anomalies")
        anomalies.append(len(diag) if isinstance(diag, list) else 0)

    def _window_stats(values: List[float], window: int) -> Dict[str, Optional[float]]:
        subset = values[-window:] if values else []
        if not subset:
            return {"avg": None, "min": None, "max": None}
        return {"avg": sum(subset) / len(subset), "min": min(subset), "max": max(subset)}

    variance = pstdev(scores) if len(scores) > 1 else None
    drift = None
    if scores:
        drift = scores[-1] - scores[0] if len(scores) > 1 else 0.0

    return {
        "scores": {
            "overall_avg": mean(scores) if scores else None,
            "last5": _window_stats(scores, 5),
            "last10": _window_stats(scores, 10),
        },
        "rewards": {
            "overall_avg": mean(rewards) if rewards else None,
            "last5": _window_stats(rewards, 5),
            "last10": _window_stats(rewards, 10),
        },
        "anomaly_rate": mean(anomalies) if anomalies else None,
        "variance": variance,
        "drift": drift,
        "sample_size": len(run_history),
    }


def write_long_horizon_profile(profile: Dict[str, Any], timestamp: str) -> None:
    """
    Writes JSON to .pipeline/long_horizon/long_horizon_<timestamp>.json
    """
    try:
        out_dir = Path(".pipeline") / "long_horizon"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"long_horizon_{timestamp}.json"
        out_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    except Exception:
        return
