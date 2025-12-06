#!/usr/bin/env python3
"""
Pydantic models for pipeline.json schema validation.

These models are the Python representation of schema.json v4.0.0.
They provide:
- Type safety for pipeline state
- Runtime validation
- IDE autocompletion and documentation
- Serialization/deserialization

Philosophy:
- Models mirror schema.json structure exactly
- Required fields match schema requirements
- additionalProperties preserved via Config.extra = "allow"
- Graceful degradation when pydantic unavailable
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Gracefully handle missing pydantic
try:
    from pydantic import BaseModel, Field, field_validator, ConfigDict

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    # Stub classes for when pydantic is not available
    class BaseModel:
        """Stub BaseModel when pydantic unavailable."""
        model_config = {}

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self, **kwargs):
            return self.__dict__.copy()

    class ConfigDict:
        """Stub ConfigDict."""
        def __init__(self, **kwargs):
            pass

    def Field(*args, **kwargs):
        return kwargs.get("default", None)

    def field_validator(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


# =============================================================================
# Enums
# =============================================================================

class StatusEnum(str, Enum):
    """Valid status values for phases, files, and chunks."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class FileTypeEnum(str, Enum):
    """Supported input file types."""
    PDF = "pdf"
    EPUB = "epub"
    DOCX = "docx"
    TXT = "txt"
    MOBI = "mobi"
    UNKNOWN = "unknown"


class ClassificationEnum(str, Enum):
    """Document content classification."""
    TEXT = "text"
    SCANNED = "scanned"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class RepairStatusEnum(str, Enum):
    """Phase 1 repair status."""
    VALIDATED = "validated"
    REPAIRED = "repaired"
    SKIPPED = "skipped"
    FAILED = "failed"


class EngineEnum(str, Enum):
    """Supported TTS engines."""
    XTTS = "xtts"
    KOKORO = "kokoro"
    PIPER = "piper"
    AUTO = "auto"


class ProfileEnum(str, Enum):
    """Genre profiles for chunking and voice selection."""
    AUTO = "auto"
    PHILOSOPHY = "philosophy"
    FICTION = "fiction"
    TECHNICAL = "technical"
    POETRY = "poetry"
    DRAMA = "drama"


class PresetEnum(str, Enum):
    """Audio mastering presets."""
    AUDIOBOOK_INTIMATE = "audiobook_intimate"
    AUDIOBOOK_DYNAMIC = "audiobook_dynamic"
    PODCAST_STANDARD = "podcast_standard"
    AUDIOBOOK_CLASSIC = "audiobook_classic"
    MINIMAL = "minimal"


class ExtractionToolEnum(str, Enum):
    """Text extraction tools."""
    PDFPLUMBER = "pdfplumber"
    PYPDF = "pypdf"
    FITZ = "fitz"
    PYTESSERACT = "pytesseract"
    EASYOCR = "easyocr"
    EBOOKLIB = "ebooklib"
    PYTHON_DOCX = "python-docx"
    UNKNOWN = "unknown"


# =============================================================================
# Common Models
# =============================================================================

class TimestampModel(BaseModel):
    """Timing information for operations."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    start: Optional[Union[float, str]] = Field(
        default=None,
        description="Unix timestamp or ISO8601 when operation started"
    )
    end: Optional[Union[float, str]] = Field(
        default=None,
        description="Unix timestamp or ISO8601 when operation ended"
    )
    duration: Optional[float] = Field(
        default=None,
        description="Duration in seconds"
    )


class ErrorEntry(BaseModel):
    """Structured error with context."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    type: Optional[str] = Field(
        default=None,
        description="Error category (e.g., ValidationError, TimeoutError)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable error description"
    )
    timestamp: Optional[Union[float, str]] = Field(
        default=None,
        description="When the error occurred"
    )
    file_id: Optional[str] = Field(
        default=None,
        description="Associated file if applicable"
    )
    chunk_id: Optional[str] = Field(
        default=None,
        description="Associated chunk if applicable"
    )


# =============================================================================
# Phase 1: Validation & Repair
# =============================================================================

