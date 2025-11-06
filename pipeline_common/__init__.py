"""
Pipeline Common - Shared utilities for the audiobook pipeline

Provides:
- Atomic state management for pipeline.json
- Transaction-based updates with rollback
- Automatic backups and rotation
- Schema validation
- Audit logging
"""

from .state_manager import (
    PipelineState,
    StateTransaction,
    StateError,
    StateLockError,
    StateValidationError,
)

from .models import (
    PipelineSchema,
    MinimalPipelineSchema,
    VALIDATION_STRICT,
    VALIDATION_LENIENT,
)

__version__ = "1.0.0"

__all__ = [
    "PipelineState",
    "StateTransaction",
    "StateError",
    "StateLockError",
    "StateValidationError",
    "PipelineSchema",
    "MinimalPipelineSchema",
    "VALIDATION_STRICT",
    "VALIDATION_LENIENT",
]
