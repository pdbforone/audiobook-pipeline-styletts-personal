"""
XTTS v2 Engine Wrapper
Mature, production-tested TTS with excellent voice cloning
"""

import logging
import numpy as np
import torch
from pathlib import Path
from typing import Optional, List

from . import TTSEngine

logger = logging.getLogger(__name__)


class XTTSEngine(TTSEngine):
    """
    Coqui XTTS v2 - Production-grade multilingual TTS

    Features:
    - Excellent voice cloning (6-30s reference)
    - 17 language support
    - Emotion via reference audio
    - Stable, proven in production
    """

    def __init__(self, device: str = "cpu"):
        super().__init__(device)
        self.sample_rate_val = 24000

    @property
    def name(self) -> str:
        return "XTTS v2 (Versatile)"

    @property
    def supports_emotions(self) -> bool:
        return True  # Via reference audio with emotion

    def get_sample_rate(self) -> int:
        return self.sample_rate_val

    def get_supported_languages(self) -> List[str]:
        return [
            "en", "es", "fr", "de", "it", "pt", "pl", "tr",
            "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko"
        ]

    def load_model(self) -> None:
        """Load XTTS v2 model"""
        try:
            from TTS.api import TTS

            logger.info("Loading XTTS v2 model...")

            # Initialize XTTS
            self.model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False,
                gpu=(self.device == "cuda")
            )

            logger.info("XTTS v2 model loaded successfully")

        except ImportError as e:
            raise ImportError(
                f"Coqui TTS not installed. Please install with:\n"
                f"  pip install TTS\n"
                f"Error: {e}"
            )

    def synthesize(
        self,
        text: str,
        reference_audio: Optional[Path] = None,
        language: str = "en",
        **kwargs
    ) -> np.ndarray:
        """
        Synthesize speech using XTTS v2

        Args:
            text: Text to synthesize (max 250 characters)
            reference_audio: Optional path to reference audio for voice cloning
                           If None, uses default XTTS voice
            language: Language code
            **kwargs: Additional parameters
                - emotion: str (controlled via reference audio tone)
                - speed: float (0.5-2.0, default 1.0)
                - temperature: float (0.1-1.0, creativity)
                - speaker: str (default voice name if no reference_audio)

        Returns:
            Audio array (float32, mono, 24kHz)
        """
        if self.model is None:
            self.load_model()

        # Extract parameters
        speed = kwargs.get("speed", 1.0)
        temperature = kwargs.get("temperature", 0.7)
        speaker = kwargs.get("speaker", "Claribel Dervla")  # Default XTTS voice

        # Validate language
        if language not in self.get_supported_languages():
            logger.warning(
                f"Language {language} not in XTTS supported list, using 'en'"
            )
            language = "en"

        try:
            # Voice cloning vs default voice
            if reference_audio and reference_audio.exists():
                logger.info(f"Using voice cloning with reference: {reference_audio}")
                # Generate audio using XTTS with voice cloning
                wav = self.model.tts(
                    text=text,
                    speaker_wav=str(reference_audio),
                    language=language,
                    speed=speed,
                    temperature=temperature
                )
            else:
                if reference_audio:
                    logger.warning(f"Reference audio not found: {reference_audio}, using default voice")
                else:
                    logger.info(f"Using default XTTS voice: {speaker}")
                # Generate audio using XTTS default voice
                wav = self.model.tts(
                    text=text,
                    speaker=speaker,
                    language=language,
                    speed=speed,
                    temperature=temperature
                )

            # Convert to numpy array
            if isinstance(wav, list):
                audio = np.array(wav, dtype=np.float32)
            else:
                audio = wav.astype(np.float32)

            # Ensure mono
            if audio.ndim > 1:
                audio = audio.mean(axis=0)

            # XTTS outputs 24kHz by default, but verify
            # Normalization
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio)) * 0.95

            return audio

        except Exception as e:
            logger.error(f"XTTS synthesis failed: {e}")
            raise

    def get_max_text_length(self) -> Optional[int]:
        """XTTS v2 has a hard 250 character limit"""
        return 250  # Characters - XTTS v2 hard limit

    def supports_fine_tuning(self) -> bool:
        """XTTS supports fine-tuning for better voice adaptation"""
        return True