class Phase1FileModel(BaseModel):
    """Phase 1 output for a single file."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    chunks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    # Phase 1 specific fields
    title: Optional[str] = Field(default=None, description="Extracted document title")
    author: Optional[str] = Field(default=None, description="Extracted author name")
    creation_date: Optional[str] = Field(default=None, description="Document creation date")
    file_type: Optional[str] = Field(default=None, description="Detected file format")
    classification: Optional[str] = Field(default=None, description="Content classification")
    hash: Optional[str] = Field(default=None, description="SHA256 hash of file")
    repair_status: Optional[str] = Field(default=None, description="Repair status")
    duplicate: Optional[bool] = Field(default=False, description="Is duplicate file")
    artifacts_path: Optional[str] = Field(default=None, description="Path to artifacts")


class Phase1Metrics(BaseModel):
    """Phase 1 aggregate metrics."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    total_files: Optional[int] = Field(default=0)
    duplicates: Optional[int] = Field(default=0)
    repaired: Optional[int] = Field(default=0)


class Phase1Schema(BaseModel):
    """Phase 1: Validation & Repair."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Phase1Metrics] = Field(default_factory=Phase1Metrics)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    files: Optional[Dict[str, Phase1FileModel]] = Field(default_factory=dict)
    hashes: Optional[List[str]] = Field(
        default_factory=list,
        description="SHA256 hashes for duplicate detection"
    )


# =============================================================================
# Phase 2: Text Extraction
# =============================================================================

class Phase2FileModel(BaseModel):
    """Phase 2 output for a single file."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    chunks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    # Phase 2 specific fields
    extracted_text_path: Optional[str] = Field(default=None, description="Path to extracted text")
    tool_used: Optional[str] = Field(default=None, description="Extraction tool used")
    yield_pct: Optional[float] = Field(default=None, ge=0, le=100, description="Content yield %")
    quality_score: Optional[float] = Field(default=None, ge=0, le=1, description="Quality 0-1")
    language: Optional[str] = Field(default=None, description="Detected language code")
    lang_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    structure: Optional[List[Dict[str, Any]]] = Field(default=None, description="Document structure")
    cleanup_notes: Optional[str] = Field(default=None)


class Phase2Metrics(BaseModel):
    """Phase 2 aggregate metrics."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    total_files: Optional[int] = Field(default=0)
    successful: Optional[int] = Field(default=0)
    failed: Optional[int] = Field(default=0)


class Phase2Schema(BaseModel):
    """Phase 2: Text Extraction."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Phase2Metrics] = Field(default_factory=Phase2Metrics)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    files: Optional[Dict[str, Phase2FileModel]] = Field(default_factory=dict)


# =============================================================================
# Phase 3: Semantic Chunking
# =============================================================================

class ChunkMetrics(BaseModel):
    """Aggregate chunk statistics."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    avg_chars: Optional[float] = Field(default=None)
    min_chars: Optional[int] = Field(default=None)
    max_chars: Optional[int] = Field(default=None)
    total_chunks: Optional[int] = Field(default=None)


class Phase3FileModel(BaseModel):
    """Phase 3 output for a single file."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    chunks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    # Phase 3 specific fields
    text_path: Optional[str] = Field(default=None, description="Source text path from Phase 2")
    chunk_paths: Optional[List[str]] = Field(default_factory=list, description="Chunk file paths")
    coherence_scores: Optional[List[float]] = Field(default=None, description="Inter-chunk coherence")
    readability_scores: Optional[List[float]] = Field(default=None, description="Flesch-Kincaid scores")
    embeddings: Optional[List[List[float]]] = Field(default=None, description="Chunk embeddings")
    chunk_metrics: Optional[ChunkMetrics] = Field(default=None)
    applied_profile: Optional[str] = Field(default=None, description="Genre profile used")
    genre_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    suggested_voice: Optional[str] = Field(default=None, description="Recommended voice ID")
    chunk_voice_overrides: Optional[Dict[str, str]] = Field(default=None)
    coherence_threshold: Optional[float] = Field(default=None)
    flesch_threshold: Optional[float] = Field(default=None)


class Phase3Metrics(BaseModel):
    """Phase 3 aggregate metrics."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    total_files: Optional[int] = Field(default=0)
    successful: Optional[int] = Field(default=0)
    partial: Optional[int] = Field(default=0)
    failed: Optional[int] = Field(default=0)
    total_chunks: Optional[int] = Field(default=0)


class Phase3Schema(BaseModel):
    """Phase 3: Semantic Chunking."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Phase3Metrics] = Field(default_factory=Phase3Metrics)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    files: Optional[Dict[str, Phase3FileModel]] = Field(default_factory=dict)


