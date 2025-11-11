"""
Chatterbox/Kokoro Engine Wrapper
Legacy engine - fast but limited expressiveness
"""

import sys
import logging
import torch
import numpy as np
from pathlib import Path
from typing import Optional

# Add Chatterbox to path
MODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MODULE_ROOT / "Chatterbox-TTS-Extended" / "chatterbox" / "src"))

try:
    from chatterbox.tts import ChatterboxTTS
except ImportError:
    ChatterboxTTS = None

from . import TTSEngine

logger = logging.getLogger(__name__)


class ChatterboxEngine(TTSEngine):
    """Chatterbox/Kokoro TTS Engine - fast, clear, basic prosody"""

    def __init__(self, device: str = "cpu"):
        super().__init__(device)
        self.sample_rate_val = 24000

    @property
    def name(self) -> str:
        return "Chatterbox (Kokoro-82M)"

    @property
    def supports_emotions(self) -> bool:
        return False

    def get_sample_rate(self) -> int:
        return self.sample_rate_val

    def load_model(self) -> None:
        """Load Chatterbox model"""
        if ChatterboxTTS is None:
            raise ImportError(
                "Chatterbox not available. Ensure Chatterbox-TTS-Extended is cloned "
                "in phase4_tts/Chatterbox-TTS-Extended"
            )

        logger.info("Loading Chatterbox model...")

        # Force CPU loading
        original_load = torch.load
        def cpu_load(*args, **kwargs):
            kwargs['map_location'] = 'cpu'
            return original_load(*args, **kwargs)
        torch.load = cpu_load

        self.model = ChatterboxTTS.from_pretrained(device=self.device)
        self.model.sr = self.sample_rate_val

        torch.load = original_load
        logger.info("Chatterbox model loaded successfully")

    def synthesize(
        self,
        text: str,
        reference_audio: Path,
        language: str = "en",
        **kwargs
    ) -> np.ndarray:
        """
        Synthesize speech using Chatterbox

        Args:
            text: Text to synthesize
            reference_audio: Path to reference audio
            language: Language (Chatterbox is English-only)
            **kwargs: Additional parameters (passed to model)

        Returns:
            Audio array (float32, mono)
        """
        if self.model is None:
            self.load_model()

        # Extract parameters
        exaggeration = kwargs.get("exaggeration", 0.5)
        cfg_weight = kwargs.get("cfg_weight", 0.5)
        temperature = kwargs.get("temperature", 0.7)

        # Synthesize
        audio = self.model.generate_speech(
            text=text,
            ref_audio=str(reference_audio),
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
        )

        # Convert to numpy if needed
        if torch.is_tensor(audio):
            audio = audio.cpu().numpy()

        # Ensure float32 and mono
        audio = audio.astype(np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=0)

        return audio

    def get_max_text_length(self) -> Optional[int]:
        """Chatterbox can handle long text with splitting"""
        return 5000  # Conservative limit
