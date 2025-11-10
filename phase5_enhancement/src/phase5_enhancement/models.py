from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Literal
from pathlib import Path
from dataclasses import dataclass, field as dataclass_field
import os
import json


class EnhancementConfig(BaseModel):
    """Configuration for audio enhancement pipeline"""

    # Input/Output Paths
    input_dir: str = Field(
        default="../phase4_tts/audio_chunks",
        description="Input directory for WAV chunks from Phase 4",
    )
    output_dir: str = Field(
        default="processed", description="Output directory for enhanced audio"
    )
    pipeline_json: str = Field(
        default="../../pipeline.json", description="Path to pipeline.json"
    )

    # Audio Processing Parameters
    sample_rate: int = Field(default=48000, description="Audio sample rate")
    lufs_target: float = Field(
        default=-23.0, ge=-40.0, le=-10.0, description="Target LUFS for normalization"
    )
    snr_threshold: float = Field(
        default=0.0,
        description="Minimum SNR for quality validation in dB",
    )
    noise_reduction_factor: float = Field(
        default=0.02,
        description="Noise reduction strength for noisereduce",
    )
    enable_volume_normalization: bool = Field(
        default=True,
        description="Enable pydub volume normalization before processing",
    )
    volume_norm_headroom: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Headroom for volume normalization (prevents clipping)",
    )

    # Output Parameters
    crossfade_duration: float = Field(
        default=0.5, ge=0.0, le=5.0, description="Crossfade duration in seconds"
    )
    mp3_bitrate: str = Field(
        default="192k",
        pattern=r"^\d{2,3}k$",
        description="MP3 export bitrate (e.g., '192k')",
    )

    # Metadata
    audiobook_title: str = Field(
        default="The Analects of Confucius", description="Title for metadata"
    )
    audiobook_author: str = Field(
        default="Confucius", description="Author for metadata"
    )

    # Processing Parameters
    retries: int = Field(
        default=2, ge=0, le=5, description="Max retries on quality failure"
    )
    max_workers: int = Field(
        default=2, ge=1, le=16, description="Max parallel workers for batch processing"
    )
    chunk_size_seconds: int = Field(
        default=30, ge=10, le=300, description="Chunk size for large audio processing"
    )

    # Quality Control
    quality_validation_enabled: bool = Field(
        default=True, description="Enable quality validation checks"
    )
    processing_timeout: int = Field(
        default=60, ge=10, le=300, description="Processing timeout per chunk in seconds"
    )

    # System Resources
    memory_limit_mb: int = Field(
        default=1024,
        ge=256,
        le=8192,
        description="Memory limit per process in MB",
    )
    temp_dir: str = Field(
        default="temp", description="Temporary directory for processing"
    )
    cleanup_temp_files: bool = Field(
        default=True, description="Cleanup temp files after processing"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    log_file: str = Field(default="audio_enhancement.log", description="Log file path")

    # Recovery Options
    resume_on_failure: bool = Field(
        default=True, description="Resume from failures using JSON checkpoints"
    )
    backup_original: bool = Field(
        default=False, description="Backup original chunks before enhancement"
    )

    # Phrase Cleanup (NEW)
    enable_phrase_cleanup: bool = Field(
        default=True, description="Enable automatic phrase removal before enhancement"
    )
    cleanup_target_phrases: List[str] = Field(
        default=[
            "You need to add some text for me to talk",
            "You need to add some text for me to talk.",
            "You need to add text for me to talk",
            "You need to add text for me to talk."
        ],
        description="Phrases to detect and remove from audio chunks"
    )
    cleanup_whisper_model: str = Field(
        default="base",
        pattern=r"^(tiny|base|small|medium|large)$",
        description="Whisper model size for transcription (tiny, base, small, medium, large)"
    )
    cleanup_save_transcripts: bool = Field(
        default=False, description="Save SRT transcripts during cleanup for debugging"
    )

    # Advanced Audio Mastering (NEW)
    enable_deepfilternet: bool = Field(
        default=False,
        description="Use DeepFilterNet for professional noise reduction (replaces noisereduce when enabled)"
    )
    enable_matchering: bool = Field(
        default=False,
        description="Apply reference-based mastering using Matchering (GPL-3.0, internal use only)"
    )
    matchering_reference: Optional[str] = Field(
        default=None,
        description="Path to reference audio file for Matchering mastering (WAV format, stereo recommended)"
    )
    matchering_max_length: int = Field(
        default=1800,  # 30 minutes in seconds
        ge=60,
        le=7200,
        description="Maximum audio length for Matchering processing in seconds"
    )

    @field_validator("input_dir", "output_dir", "temp_dir")
    @classmethod
    def validate_directories(cls, v: str) -> str:
        """Create directories if they don't exist"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @model_validator(mode="after")
    def validate_paths_exist(self):
        """Additional validation for critical paths"""
        path = Path(self.pipeline_json)
        if not path.exists():
            # Create empty pipeline.json if missing
            with open(path, "w") as f:
                json.dump({"phase5": {}}, f)
        return self

    class Config:
        validate_assignment = True
        extra = "forbid"


class AudioMetadata(BaseModel):
    """Metadata for audio chunks"""

    chunk_id: int
    wav_path: str
    enhanced_path: Optional[str] = None
    snr_pre: Optional[float] = None
    snr_post: Optional[float] = None
    rms_pre: Optional[float] = None
    rms_post: Optional[float] = None
    rms_volume_norm_pre: Optional[float] = None
    rms_volume_norm_post: Optional[float] = None
    lufs_pre: Optional[float] = None
    lufs_post: Optional[float] = None
    status: str = "pending"
    error_message: Optional[str] = None
    duration: Optional[float] = None
    # Phrase cleanup metadata
    cleanup_status: Optional[str] = None  # 'cleaned', 'clean', 'disabled', 'error'
    phrases_removed: Optional[int] = None
    cleanup_processing_time: Optional[float] = None


class ProcessingResult(BaseModel):
    """Overall processing result"""

    successful_chunks: int
    failed_chunks: int
    total_duration: float
    artifacts: List[str]
    metrics: dict  # e.g., {"avg_snr_improvement": float}
    errors: List[str]


@dataclass
class SubtitleConfig:
    """Configuration for subtitle generation."""

    # Input/Output
    audio_path: Path
    output_dir: Path = dataclass_field(default_factory=lambda: Path("subtitles"))
    file_id: str = "audiobook"

    # Model Selection
    model_size: Literal["tiny", "small", "base"] = "small"
    device: Literal["cpu", "cuda"] = "cpu"
    compute_type: Literal["int8", "float16", "float32"] = "int8"

    # Quality Settings
    language: str = "en"
    beam_size: int = 5
    temperature: float = 0.0  # Deterministic

    # Segment Settings
    max_chars: int = 84  # YouTube recommendation
    min_duration: float = 1.5  # seconds
    max_duration: float = 7.0  # seconds

    # Quality Thresholds
    min_coverage: float = 0.95  # 95% of audio duration
    max_wer: float = 0.15  # 15% Word Error Rate
    max_drift: float = 2.0  # 2 second timestamp drift

    # Processing Options
    enable_checkpoints: bool = True
    checkpoint_interval: int = 300  # Save every 5 minutes of audio
    reference_text_path: Optional[Path] = None  # For WER calculation

    # Alignment
    enable_drift_correction: bool = True
    drift_correction_threshold: float = 1.0  # Correct if drift >1 sec

    def __post_init__(self):
        """Ensure paths are Path objects."""
        self.audio_path = Path(self.audio_path)
        self.output_dir = Path(self.output_dir)
        if self.reference_text_path:
            self.reference_text_path = Path(self.reference_text_path)