# =============================================================================
# Phase 4: TTS Synthesis
# =============================================================================

class ValidationResult(BaseModel):
    """Audio validation results."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    tier1_passed: Optional[bool] = Field(default=None, description="Basic validation passed")
    tier2_wer: Optional[float] = Field(default=None, description="Word Error Rate")
    tier2_passed: Optional[bool] = Field(default=None, description="ASR validation passed")


class Phase4ChunkModel(BaseModel):
    """Phase 4 TTS result for a single chunk."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    chunk_id: Union[str, int] = Field(description="Chunk identifier")
    status: Optional[str] = Field(default="pending")
    audio_path: Optional[str] = Field(default=None, description="Generated audio path")
    engine_used: Optional[str] = Field(default=None, description="TTS engine used")
    voice_used: Optional[str] = Field(default=None, description="Voice ID used")
    text_length: Optional[int] = Field(default=None, description="Input text char count")
    audio_seconds: Optional[float] = Field(default=None, description="Audio duration")
    rt_factor: Optional[float] = Field(default=None, description="Real-time factor")
    latency_fallback_used: Optional[bool] = Field(default=False)
    validation: Optional[ValidationResult] = Field(default=None)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)


class Phase4FileModel(BaseModel):
    """Phase 4 output for a single file."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    chunks: Optional[List[Phase4ChunkModel]] = Field(default_factory=list)

    # Phase 4 specific fields
    voice_id: Optional[str] = Field(default=None, description="Voice ID used")
    requested_engine: Optional[str] = Field(default=None)
    selected_engine: Optional[str] = Field(default=None)
    engines_used: Optional[List[str]] = Field(default_factory=list)
    total_chunks: Optional[int] = Field(default=None)
    chunks_completed: Optional[int] = Field(default=None)
    chunks_failed: Optional[int] = Field(default=None)
    audio_dir: Optional[str] = Field(default=None)
    chunk_audio_paths: Optional[List[str]] = Field(default_factory=list)
    duration_seconds: Optional[float] = Field(default=None)
    avg_rt_factor: Optional[float] = Field(default=None)
    rt_p50: Optional[float] = Field(default=None)
    rt_p90: Optional[float] = Field(default=None)
    rt_p99: Optional[float] = Field(default=None)
    latency_fallback_chunks: Optional[int] = Field(default=None)
    fallback_rate: Optional[float] = Field(default=None)
    advisory: Optional[str] = Field(default=None)


class Phase4Metrics(BaseModel):
    """Phase 4 aggregate metrics."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    total_files: Optional[int] = Field(default=0)
    successful: Optional[int] = Field(default=0)
    partial: Optional[int] = Field(default=0)
    failed: Optional[int] = Field(default=0)
    total_chunks: Optional[int] = Field(default=0)
    total_audio_seconds: Optional[float] = Field(default=0)


class Phase4Schema(BaseModel):
    """Phase 4: TTS Synthesis."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Phase4Metrics] = Field(default_factory=Phase4Metrics)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    files: Optional[Dict[str, Phase4FileModel]] = Field(default_factory=dict)


# =============================================================================
# Phase 5: Audio Enhancement
# =============================================================================

class Phase5ChunkModel(BaseModel):
    """Phase 5 enhancement result for a single chunk."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    chunk_id: Union[str, int] = Field(description="Chunk identifier")
    status: Optional[str] = Field(default="pending")
    wav_path: Optional[str] = Field(default=None, description="Input audio path")
    enhanced_path: Optional[str] = Field(default=None, description="Output enhanced path")
    snr_pre: Optional[float] = Field(default=None, description="SNR before (dB)")
    snr_post: Optional[float] = Field(default=None, description="SNR after (dB)")
    rms_pre: Optional[float] = Field(default=None, description="RMS before (dBFS)")
    rms_post: Optional[float] = Field(default=None, description="RMS after (dBFS)")
    lufs_pre: Optional[float] = Field(default=None, description="LUFS before")
    lufs_post: Optional[float] = Field(default=None, description="LUFS after")
    duration: Optional[float] = Field(default=None, description="Audio duration")
    cleanup_status: Optional[str] = Field(default=None)
    phrases_removed: Optional[int] = Field(default=None)
    cleanup_processing_time: Optional[float] = Field(default=None)
    speech_ratio: Optional[float] = Field(default=None, description="Speech/total ratio")
    error_message: Optional[str] = Field(default=None)


