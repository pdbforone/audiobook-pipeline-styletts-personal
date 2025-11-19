"""
Kokoro ONNX Engine - Direct Integration
Fast, CPU-friendly TTS without Chatterbox wrapper
"""

import logging
import os
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
            import kokoro_onnx as kokoro

            logger.info("Loading Kokoro-82M ONNX model...")

            # Model files are in phase4_tts/models/kokoro/
            model_dir = Path(__file__).parent.parent / "models" / "kokoro"
            env_model_path = os.getenv("KOKORO_MODEL_PATH")
            model_path = Path(env_model_path).expanduser() if env_model_path else model_dir / "kokoro-v1.0.onnx"
            # Kokoro releases ship a binary voice pack (voices-v1.0.bin). Keep JSON support if present.
            env_voices_path = os.getenv("KOKORO_VOICES_PATH")
            voices_bin = model_dir / "voices-v1.0.bin"
            voices_json = model_dir / "voices.json"
            voices_path = Path(env_voices_path).expanduser() if env_voices_path else (voices_json if voices_json.exists() else voices_bin)

            if not model_path.exists() or not voices_path.exists():
                raise FileNotFoundError(
                    f"Kokoro model files not found. Please download:\n"
                    f"  wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx\n"
                    f"  wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin\n"
                    f"and place them in {model_dir}"
                )

            # Initialize Kokoro with model paths
            self.model = kokoro.Kokoro(str(model_path), str(voices_path))

            logger.info("Kokoro-82M model loaded successfully")
            if env_model_path:
                logger.info("Using custom Kokoro model path from KOKORO_MODEL_PATH: %s", model_path)
            if env_voices_path:
                logger.info("Using custom Kokoro voices from KOKORO_VOICES_PATH: %s", voices_path)

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
                - voice: str (voice ID, default "af_sarah")

        Returns:
            Audio array (float32, mono, 24kHz)
        """
        if self.model is None:
            self.load_model()

        # Extract parameters
        speed = kwargs.get("speed", 1.0)
        voice = kwargs.get("voice", "af_sarah")  # Default female voice

        # Map language code to kokoro format
        lang_map = {
            "en": "en-us",
            "en-us": "en-us",
            "en-gb": "en-gb",
        }
        kokoro_lang = lang_map.get(language, "en-us")

        try:
            # Generate audio using create() method
            # Returns (samples, sample_rate) tuple
            audio, sample_rate = self.model.create(
                text,
                voice=voice,
                speed=speed,
                lang=kokoro_lang
            )

            # Ensure correct sample rate
            if sample_rate != self.sample_rate_val:
                logger.warning(f"Sample rate mismatch: got {sample_rate}, expected {self.sample_rate_val}")
                self.sample_rate_val = sample_rate

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
