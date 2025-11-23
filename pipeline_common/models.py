#!/usr/bin/env python3
"""
Pydantic models for pipeline.json schema validation.

Philosophy:
- Validate structure, not content
- Allow phases to evolve without breaking validation
- Required fields are truly required, everything else is optional
- Type hints guide correctness without being overly rigid
"""

from typing import Any, Dict, List, Optional

# Gracefully handle missing pydantic
try:
    from pydantic import BaseModel, Field, field_validator

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    # Stub classes for when pydantic is not available
    class BaseModel:
        def __init__(self, **kwargs):
            pass

    def Field(*args, **kwargs):
        return None

    def field_validator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


class TimestampModel(BaseModel):
    """Common timestamp structure"""

    start: Optional[float] = None
    end: Optional[float] = None
    duration: Optional[float] = None

    class Config:
        extra = "allow"  # Allow additional fields


class PhaseStatus(BaseModel):
    """
    Base model for phase status blocks.

    Each phase can extend this with phase-specific fields.
    """

    status: Optional[str] = Field(
        None,
        pattern="^(pending|running|success|partial|partial_success|failed|error|skipped|unknown)$",
    )
    errors: Optional[List[Any]] = Field(default_factory=list)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamps: Optional[TimestampModel] = None

    class Config:
        extra = "allow"  # Phases can add custom fields


class Phase1Schema(PhaseStatus):
    """Phase 1: Validation & Repair"""

    files: Optional[Dict[str, Any]] = Field(default_factory=dict)
    hashes: Optional[List[str]] = Field(default_factory=list)


class Phase2Schema(PhaseStatus):
    """Phase 2: Text Extraction"""

    files: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Phase3Schema(PhaseStatus):
    """Phase 3: Semantic Chunking"""

    files: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Phase4Schema(PhaseStatus):
    """Phase 4: TTS Synthesis"""

    files: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Phase5Schema(PhaseStatus):
    """Phase 5: Audio Enhancement"""

    artifacts: Optional[List[str]] = Field(default_factory=list)
    chunks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class Phase5_5Schema(PhaseStatus):
    """Phase 5.5: Subtitle Generation"""

    timestamp: Optional[float] = None
    duration: Optional[float] = None
    srt_file: Optional[str] = None
    vtt_file: Optional[str] = None
    error: Optional[str] = None


class PipelineSchema(BaseModel):
    """
    Root pipeline.json schema.

    Validates:
    - Top-level structure is correct
    - Phase blocks have valid status values
    - Critical metadata is present (when phases are populated)

    Does NOT validate:
    - Specific phase implementation details
    - File paths exist
    - Metrics are in valid ranges

    This keeps validation flexible while preventing structural corruption.
    """

    # Top-level metadata (optional for backwards compatibility)
    pipeline_version: Optional[str] = "1.0"
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    input_file: Optional[str] = None
    file_id: Optional[str] = None
    tts_profile: Optional[str] = None
    tts_voice: Optional[str] = None

    # Phase blocks (all optional - phases may not be run yet)
    phase1: Optional[Phase1Schema] = None
    phase2: Optional[Phase2Schema] = None
    phase3: Optional[Phase3Schema] = None
    phase4: Optional[Phase4Schema] = None
    phase5: Optional[Phase5Schema] = None
    phase5_5: Optional[Phase5_5Schema] = None
    phase6: Optional[Dict[str, Any]] = None  # Orchestration telemetry
    phase7: Optional[Dict[str, Any]] = None  # Batch telemetry

    # Allow additional fields (for custom phases or metadata)
    class Config:
        extra = "allow"

    @field_validator(
        "phase1", "phase2", "phase3", "phase4", "phase5", mode="before"
    )
    @classmethod
    def validate_phase_structure(cls, v):
        """Ensure phase blocks are dictionaries"""
        if v is not None and not isinstance(v, dict):
            raise ValueError("Phase block must be a dictionary")
        return v


class MinimalPipelineSchema(BaseModel):
    """
    Minimal validation - only ensures it's valid JSON structure.

    Use this for lenient validation during development or migration.
    """

    class Config:
        extra = "allow"


# Validation levels
VALIDATION_STRICT = PipelineSchema
VALIDATION_LENIENT = MinimalPipelineSchema