class Phase5FileModel(BaseModel):
    """Phase 5 output for a single file."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    chunks: Optional[List[Phase5ChunkModel]] = Field(default_factory=list)
    output_path: Optional[str] = Field(default=None, description="Final mastered audio")
    preset_used: Optional[str] = Field(default=None, description="Mastering preset")


class Phase5Metrics(BaseModel):
    """Phase 5 aggregate metrics."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    successful: Optional[int] = Field(default=0)
    failed: Optional[int] = Field(default=0)
    total_duration: Optional[float] = Field(default=0)
    avg_snr_improvement: Optional[float] = Field(default=None)
    avg_volume_normalization_delta: Optional[float] = Field(default=None)
    volume_normalization_applied_count: Optional[int] = Field(default=None)
    phrases_removed_total: Optional[int] = Field(default=None)
    chunks_with_phrases: Optional[int] = Field(default=None)
    cleanup_errors: Optional[int] = Field(default=None)


class Phase5Schema(BaseModel):
    """Phase 5: Audio Enhancement."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Phase5Metrics] = Field(default_factory=Phase5Metrics)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    files: Optional[Dict[str, Phase5FileModel]] = Field(default_factory=dict)
    chunks: Optional[List[Phase5ChunkModel]] = Field(
        default_factory=list,
        description="Legacy flat chunk structure"
    )


# =============================================================================
# Phase 5.5: Subtitle Generation
# =============================================================================

class Phase5_5FileModel(BaseModel):
    """Phase 5.5 output for a single file."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    chunks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    srt_file: Optional[str] = Field(default=None)
    vtt_file: Optional[str] = Field(default=None)
    karaoke_file: Optional[str] = Field(default=None)
    coverage: Optional[float] = Field(default=None)
    wer: Optional[float] = Field(default=None)


class Phase5_5Metrics(BaseModel):
    """Phase 5.5 metrics."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    coverage: Optional[float] = Field(default=None, description="Audio coverage 0-1")
    wer: Optional[float] = Field(default=None, description="Word Error Rate")
    segments: Optional[int] = Field(default=None)
    average_segment_duration: Optional[float] = Field(default=None)
    max_drift_seconds: Optional[float] = Field(default=None)
    model: Optional[str] = Field(default=None, description="Whisper model used")
    processing_host: Optional[str] = Field(default=None)


class Phase5_5Schema(BaseModel):
    """Phase 5.5: Subtitle Generation."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Phase5_5Metrics] = Field(default_factory=Phase5_5Metrics)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    files: Optional[Dict[str, Phase5_5FileModel]] = Field(default_factory=dict)
    timestamp: Optional[float] = Field(default=None)
    duration: Optional[float] = Field(default=None)
    srt_file: Optional[str] = Field(default=None)
    vtt_file: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)


# =============================================================================
# Phase 6 & 7: Orchestration & Batch
# =============================================================================

class Phase6Schema(BaseModel):
    """Phase 6: Orchestration telemetry."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    files: Optional[Dict[str, Any]] = Field(default_factory=dict)
    run_config: Optional[Dict[str, Any]] = Field(default=None)
    phases_executed: Optional[List[str]] = Field(default_factory=list)
    total_duration_seconds: Optional[float] = Field(default=None)
    policy_decisions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class Phase7Schema(BaseModel):
    """Phase 7: Batch processing telemetry."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    files: Optional[Dict[str, Any]] = Field(default_factory=dict)
    manifest_path: Optional[str] = Field(default=None)
    worker_count: Optional[int] = Field(default=None)
    files_queued: Optional[int] = Field(default=None)
    files_completed: Optional[int] = Field(default=None)
    files_failed: Optional[int] = Field(default=None)


# =============================================================================
# Batch Run
# =============================================================================

