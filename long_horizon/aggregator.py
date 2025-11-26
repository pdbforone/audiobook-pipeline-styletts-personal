"""
Long-horizon run aggregation for Phase I (additive, opt-in).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_all_runs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Load run summaries from .pipeline/run/* directories.
    Returns list of dicts sorted oldest→newest.
    """
    run_root = Path(".pipeline") / "run"
    if not run_root.exists():
        return []

    runs: List[Dict[str, Any]] = []
    candidates = sorted(run_root.glob("*"), key=lambda p: p.stat().st_mtime)[:limit]
    for run_dir in candidates:
        if not run_dir.is_dir():
            continue
        summary_path = run_dir / "run_summary.json"
        if not summary_path.exists():
            continue
        try:
            runs.append(json.loads(summary_path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return runs


def _trend(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"slope": None, "moving_avg": None, "stability": None}
    moving_avg = sum(values) / len(values)
    slope = None
    if len(values) >= 2:
        slope = values[-1] - values[0]
    diffs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    stability = 1.0 / (1.0 + (sum(diffs) / len(diffs))) if diffs else 1.0
    return {"slope": slope, "moving_avg": moving_avg, "stability": stability}


def aggregate_long_horizon_history(run_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Produce long-horizon metrics:
      - evaluator_avg_last_10
      - evaluator_trend_last_10
      - reward_avg_last_10
      - reward_trend_last_10
      - anomaly_frequency_last_10
    Returns a JSON-serializable dict.
    """
    tail = run_summaries[-10:] if len(run_summaries) > 10 else run_summaries
    scores: List[float] = []
    rewards: List[float] = []
    anomalies: List[int] = []

    for entry in tail:
        eval_score = entry.get("score") or (entry.get("payload") or {}).get("evaluator", {}).get("score")
        if isinstance(eval_score, (int, float)):
            scores.append(float(eval_score))
        reward = (entry.get("payload") or {}).get("reward")
        if isinstance(reward, (int, float)):
            rewards.append(float(reward))
        diag_anomalies = (
            (entry.get("payload") or {}).get("diagnostics", {}).get("anomalies")
            if isinstance(entry.get("payload"), dict)
            else entry.get("diagnostics", {}).get("anomalies")
        )
        anomalies.append(len(diag_anomalies) if isinstance(diag_anomalies, list) else 0)

    evaluator_avg = sum(scores) / len(scores) if scores else None
    reward_avg = sum(rewards) / len(rewards) if rewards else None
    anomaly_freq = sum(anomalies) / len(anomalies) if anomalies else None

    return {
        "runs_considered": len(tail),
        "evaluator_avg_last_10": evaluator_avg,
        "evaluator_trend_last_10": _trend(scores),
        "reward_avg_last_10": reward_avg,
        "reward_trend_last_10": _trend(rewards),
        "anomaly_frequency_last_10": anomaly_freq,
    }


def write_long_horizon_snapshot(snapshot: Dict[str, Any], timestamp: str) -> Optional[Path]:
    """
    Write long-horizon snapshot to:
    .pipeline/long_horizon/long_horizon_<timestamp>.json
    """
    try:
        out_dir = Path(".pipeline") / "long_horizon"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"long_horizon_{timestamp}.json"
        out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        return out_path
    except Exception:
        return None
