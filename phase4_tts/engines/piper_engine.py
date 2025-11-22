"""
Piper TTS Engine - Ultra-fast CPU synthesis.

Piper is a fast, local neural text-to-speech system optimized for:
- Raspberry Pi and other low-power devices
- Real-time streaming
- Minimal resource usage

Performance: ~0.3x RTF on CPU (3x faster than real-time!)
Memory: ~200MB per model
Quality: Good (MOS ~3.8)

Installation:
    pip install piper-tts

Usage:
    engine = PiperEngine(device="cpu", voice="en_US-lessac-medium")
    engine.load_model()
    audio = engine.synthesize("Hello world", reference_audio=None)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from . import TTSEngine

logger = logging.getLogger(__name__)

# Voice configurations
PIPER_VOICES = {
    "en_US-lessac-medium": {
        "name": "Lessac",
        "language": "en_US",
        "quality": "medium",
        "sample_rate": 22050,
        "description": "Clear, neutral American English voice",
    },
    "en_US-amy-medium": {
        "name": "Amy",
        "language": "en_US",
        "quality": "medium",
        "sample_rate": 22050,
        "description": "Warm, friendly American English voice",
    },
    "en_GB-alan-medium": {
        "name": "Alan",
        "language": "en_GB",
        "quality": "medium",
        "sample_rate": 22050,
        "description": "British English male voice",
    },
}

DEFAULT_VOICE = "en_US-lessac-medium"


class PiperEngine(TTSEngine):
    """
    Piper TTS engine implementation.

    Ultra-fast CPU synthesis with good quality.
    Best used for:
    - Draft/preview generation
    - Rapid iteration during editing
    - Low-resource environments
    - When speed > quality
    """

    def __init__(self, device: str = "cpu", voice: str = DEFAULT_VOICE):
        super().__init__(device=device)
        self.voice = voice
        self._piper = None
        self._voice_config = PIPER_VOICES.get(voice, PIPER_VOICES[DEFAULT_VOICE])

    @property
    def name(self) -> str:
        return "Piper (Ultra-Fast)"

    @property
    def supports_emotions(self) -> bool:
        return False

    def get_sample_rate(self) -> int:
        return self._voice_config.get("sample_rate", 22050)

    def get_supported_languages(self) -> list:
        return ["en", "de", "es", "fr", "it", "pl", "pt", "ru", "uk", "nl"]

    def get_max_text_length(self) -> Optional[int]:
        """Piper handles long text well via internal chunking."""
        return 5000

    def load_model(self) -> None:
        """Load the Piper model."""
        try:
            from piper import PiperVoice
        except ImportError:
            logger.error(
                "Piper TTS not installed. Install with: pip install piper-tts"
            )
            raise RuntimeError(
                "Piper TTS not installed. Run: pip install piper-tts"
            )

        try:
            # Piper auto-downloads voices on first use
            logger.info(f"Loading Piper voice: {self.voice}")
            self._piper = PiperVoice.load(self.voice)
            logger.info(f"Piper voice loaded: {self.voice}")

        except Exception as e:
            logger.error(f"Failed to load Piper voice {self.voice}: {e}")
            raise

    def synthesize(
        self,
        text: str,
        reference_audio: Optional[Path] = None,
        language: str = "en",
        **kwargs,
    ) -> np.ndarray:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            reference_audio: Ignored (Piper doesn't support cloning)
            language: Language code (used for phoneme conversion)
            **kwargs: Additional parameters (ignored)

        Returns:
            Audio as numpy array (float32, mono)
        """
        if self._piper is None:
            self.load_model()

        if not text.strip():
            logger.warning("Empty text provided, returning silence")
            return np.zeros(int(self.get_sample_rate() * 0.5), dtype=np.float32)

        try:
            # Piper synthesize returns raw bytes
            audio_bytes = b""
            for audio_chunk in self._piper.synthesize_stream_raw(text):
                audio_bytes += audio_chunk

            # Convert to numpy
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            audio /= 32768.0  # Normalize to [-1, 1]

            return audio

        except Exception as e:
            logger.error(f"Piper synthesis failed: {e}")
            raise

    def __repr__(self) -> str:
        return f"PiperEngine(voice={self.voice})"


class PiperEngineStub(TTSEngine):
    """
    Stub implementation when Piper is not installed.

    Returns silence with a warning. Used to prevent crashes
    when Piper is referenced but not available.
    """

    def __init__(self, device: str = "cpu", voice: str = DEFAULT_VOICE):
        super().__init__(device=device)
        self.voice = voice
        self._warned = False

    @property
    def name(self) -> str:
        return "Piper (Not Installed)"

    @property
    def supports_emotions(self) -> bool:
        return False

    def get_sample_rate(self) -> int:
        return 22050

    def get_supported_languages(self) -> list:
        return ["en"]

    def get_max_text_length(self) -> Optional[int]:
        return 5000

    def load_model(self) -> None:
        if not self._warned:
            logger.warning(
                "Piper TTS not installed. Install with: pip install piper-tts"
            )
            self._warned = True

    def synthesize(
        self,
        text: str,
        reference_audio: Optional[Path] = None,
        language: str = "en",
        **kwargs,
    ) -> np.ndarray:
        if not self._warned:
            self.load_model()

        # Return silence of appropriate length
        # Estimate: ~150 words/minute = ~2.5 words/second
        words = len(text.split())
        duration_sec = max(1.0, words / 2.5)
        return np.zeros(int(self.get_sample_rate() * duration_sec), dtype=np.float32)


def get_piper_engine(device: str = "cpu", voice: str = DEFAULT_VOICE) -> TTSEngine:
    """
    Factory function to get Piper engine.

    Returns real engine if piper-tts installed, stub otherwise.
    """
    try:
        import piper  # noqa: F401
        return PiperEngine(device=device, voice=voice)
    except ImportError:
        logger.info("Piper not installed, using stub engine")
        return PiperEngineStub(device=device, voice=voice)