class BatchFileEntry(BaseModel):
    """Status of a single file within a batch run."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    source_path: Optional[str] = Field(default=None)
    duration_sec: Optional[float] = Field(default=None)
    cpu_avg: Optional[float] = Field(default=None)


class BatchRun(BaseModel):
    """Record of a batch processing run."""
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    run_id: str = Field(description="Unique batch run identifier")
    status: Optional[str] = Field(default="pending")
    timestamps: Optional[TimestampModel] = Field(default_factory=TimestampModel)
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    errors: Optional[List[Union[str, ErrorEntry]]] = Field(default_factory=list)
    artifacts: Optional[Union[Dict[str, Any], List[str]]] = Field(default_factory=dict)
    files: Optional[Dict[str, BatchFileEntry]] = Field(default_factory=dict)


# =============================================================================
# Root Pipeline Schema
# =============================================================================

class PipelineSchema(BaseModel):
    """
    Root pipeline.json schema - the single source of truth.

    This model represents the complete state of an audiobook pipeline,
    including all phases, their outputs, and batch run history.
    """
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}

    # Top-level metadata
    pipeline_version: Optional[str] = Field(
        default="4.0.0",
        description="Schema version for migration"
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO8601 creation timestamp"
    )
    last_updated: Optional[str] = Field(
        default=None,
        description="ISO8601 last update timestamp"
    )
    file_id: Optional[str] = Field(
        default=None,
        description="Primary file identifier"
    )
    input_file: Optional[str] = Field(
        default=None,
        description="Source file path"
    )
    tts_profile: Optional[str] = Field(
        default=None,
        description="Genre profile for TTS"
    )
    tts_voice: Optional[str] = Field(
        default=None,
        description="Global voice override"
    )
    voice_overrides: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Per-file voice overrides"
    )
    phases: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Quick-lookup status map"
    )

    # Phase blocks
    phase1: Optional[Phase1Schema] = Field(default=None)
    phase2: Optional[Phase2Schema] = Field(default=None)
    phase3: Optional[Phase3Schema] = Field(default=None)
    phase4: Optional[Phase4Schema] = Field(default=None)
    phase5: Optional[Phase5Schema] = Field(default=None)
    phase5_5: Optional[Phase5_5Schema] = Field(default=None)
    phase6: Optional[Phase6Schema] = Field(default=None)
    phase7: Optional[Phase7Schema] = Field(default=None)

    # Batch history
    batch_runs: Optional[List[BatchRun]] = Field(
        default_factory=list,
        description="History of batch runs"
    )

    if PYDANTIC_AVAILABLE:
        @field_validator(
            "phase1", "phase2", "phase3", "phase4", "phase5", mode="before"
        )
        @classmethod
        def validate_phase_structure(cls, v):
            """Ensure phase blocks are dictionaries."""
            if v is not None and not isinstance(v, (dict, BaseModel)):
                raise ValueError("Phase block must be a dictionary")
            return v


# =============================================================================
# Minimal Schema for lenient validation
# =============================================================================

class MinimalPipelineSchema(BaseModel):
    """
    Minimal validation - only ensures valid JSON structure.
    Use for lenient validation during development or migration.
    """
    model_config = ConfigDict(extra="allow") if PYDANTIC_AVAILABLE else {}


# =============================================================================
# Validation Levels
# =============================================================================

VALIDATION_STRICT = PipelineSchema
VALIDATION_LENIENT = MinimalPipelineSchema


# =============================================================================
# Helper Functions
# =============================================================================

def validate_pipeline_data(data: Dict[str, Any], strict: bool = True) -> PipelineSchema:
    """
    Validate pipeline data against the schema.

    Args:
        data: Pipeline state dictionary
        strict: If True, use full validation; if False, minimal validation

    Returns:
        Validated PipelineSchema instance

    Raises:
        ValueError: If validation fails
    """
    if not PYDANTIC_AVAILABLE:
        return PipelineSchema(**data)

    schema_class = VALIDATION_STRICT if strict else VALIDATION_LENIENT
    return schema_class(**data)


def create_empty_pipeline(file_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new empty pipeline state with proper structure.

    Args:
        file_id: Optional primary file identifier

    Returns:
        Dictionary with proper pipeline structure
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return {
        "pipeline_version": "4.0.0",
        "created_at": now,
        "last_updated": now,
        "file_id": file_id,
        "input_file": None,
        "tts_profile": None,
        "tts_voice": None,
        "voice_overrides": {},
        "phases": {},
        "batch_runs": [],
    }
