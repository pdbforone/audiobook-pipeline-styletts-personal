"""
Reinforcement signals (opt-in; feedback only).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

REWARDS_DIR = Path(".pipeline") / "rewards"
REWARDS_DIR.mkdir(parents=True, exist_ok=True)


def compute_reward(
    evaluator_summary: Dict[str, Any],
    diagnostics_summary: Dict[str, Any],
    previous_run_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Computes a numeric reward:
    + Quality improvement
    + Fewer failures
    + Faster chunks (if benchmark data available)
    - Regressions
    """
    reward = 0.0
    factors: Dict[str, Any] = {}

    score = evaluator_summary.get("score")
    if isinstance(score, (int, float)):
        reward += score / 100.0
        factors["score"] = score

    failure_rate = (
        evaluator_summary.get("metrics", {})
        .get("chunk_failure_rate", {})
        .get("rate")
    )
    if isinstance(failure_rate, (int, float)):
        reward -= failure_rate
        factors["failure_rate"] = failure_rate

    prev_score = None
    if previous_run_summary:
        prev_score = previous_run_summary.get("score")
        if isinstance(prev_score, (int, float)) and isinstance(score, (int, float)):
            delta = score - prev_score
            reward += delta / 50.0  # modest weight
            factors["score_delta"] = delta

    return {
        "reward": float(reward),
        "factors": factors,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def save_reward(reward: Dict[str, Any]) -> Path:
    """Persist reward to disk."""
    # Include microseconds to avoid filename collisions when multiple rewards
    # are saved within the same second.
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    path = REWARDS_DIR / f"{ts}.json"
    path.write_text(json.dumps(reward, indent=2), encoding="utf-8")
    return path


def load_recent_rewards(limit: int = 5) -> List[Dict[str, Any]]:
    """Load recent reward files."""
    if not REWARDS_DIR.exists():
        return []
    paths = sorted(
        REWARDS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )[:limit]
    rewards: List[Dict[str, Any]] = []
    for p in paths:
        try:
            rewards.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return rewards


def load_reward_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Alias for load_recent_rewards (additive for profile fusion)."""
    return load_recent_rewards(limit=limit)
