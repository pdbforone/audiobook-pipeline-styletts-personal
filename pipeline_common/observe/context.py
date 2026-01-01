"""
Run context for correlation across phases.

Provides thread-local context propagation for run_id, file_id, and phase.
This enables log correlation and metrics attribution without passing
context through every function call.
"""

import uuid
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Generator


@dataclass
class RunContext:
    """Context for a pipeline run, enabling correlation across phases."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    file_id: Optional[str] = None
    phase: Optional[str] = None
    chunk_id: Optional[str] = None
    engine: Optional[str] = None

    def as_dict(self) -> dict:
        """Return context as dict for logging extra fields."""
        return {
            k: v for k, v in {
                "run_id": self.run_id,
                "file_id": self.file_id,
                "phase": self.phase,
                "chunk_id": self.chunk_id,
                "engine": self.engine,
            }.items() if v is not None
        }

    def copy(self, **updates) -> "RunContext":
        """Create a copy with optional field updates."""
        return RunContext(
            run_id=updates.get("run_id", self.run_id),
            file_id=updates.get("file_id", self.file_id),
            phase=updates.get("phase", self.phase),
            chunk_id=updates.get("chunk_id", self.chunk_id),
            engine=updates.get("engine", self.engine),
        )


# Thread-local storage for context
_context_storage = threading.local()


def get_current_context() -> RunContext:
    """Get the current run context, creating a default if none exists."""
    if not hasattr(_context_storage, "context"):
        _context_storage.context = RunContext()
    return _context_storage.context


def set_context(ctx: RunContext) -> None:
    """Set the current run context."""
    _context_storage.context = ctx


def clear_context() -> None:
    """Clear the current run context."""
    if hasattr(_context_storage, "context"):
        delattr(_context_storage, "context")


@contextmanager
def with_context(
    run_id: Optional[str] = None,
    file_id: Optional[str] = None,
    phase: Optional[str] = None,
    chunk_id: Optional[str] = None,
    engine: Optional[str] = None,
) -> Generator[RunContext, None, None]:
    """
    Context manager for scoped context updates.

    Preserves the previous context and restores it on exit.
    Only provided fields are updated; None values keep existing values.

    Usage:
        with with_context(file_id="book1", phase="phase4"):
            logger.info("Processing")  # Includes file_id and phase
    """
    previous = get_current_context()

    # Create new context with updates
    updates = {}
    if run_id is not None:
        updates["run_id"] = run_id
    if file_id is not None:
        updates["file_id"] = file_id
    if phase is not None:
        updates["phase"] = phase
    if chunk_id is not None:
        updates["chunk_id"] = chunk_id
    if engine is not None:
        updates["engine"] = engine

    new_context = previous.copy(**updates)
    set_context(new_context)

    try:
        yield new_context
    finally:
        set_context(previous)
