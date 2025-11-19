"""Shared utilities for the audiobook pipeline."""

from .astromech_notify import play_alert_beep, play_success_beep
from .state_manager import PipelineState, StateError, StateLockError, StateValidationError

__version__ = "1.0.1"

__all__ = [
    "PipelineState",
    "StateError",
    "StateLockError",
    "StateValidationError",
    "play_success_beep",
    "play_alert_beep",
]
