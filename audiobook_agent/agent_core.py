"""
Core agent scaffold for future audiobook autonomy.

All methods are placeholders and intentionally raise NotImplementedError
until real logic is supplied.
"""

from __future__ import annotations

from typing import Any, Dict


class AudiobookAgent:
    """Stub agent coordinating autonomy and reasoning phases."""

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent loop for a single payload."""
        raise NotImplementedError("AudiobookAgent run is not implemented.")

    def load(self, state: Dict[str, Any]) -> None:
        """Load agent state from a serialized representation."""
        raise NotImplementedError("AudiobookAgent load is not implemented.")

    def save(self) -> Dict[str, Any]:
        """Return a serialized snapshot of agent state."""
        raise NotImplementedError("AudiobookAgent save is not implemented.")
