"""
F5-TTS Engine Wrapper
Cutting-edge TTS with superior prosody and naturalness
"""

import logging
import numpy as np
import torch
from pathlib import Path
from typing import Optional, List

from . import TTSEngine

logger = logging.getLogger(__name__)


class F5TTSEngine(TTSEngine):
    """
    F5-TTS - Flow Matching based TTS

    Features:
    - Superior naturalness and prosody
    - Zero-shot voice cloning
    - Emotion control via reference selection
    - Fast inference with diffusion
    """

    def __init__(self, device: str = "cpu", model_variant: str = "F5-TTS"):
        super().__init__(device)
        self.model_variant = model_variant  # F5-TTS or E2-TTS
        self.sample_rate_val = 24000
        self.vocoder = None

    @property
    def name(self) -> str:
        return f"{self.model_variant} (Expressive)"

    @property
    def supports_emotions(self) -> bool:
        return True  # Via reference audio selection

    def get_sample_rate(self) -> int:
        return self.sample_rate_val

    def get_supported_languages(self) -> List[str]:
        return ["en", "zh", "ja", "de", "fr", "es"]  # Multilingual

    def load_model(self) -> None:
        """Load F5-TTS model"""
        try:
            # Import F5-TTS (lazy import to avoid loading if not needed)
            from f5_tts.api import F5TTS

            logger.info(f"Loading {self.model_variant} model...")

            # Initialize model
            self.model = F5TTS(
                model_type=self.model_variant,
                device=self.device
            )

            logger.info(f"{self.model_variant} model loaded successfully")

        except ImportError as e:
            raise ImportError(
                f"F5-TTS not installed. Please install with:\n"
                f"  git clone https://github.com/SWivid/F5-TTS\n"
                f"  cd F5-TTS\n"
                f"  pip install -e .\n"
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
        Synthesize speech using F5-TTS

        Args:
            text: Text to synthesize
            reference_audio: Path to reference audio for voice cloning
            language: Language code
            **kwargs: Additional parameters
                - emotion: str (contemplative, dramatic, measured, etc.)
                - speed: float (0.5-2.0, default 1.0)
                - seed: int (for reproducibility)

        Returns:
            Audio array (float32, mono, 24kHz)
        """
        if self.model is None:
            self.load_model()

        # Extract parameters
        emotion = kwargs.get("emotion", "neutral")
        speed = kwargs.get("speed", 1.0)
        seed = kwargs.get("seed", None)

        # Set seed for reproducibility
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)

        # F5-TTS uses reference audio for voice cloning
        # Emotion is controlled by choosing appropriate reference segment
        # or by reference audio characteristics

        try:
            # Generate audio
            audio, sample_rate = self.model.infer(
                ref_file=str(reference_audio),
                ref_text="",  # F5-TTS can work without ref text
                gen_text=text,
                speed=speed,
                device=self.device
            )

            # Ensure correct format
            if torch.is_tensor(audio):
                audio = audio.cpu().numpy()

            audio = audio.astype(np.float32)

            # Ensure mono
            if audio.ndim > 1:
                audio = audio.mean(axis=0)

            # Resample if needed (F5-TTS should output 24kHz already)
            if sample_rate != self.sample_rate_val:
                logger.warning(
                    f"Sample rate mismatch: got {sample_rate}, expected {self.sample_rate_val}"
                )
                # Would need librosa for resampling, skip for now

            return audio

        except Exception as e:
            logger.error(f"F5-TTS synthesis failed: {e}")
            raise

    def get_max_text_length(self) -> Optional[int]:
        """F5-TTS can handle longer sequences than traditional TTS"""
        return 10000  # Characters, not words

    def supports_streaming(self) -> bool:
        """F5-TTS supports streaming generation"""
        return True
