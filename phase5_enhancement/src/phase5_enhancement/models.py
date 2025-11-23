from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    PrivateAttr,
)
from typing import Optional, List, Literal, Set
from pathlib import Path
from dataclasses import dataclass, field as dataclass_field
import os

from pipeline_common import PipelineState


class EnhancementConfig(BaseModel):
    """Configuration for audio enhancement pipeline"""

    # Mastering profile presets
    profile: Literal["auto", "laptop_safe", "full_master"] = Field(
        default="auto",
        description="Preset profile that tunes CPU usage, models, and mastering defaults",
    )

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
        default=-23.0,
        ge=-40.0,
        le=-10.0,
        description="Target LUFS for normalization",
    )
    snr_threshold: float = Field(
        default=0.0,
        description="Minimum SNR for quality validation in dB",
    )
    noise_reduction_factor: float = Field(
        default=0.02,
        description="Noise reduction strength for noisereduce",
    )
    enable_rnnoise: bool = Field(
        default=True,
        description="Use RNNoise (CPU) for speech-preserving denoise before normalization",
    )
    rnnoise_frame_seconds: float = Field(
        default=0.02,
        ge=0.01,
        le=0.04,
        description="Frame size (seconds) when applying RNNoise",
    )
    enable_silero_vad: bool = Field(
        default=False,
        description="Run Silero VAD to measure speech coverage and optionally trim silence",
    )
    silero_vad_threshold: float = Field(
        default=0.6,
        ge=0.1,
        le=0.95,
        description="Probability threshold for Silero VAD speech detection",
    )
    silero_vad_min_speech: float = Field(
        default=1.0,
        ge=0.1,
        description="Minimum detected speech seconds required before warning",
    )
    trim_silence_with_vad: bool = Field(
        default=False,
        description="If true, use VAD to drop detected non-speech regions before mastering",
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
    enable_compression: bool = Field(
        default=True,
        description="Apply gentle broadband compression and limiter after denoise, before LUFS normalize",
    )
    compressor_threshold_db: float = Field(
        default=-24.0,
        description="Compressor threshold (dBFS)",
    )
    compressor_ratio: float = Field(
        default=4.0,
        ge=1.0,
        description="Compressor ratio (e.g., 4:1)",
    )
    limiter_ceiling_db: float = Field(
        default=-1.0,
        description="Limiter ceiling to catch peaks before export",
    )

    # Output Parameters
    crossfade_duration: float = Field(
        default=0.05,
        ge=0.0,
        le=5.0,
        description="Crossfade duration in seconds",
    )
    crossfade_max_sec: float = Field(
        default=0.1,
        ge=0.0,
        le=5.0,
        description="Maximum allowed crossfade duration",
    )
    crossfade_silence_guard_sec: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Skip crossfade when leading silence on next chunk exceeds this duration",
    )
    crossfade_enable_silence_guard: bool = Field(
        default=True,
        description="Disable to always apply crossfade regardless of silence",
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
        default=2,
        ge=1,
        le=16,
        description="Max parallel workers for batch processing",
    )
    chunk_size_seconds: int = Field(
        default=30,
        ge=10,
        le=300,
        description="Chunk size for large audio processing",
    )

    # Quality Control
    quality_validation_enabled: bool = Field(
        default=True, description="Enable quality validation checks"
    )
    processing_timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Processing timeout per chunk in seconds",
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
    log_file: str = Field(
        default="audio_enhancement.log", description="Log file path"
    )

    # Recovery Options
    resume_on_failure: bool = Field(
        default=True, description="Resume from failures using JSON checkpoints"
    )
    backup_original: bool = Field(
        default=False, description="Backup original chunks before enhancement"
    )

    # Phrase Cleanup (NEW)
    enable_phrase_cleanup: bool = Field(
        default=True,
        description="Enable automatic phrase removal before enhancement",
    )
    cleanup_scope: Literal["none", "first_n_chunks", "all", "final_only"] = (
        Field(
            default="all",
            description="Controls which chunks run Whisper cleanup to save CPU",
        )
    )
    cleanup_first_n: int = Field(
        default=3,
        ge=1,
        description="Number of chunks to clean when cleanup_scope=first_n_chunks",
    )
    cleanup_target_phrases: List[str] = Field(
        default=[
            "You need to add some text for me to talk",
            "You need to add some text for me to talk.",
            "You need to add text for me to talk",
            "You need to add text for me to talk.",
        ],
        description="Phrases to detect and remove from audio chunks",
    )
    cleanup_whisper_model: str = Field(
        default="base",
        pattern=r"^(tiny|base|small|medium|large)$",
        description="Whisper model size for transcription (tiny, base, small, medium, large)",
    )
    cleanup_save_transcripts: bool = Field(
        default=False,
        description="Save SRT transcripts during cleanup for debugging",
    )

    # Advanced Audio Mastering (NEW)
    enable_deepfilternet: bool = Field(
        default=False,
        description="Use DeepFilterNet for professional noise reduction (replaces noisereduce when enabled)",
    )
    enable_matchering: bool = Field(
        default=False,
        description="Apply reference-based mastering using Matchering (GPL-3.0, internal use only)",
    )
    matchering_reference: Optional[str] = Field(
        default=None,
        description="Path to reference audio file for Matchering mastering (WAV format, stereo recommended)",
    )
    matchering_max_length: int = Field(
        default=1800,  # 30 minutes in seconds
        ge=60,
        le=7200,
        description="Maximum audio length for Matchering processing in seconds",
    )

    # Track user-specified overrides so profiles don't clobber them
    _user_overrides: Set[str] = PrivateAttr(default_factory=set)

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
        # Capture which fields the user explicitly set so profiles can respect overrides
        self._user_overrides = set(getattr(self, "model_fields_set", set()))
        self._apply_profile_defaults()

        path = Path(self.pipeline_json)
        if not path.exists():
            state = PipelineState(path, validate_on_read=False)
            with state.transaction(validate=False) as txn:
                phase_block = txn.data.setdefault("phase5", {})
                phase_block.setdefault("status", "pending")
                phase_block.setdefault("files", {})
                phase_block.setdefault("errors", [])
                phase_block.setdefault("timestamps", {})
        return self

    def _apply_profile_defaults(self) -> None:
        """Apply profile-tuned defaults without overwriting user overrides."""
        cores = os.cpu_count() or 2
        cleanup_scope_overridden = "cleanup_scope" in self._user_overrides

        def set_if_missing(field_name: str, value):
            if field_name not in self._user_overrides:
                setattr(self, field_name, value)

        if self.profile == "laptop_safe":
            set_if_missing("max_workers", 1 if cores <= 4 else 2)
            set_if_missing("enable_rnnoise", True)
            set_if_missing("enable_silero_vad", True)
            set_if_missing("enable_deepfilternet", False)
            set_if_missing("enable_matchering", False)
            set_if_missing("cleanup_whisper_model", "tiny")
            set_if_missing("lufs_target", -23.0)
            if "enable_phrase_cleanup" not in self._user_overrides:
                # Default to skipping cleanup on constrained machines unless user opts in
                set_if_missing(
                    "enable_phrase_cleanup", cleanup_scope_overridden
                )
            if not cleanup_scope_overridden:
                set_if_missing("cleanup_scope", "none")
        elif self.profile == "full_master":
            set_if_missing("enable_rnnoise", False)
            set_if_missing("enable_deepfilternet", True)
            set_if_missing("enable_matchering", True)
            set_if_missing("max_workers", max(1, cores - 1))
            set_if_missing("cleanup_whisper_model", "base")
            set_if_missing("lufs_target", -19.0)
            set_if_missing("enable_phrase_cleanup", True)
        else:
            # auto profile - prefer modest parallelism and lighter models when heavy processors are enabled
            if "max_workers" not in self._user_overrides:
                default_workers = (
                    1
                    if self.enable_deepfilternet or self.enable_matchering
                    else min(4, cores)
                )
                set_if_missing("max_workers", default_workers)
            if "cleanup_whisper_model" not in self._user_overrides:
                set_if_missing("cleanup_whisper_model", "small")

    def is_user_override(self, field_name: str) -> bool:
        """Return True if a config value was provided explicitly by the user."""
        return field_name in self._user_overrides

    class Config:
        validate_assignment = True
        extra = "forbid"


