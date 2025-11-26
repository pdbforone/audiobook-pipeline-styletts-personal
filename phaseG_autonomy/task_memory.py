"""
Task memory scaffold for Phase G autonomy.

Stores and retrieves short-lived context to inform future planning.
Methods are stubbed to avoid altering current pipeline behavior.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class TaskMemory:
    """Lightweight memory interface for autonomy tasks."""

    def record_event(self, event: Dict[str, Any]) -> None:
        """Record an event into the task memory."""
        raise NotImplementedError("Task memory recording is not implemented.")

    def recall_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent events up to the provided limit."""
        raise NotImplementedError("Task memory recall is not implemented.")

    def get_state(self) -> Optional[Dict[str, Any]]:
        """Retrieve serialized state for persistence."""
        raise NotImplementedError("Task memory serialization is not implemented.")
