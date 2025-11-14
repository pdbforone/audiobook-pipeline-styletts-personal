# models.py - Pydantic Models for Phase 4
# Why: Validates config and records data before writing to pipeline.json. Ensures type safety and schema compliance.
# Place in phase4_tts/models.py; import in main.py and utils.py.

from pydantic import BaseModel, field_validator, ValidationError
from typing import Dict, List, Optional

class TTSConfig(BaseModel):
    sample_rate: int = 24000
    language: str = "en"
    ref_url: str
    exaggeration: float = 0.5
    cfg_weight: float = 2.0
    temperature: float = 0.7
    sub_chunk_retries: int = 3
    silence_duration: float = 0.5
    enable_splitting: bool = True
    split_char_limit: int = 1200
    output_dir: str = "audio_chunks"

    @field_validator("ref_url")
    @classmethod
    def validate_ref_url(cls, v):
        if not v.startswith("http"):
            raise ValueError("ref_url must be a valid HTTP URL for reference audio")
        return v

class TTSRecord(BaseModel):
    chunk_id: str
    audio_path: str
    status: str  # "success", "failed", "partial"
    mos_score: float = 0.0  # Proxy quality metric (e.g., from librosa features)
    duration: float  # Seconds of generated audio
    metrics: Dict[str, float] = {}
    errors: List[str] = []
    timestamps: Dict[str, float] = {}  # start, end, duration
    split_metadata: Optional[Dict] = None  # If splitting used: num_sub_chunks, etc.