class AudioMetadata(BaseModel):
    """Metadata for audio chunks"""

    chunk_id: int
    wav_path: str
    enhanced_path: Optional[str] = None
    text_len: Optional[int] = None
    est_dur: Optional[float] = None
    engine: Optional[str] = None
    rt_factor: Optional[float] = None
    snr_pre: Optional[float] = None
    snr_post: Optional[float] = None
    rms_pre: Optional[float] = None
    rms_post: Optional[float] = None
    rms_volume_norm_pre: Optional[float] = None
    rms_volume_norm_post: Optional[float] = None
    lufs_pre: Optional[float] = None
    lufs_post: Optional[float] = None
    speech_ratio_pre: Optional[float] = None
    speech_ratio_post: Optional[float] = None
    status: str = "pending"
    error_message: Optional[str] = None
    duration: Optional[float] = None
    # Phrase cleanup metadata
    cleanup_status: Optional[str] = (
        None  # 'cleaned', 'clean', 'disabled', 'error'
    )
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
    output_dir: Path = dataclass_field(
        default_factory=lambda: Path("subtitles")
    )
    file_id: str = "audiobook"
    pipeline_json: Optional[Path] = None

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
    use_aeneas_alignment: bool = (
        False  # Optional forced alignment with reference text
    )

    # Alignment
    enable_drift_correction: bool = True
    drift_correction_threshold: float = 1.0  # Correct if drift >1 sec

    def __post_init__(self):
        """Ensure paths are Path objects."""
        self.audio_path = Path(self.audio_path)
        self.output_dir = Path(self.output_dir)
        if self.reference_text_path:
            self.reference_text_path = Path(self.reference_text_path)
        if self.pipeline_json:
            self.pipeline_json = Path(self.pipeline_json)
