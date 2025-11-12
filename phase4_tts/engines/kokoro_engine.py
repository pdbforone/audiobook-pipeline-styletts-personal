"""
Kokoro ONNX Engine - Direct Integration
Fast, CPU-friendly TTS without Chatterbox wrapper
"""

import logging
import numpy as np
from pathlib import Path
from typing import Optional, List

from . import TTSEngine

logger = logging.getLogger(__name__)


class KokoroEngine(TTSEngine):
    """
    Kokoro-82M Direct - Fast CPU-friendly TTS

    Features:
    - Fast inference (CPU-optimized)
    - Clean, clear speech
    - Low resource requirements
    - ONNX runtime (cross-platform)
    """

    def __init__(self, device: str = "cpu"):
        super().__init__(device)
        self.sample_rate_val = 24000

    @property
    def name(self) -> str:
        return "Kokoro-82M (CPU-Friendly)"

    @property
    def supports_emotions(self) -> bool:
        return False  # Basic prosody only

    def get_sample_rate(self) -> int:
        return self.sample_rate_val

    def get_supported_languages(self) -> List[str]:
        return ["en"]  # English only

    def load_model(self) -> None:
        """Load Kokoro ONNX model"""
        try:
            # Import kokoro-onnx
            import kokoro

            logger.info("Loading Kokoro-82M ONNX model...")

            # Initialize Kokoro
            self.model = kokoro.Kokoro(
                lang="en-us",  # US English
                speed=1.0
            )

            logger.info("Kokoro-82M model loaded successfully")

        except ImportError as e:
            raise ImportError(
                f"kokoro-onnx not installed. Please install with:\n"
                f"  pip install kokoro-onnx\n"
                f"Error: {e}"
            )

    def synthesize(
        self,
        text: str,
        reference_audio: Path,
        language: str = "en",
        **kwargs
    ) -> np.ndarray:
        """
        Synthesize speech using Kokoro ONNX

        Args:
            text: Text to synthesize
            reference_audio: Path to reference audio (not used by Kokoro)
            language: Language code (only 'en' supported)
            **kwargs: Additional parameters
                - speed: float (0.5-2.0, default 1.0)
                - voice: str (voice ID, default "af_bella")

        Returns:
            Audio array (float32, mono, 24kHz)
        """
        if self.model is None:
            self.load_model()

        # Extract parameters
        speed = kwargs.get("speed", 1.0)
        voice = kwargs.get("voice", "af_bella")  # Default female voice

        # Set voice
        self.model.set_voice(voice)

        # Set speed
        self.model.set_speed(speed)

        try:
            # Generate audio samples
            # Kokoro returns iterator of audio chunks
            audio_chunks = []
            for chunk in self.model.create(text):
                audio_chunks.append(chunk)

            # Concatenate chunks
            if audio_chunks:
                audio = np.concatenate(audio_chunks)
            else:
                # Return silence if no audio generated
                audio = np.zeros(int(0.1 * self.sample_rate_val), dtype=np.float32)

            # Ensure float32 and mono
            audio = audio.astype(np.float32)
            if audio.ndim > 1:
                audio = audio.mean(axis=0)

            # Normalize
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio)) * 0.95

            return audio

        except Exception as e:
            logger.error(f"Kokoro synthesis failed: {e}")
            raise

    def get_max_text_length(self) -> Optional[int]:
        """Kokoro can handle long text with splitting"""
        return 5000  # Characters

    def get_available_voices(self) -> List[str]:
        """Get list of available Kokoro voices"""
        # Kokoro has multiple voices available
        return [
            "af_bella",  # Female, warm
            "af_sarah",  # Female, clear
            "am_adam",   # Male, deep
            "am_michael" # Male, neutral
        ]
