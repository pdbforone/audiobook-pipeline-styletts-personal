"""Shared utilities for the audiobook pipeline."""

from .adapter import adapt_payload, upgrade_pipeline_file
from .astromech_notify import play_alert_beep, play_success_beep
from .state_manager import (
    PipelineState,
    StateError,
    StateLockError,
    StateReadError,
    StateTransactionError,
    StateValidationError,
    StateWriteError,
)
from .schema import (
    CANONICAL_JSON_SCHEMA,
    CANONICAL_SCHEMA_VERSION,
    PHASE_KEYS,
    VALID_PHASE_STATUSES,
    canonicalize_state,
    validate_pipeline_schema,
)
from .phase_utils import (
    ensure_phase_block,
    ensure_phase_file_entry,
    ensure_phase_files,
    ensure_phase_and_file,
)

__version__ = "1.0.1"

__all__ = [
    "adapt_payload",
    "PipelineState",
    "upgrade_pipeline_file",
    "StateError",
    "StateLockError",
    "StateReadError",
    "StateTransactionError",
    "StateValidationError",
    "StateWriteError",
    "play_success_beep",
    "play_alert_beep",
    "canonicalize_state",
    "validate_pipeline_schema",
    "CANONICAL_JSON_SCHEMA",
    "CANONICAL_SCHEMA_VERSION",
    "PHASE_KEYS",
    "VALID_PHASE_STATUSES",
    "ensure_phase_block",
    "ensure_phase_file_entry",
    "ensure_phase_files",
    "ensure_phase_and_file",
]
