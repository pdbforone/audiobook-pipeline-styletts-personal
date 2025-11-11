"""
TTS Engine Abstraction Layer
Provides unified interface for multiple TTS engines
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path
import numpy as np


class TTSEngine(ABC):
    """Abstract base class for TTS engines"""

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model = None

    @abstractmethod
    def load_model(self) -> None:
        """Load the TTS model"""
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        reference_audio: Path,
        language: str = "en",
        **kwargs
    ) -> np.ndarray:
        """
        Synthesize speech from text

        Args:
            text: Input text to synthesize
            reference_audio: Path to reference audio for voice cloning
            language: Language code
            **kwargs: Engine-specific parameters

        Returns:
            Audio array (numpy float32, mono)
        """
        pass

    @abstractmethod
    def get_sample_rate(self) -> int:
        """Return the sample rate of generated audio"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name"""
        pass

    @property
    @abstractmethod
    def supports_emotions(self) -> bool:
        """Whether engine supports emotion control"""
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """Return engine capabilities"""
        return {
            "name": self.name,
            "supports_emotions": self.supports_emotions,
            "sample_rate": self.get_sample_rate(),
            "max_text_length": self.get_max_text_length(),
            "languages": self.get_supported_languages(),
        }

    def get_max_text_length(self) -> Optional[int]:
        """Maximum text length per synthesis call"""
        return None  # No limit by default

    def get_supported_languages(self) -> List[str]:
        """List of supported language codes"""
        return ["en"]  # English by default
