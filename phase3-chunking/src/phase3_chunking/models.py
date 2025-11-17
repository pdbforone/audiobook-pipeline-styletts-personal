from pydantic import BaseModel, field_validator, model_validator
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ChunkRecord(BaseModel):
    """Record of chunking results for a text file."""
    text_path: str
    chunk_paths: List[str]
    coherence_scores: List[float]
    readability_scores: List[float]
    embeddings: List[List[float]]
    status: str  # 'success', 'partial', 'failed'
    errors: List[str] = []
    timestamps: Dict[str, float] = {}
    chunk_metrics: Optional[Dict[str, Any]] = None  # Chunk size/duration metrics
    source_hash: Optional[str] = None  # Hash of source text to enable reuse
    
    # NEW: Genre-aware fields
    applied_profile: Optional[str] = None  # Genre profile used (e.g., 'philosophy', 'fiction')
    genre_confidence: Optional[float] = None  # Confidence score for genre detection (0-1)
    suggested_voice: Optional[str] = None  # Selected voice ID for TTS (e.g., 'jim_locke')
    coherence_threshold: Optional[float] = None
    flesch_threshold: Optional[float] = None

    class Config:
        arbitrary_types_allowed = True  # Allow 'any' type for chunk_metrics

    @field_validator("text_path")
    @classmethod
    def validate_text_path(cls, v: str) -> str:
        """Ensure text_path is not empty."""
        if not v or not v.strip():
            raise ValueError("text_path cannot be empty")
        return v

    @field_validator("chunk_paths")
    @classmethod
    def validate_chunk_paths(cls, v: List[str]) -> List[str]:
        """Ensure at least one chunk was created."""
        if not v:
            logger.warning("No chunk paths provided")
        return v

    @field_validator("coherence_scores")
    @classmethod
    def validate_coherence(cls, v: List[float]) -> List[float]:
        """Check coherence scores and log warnings."""
        if not v:
            logger.warning("No coherence scores provided")
            return v

        # Check for invalid scores
        for i, score in enumerate(v):
            if not (0.0 <= score <= 1.0):
                logger.warning(f"Coherence score {i} out of range: {score}")

        return v

    @field_validator("readability_scores")
    @classmethod
    def validate_readability(cls, v: List[float]) -> List[float]:
        """Check readability scores and log warnings."""
        if not v:
            logger.warning("No readability scores provided")
            return v

        avg = sum(v) / len(v)

        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Ensure status is one of the expected values."""
        valid_statuses = {"success", "partial", "failed"}
        if v not in valid_statuses:
            logger.warning(f"Unexpected status '{v}', using 'partial'")
            return "partial"
        return v

    @model_validator(mode="after")
    def check_consistency(self) -> "ChunkRecord":
        """
        Validate consistency across fields and populate errors list.
        """
        # Check that list lengths are consistent
        num_chunks = len(self.chunk_paths)

        if self.coherence_scores and len(self.coherence_scores) != num_chunks - 1:
            # Coherence is between consecutive chunks, so should be n-1
            if len(self.coherence_scores) != max(0, num_chunks - 1):
                logger.warning(
                    f"Coherence scores mismatch: expected {max(0, num_chunks - 1)}, "
                    f"got {len(self.coherence_scores)}"
                )

        if self.readability_scores and len(self.readability_scores) != num_chunks:
            logger.warning(
                f"Readability scores mismatch: expected {num_chunks}, "
                f"got {len(self.readability_scores)}"
            )

        if self.embeddings and len(self.embeddings) != num_chunks:
            logger.warning(
                f"Embeddings mismatch: expected {num_chunks}, "
                f"got {len(self.embeddings)}"
            )

        # Check chunk duration warnings
        if self.chunk_metrics:
            max_duration = self.chunk_metrics.get("max_duration", 0)
            limit = self.chunk_metrics.get("max_duration_limit", 25.0)
            if max_duration > limit:
                error_msg = (
                    f"Some chunks exceed {limit:.1f}s duration (max: {max_duration:.1f}s)"
                )
                if error_msg not in self.errors:
                    self.errors.append(error_msg)

        # Check aggregate coherence/readability against thresholds if provided
        avg_coherence = (
            sum(self.coherence_scores) / len(self.coherence_scores)
            if self.coherence_scores
            else None
        )
        avg_flesch = (
            sum(self.readability_scores) / len(self.readability_scores)
            if self.readability_scores
            else None
        )

        coherence_limit = self.coherence_threshold or 0.87
        if avg_coherence is not None and avg_coherence < coherence_limit:
            error_msg = (
                f"Low coherence: {avg_coherence:.4f} < {coherence_limit:.2f}"
            )
            if error_msg not in self.errors:
                self.errors.append(error_msg)

        flesch_limit = self.flesch_threshold or 60.0
        if avg_flesch is not None and avg_flesch < flesch_limit:
            error_msg = (
                f"Low readability: {avg_flesch:.2f} < {flesch_limit:.1f}"
            )
            if error_msg not in self.errors:
                self.errors.append(error_msg)

        # Validate timestamps
        if self.timestamps:
            required_keys = {"start", "end", "duration"}
            missing_keys = required_keys - set(self.timestamps.keys())
            if missing_keys:
                logger.warning(f"Missing timestamp keys: {missing_keys}")

            if "start" in self.timestamps and "end" in self.timestamps:
                calculated_duration = self.timestamps["end"] - self.timestamps["start"]
                if "duration" in self.timestamps:
                    reported_duration = self.timestamps["duration"]
                    if abs(calculated_duration - reported_duration) > 0.01:
                        logger.warning(
                            f"Duration mismatch: calculated {calculated_duration:.4f}s, "
                            f"reported {reported_duration:.4f}s"
                        )

        return self

    def get_metrics(self) -> Dict[str, float]:
        """Calculate and return summary metrics."""
        metrics = {
            "num_chunks": len(self.chunk_paths),
            "avg_coherence": (
                sum(self.coherence_scores) / len(self.coherence_scores)
                if self.coherence_scores
                else 0.0
            ),
            "avg_flesch": (
                sum(self.readability_scores) / len(self.readability_scores)
                if self.readability_scores
                else 0.0
            ),
            "duration": self.timestamps.get("duration", 0.0),
        }

        # Add quality flags
        coherence_limit = self.coherence_threshold or 0.87
        flesch_limit = self.flesch_threshold or 60.0
        metrics["high_coherence"] = metrics["avg_coherence"] >= coherence_limit
        metrics["high_readability"] = metrics["avg_flesch"] >= flesch_limit
        metrics["coherence_threshold"] = coherence_limit
        metrics["flesch_threshold"] = flesch_limit

        # Add chunk size/duration metrics if available
        if self.chunk_metrics:
            metrics.update({
                "avg_char_length": self.chunk_metrics.get("avg_char_length", 0),
                "avg_word_count": self.chunk_metrics.get("avg_word_count", 0),
                "avg_chunk_duration": self.chunk_metrics.get("avg_duration", 0),
                "max_chunk_duration": self.chunk_metrics.get("max_duration", 0),
                "min_chunk_duration": self.chunk_metrics.get("min_duration", 0),
                "chunk_char_lengths": self.chunk_metrics.get("chunk_char_lengths", []),
                "chunk_durations": self.chunk_metrics.get("chunk_durations", []),
            })
        
        # Add genre-aware metrics if available
        if self.applied_profile:
            metrics["applied_profile"] = self.applied_profile
        if self.genre_confidence is not None:
            metrics["genre_confidence"] = self.genre_confidence
        if self.suggested_voice:
            metrics["suggested_voice"] = self.suggested_voice

        return metrics

    def is_successful(self) -> bool:
        """Check if chunking was successful based on status and errors."""
        return self.status == "success" and not self.errors


class ValidationConfig(BaseModel):
    """Configuration for validation thresholds."""

    coherence_threshold: float = 0.87
    flesch_threshold: float = 60.0
    min_chunk_words: int = 200
    max_chunk_words: int = 400
    min_chunk_chars: int = 1000  # Character-based limit (optimized)
    max_chunk_chars: int = 2000  # Character-based limit (optimized)
    max_chunk_duration: float = 25.0  # Duration limit in seconds
    soft_chunk_chars: int = 1800  # Preferred upper bound before completion kicks in
    hard_chunk_chars: int = 2000  # Historic max; still enforced before emergency rules
    emergency_chunk_chars: int = 3000  # Absolute max to avoid TTS corruption
    emergency_chunk_duration: float = 38.0  # Absolute duration ceiling
    genre_profile: str = "auto"  # Preferred genre profile for voice/metric selection

    @field_validator("coherence_threshold")
    @classmethod
    def validate_coherence_threshold(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"coherence_threshold must be between 0 and 1, got {v}")
        return v

    @field_validator("flesch_threshold")
    @classmethod
    def validate_flesch_threshold(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError(f"flesch_threshold must be between 0 and 100, got {v}")
        return v

    @field_validator("min_chunk_words")
    @classmethod
    def validate_min_words(cls, v: int) -> int:
        if v < 10:
            raise ValueError(f"min_chunk_words must be at least 10, got {v}")
        return v

    @field_validator("max_chunk_words")
    @classmethod
    def validate_max_words(cls, v: int) -> int:
        if v < 50:
            raise ValueError(f"max_chunk_words must be at least 50, got {v}")
        return v

    @field_validator("min_chunk_chars")
    @classmethod
    def validate_min_chars(cls, v: int) -> int:
        if v < 100:
            raise ValueError(f"min_chunk_chars must be at least 100, got {v}")
        return v

    @field_validator("max_chunk_chars")
    @classmethod
    def validate_max_chars(cls, v: int) -> int:
        if v < 200:
            raise ValueError(f"max_chunk_chars must be at least 200, got {v}")
        return v
    
    @field_validator("soft_chunk_chars")
    @classmethod
    def validate_soft_chars(cls, v: int, info) -> int:
        min_chars = info.data.get("min_chunk_chars", 1000)
        if v < min_chars:
            raise ValueError(f"soft_chunk_chars ({v}) must be >= min_chunk_chars ({min_chars})")
        return v

    @field_validator("hard_chunk_chars")
    @classmethod
    def validate_hard_chars(cls, v: int, info) -> int:
        soft_chars = info.data.get("soft_chunk_chars", 1800)
        if v < soft_chars:
            raise ValueError(f"hard_chunk_chars ({v}) must be >= soft_chunk_chars ({soft_chars})")
        return v

    @field_validator("emergency_chunk_chars")
    @classmethod
    def validate_emergency_chars(cls, v: int, info) -> int:
        hard_chars = info.data.get("hard_chunk_chars", 2000)
        if v <= hard_chars:
            raise ValueError(f"emergency_chunk_chars ({v}) must be > hard_chunk_chars ({hard_chars})")
        return v

    @field_validator("emergency_chunk_duration")
    @classmethod
    def validate_emergency_duration(cls, v: float, info) -> float:
        max_duration = info.data.get("max_chunk_duration", 25.0)
        if v <= max_duration:
            raise ValueError(
                f"emergency_chunk_duration ({v}) must be greater than max_chunk_duration ({max_duration})"
            )
        return v

    @model_validator(mode="after")
    def check_word_limits(self) -> "ValidationConfig":
        """Ensure min < max for both words and chars."""
        if self.min_chunk_words >= self.max_chunk_words:
            raise ValueError(
                f"min_chunk_words ({self.min_chunk_words}) must be less than "
                f"max_chunk_words ({self.max_chunk_words})"
            )
        if self.min_chunk_chars >= self.max_chunk_chars:
            raise ValueError(
                f"min_chunk_chars ({self.min_chunk_chars}) must be less than "
                f"max_chunk_chars ({self.max_chunk_chars})"
            )
        if self.min_chunk_chars > self.soft_chunk_chars:
            raise ValueError(
                f"min_chunk_chars ({self.min_chunk_chars}) must be <= soft_chunk_chars ({self.soft_chunk_chars})"
            )
        if self.soft_chunk_chars > self.hard_chunk_chars:
            raise ValueError(
                f"soft_chunk_chars ({self.soft_chunk_chars}) must be <= hard_chunk_chars ({self.hard_chunk_chars})"
            )
        if self.hard_chunk_chars > self.emergency_chunk_chars:
            raise ValueError(
                f"hard_chunk_chars ({self.hard_chunk_chars}) must be <= emergency_chunk_chars ({self.emergency_chunk_chars})"
            )
        if self.emergency_chunk_duration <= self.max_chunk_duration:
            raise ValueError(
                f"emergency_chunk_duration ({self.emergency_chunk_duration}) must be > max_chunk_duration ({self.max_chunk_duration})"
            )
        if self.max_chunk_chars != self.hard_chunk_chars:
            logger.debug(
                "max_chunk_chars differs from hard_chunk_chars; aligning for backward compatibility"
            )
            self.max_chunk_chars = self.hard_chunk_chars
        return self
