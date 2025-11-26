"""
Storage interface stub for audiobook agents.

Abstracts persistence of autonomy and reasoning artifacts. Methods are
placeholders and raise NotImplementedError.
"""

from __future__ import annotations

from typing import Any, Dict, List


class StorageInterface:
    """Minimal interface for agent storage backends."""

    def save_run(self, run_id: str, payload: Dict[str, Any]) -> None:
        """Persist a run payload."""
        raise NotImplementedError("Storage save_run is not implemented.")

    def load_run(self, run_id: str) -> Dict[str, Any]:
        """Load a persisted run payload."""
        raise NotImplementedError("Storage load_run is not implemented.")

    def list_runs(self) -> List[str]:
        """List available run identifiers."""
        raise NotImplementedError("Storage list_runs is not implemented.")
