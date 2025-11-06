from pydantic import BaseModel, ValidationError, field_validator
from typing import List
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ChunkMetadata(BaseModel):
    text_path: str
    chunks: List[str]
    coherence_scores: List[float]
    readability_scores: List[float]

    @field_validator("coherence_scores")
    @classmethod
    def validate_coherence(cls, v: List[float]) -> List[float]:
        if any(score <= 0.87 for score in v):
            logging.warning(f"Low coherence detected: {min(v)} < 0.87")
        return v

    @field_validator("readability_scores")
    @classmethod
    def validate_readability(cls, v: List[float]) -> List[float]:
        if any(score <= 60 for score in v):
            logging.warning(f"Low readability detected: {min(v)} < 60 Flesch")
        return v

    @classmethod
    def create(cls, **data):
        try:
            return cls(**data)
        except ValidationError as e:
            logging.error(f"Validation failed: {e}")
            return cls(
                **{k: v for k, v in data.items() if k in cls.model_fields}
            )  # Fallback with partial data
