"""
Reward model stub for Phase H reasoning.

Defines the interface for computing rewards over autonomy actions.
All methods currently raise NotImplementedError.
"""

from __future__ import annotations

from typing import Any, Dict


class RewardModel:
    """Stub reward model used to score autonomy actions."""

    def compute_reward(self, signal: Dict[str, Any]) -> float:
        """Compute a scalar reward for the provided signal."""
        raise NotImplementedError("Reward computation is not implemented.")

    def reset(self) -> None:
        """Reset any internal state for a new episode."""
        raise NotImplementedError("Reward model reset is not implemented.")
