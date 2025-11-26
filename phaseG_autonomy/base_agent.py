"""
Base interface for Phase G autonomy agents.

This stub is a placeholder; methods must be implemented before the
autonomy phase can perform real work. Current pipeline behavior is
unchanged because nothing calls into these methods by default.
"""

from __future__ import annotations

from typing import Any, Dict


class BaseAutonomyAgent:
    """Define the minimal surface for autonomy control loops."""

    def load_state(self, state: Dict[str, Any]) -> None:
        """Load persisted autonomy state."""
        raise NotImplementedError("Autonomy agent state loading is not implemented.")

    def plan(self, objectives: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a high-level plan given objectives."""
        raise NotImplementedError("Autonomy planning is not implemented.")

    def execute_step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step of the autonomy loop."""
        raise NotImplementedError("Autonomy step execution is not implemented.")

    def persist_state(self) -> Dict[str, Any]:
        """Return state to persist between runs."""
        raise NotImplementedError("Autonomy agent persistence is not implemented.")
