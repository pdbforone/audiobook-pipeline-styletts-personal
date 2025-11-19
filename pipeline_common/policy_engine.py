from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    from pipeline_common.state_manager import PipelineState


class PolicyEngine:
    """Extensible hook surface for orchestrator lifecycle events."""

    def before_phase(self, phase: str, file_id: str, state: "PipelineState") -> None:
        """Invoked immediately before a phase (phase1..phase7/5.5) begins."""
        return None

    def after_phase(self, phase: str, file_id: str, state: "PipelineState") -> None:
        """Invoked once a phase completes successfully."""
        return None

    def before_retry(
        self,
        phase: str,
        file_id: str,
        attempt: int,
        state: "PipelineState",
    ) -> None:
        """Invoked before a retry attempt executes for the given phase."""
        return None

    def after_failure(
        self,
        phase: str,
        file_id: str,
        error: Exception,
        state: "PipelineState",
    ) -> None:
        """Invoked when a phase ultimately fails and no further retries remain."""
        return None
