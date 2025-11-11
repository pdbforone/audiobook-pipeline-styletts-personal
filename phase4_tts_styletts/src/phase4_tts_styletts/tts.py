"""
Kokoro-82M powered narrator wrapper for Phase 4.

Provides the same synth(text, out_path) API that the orchestrator expects,
but routes all TTS requests through Kokoro's lightweight pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np
import soundfile as sf
from kokoro import KPipeline

logger = logging.getLogger(__name__)


@dataclass
class StyleControls:
    """Post-processing knobs for slight timbre shaping."""

    rate: float = 1.00
    timbre: float = 0.08
    prosody_variance: float = 0.12
    formant_shift: float = 1.005
    remove_breaths: bool = True


DEFAULT_VOICE = "af_sky"
VOICE_ALIASES = {
    "female_default": "af_sky",
    "af_bella": "af_bella",
    "af_sarah": "af_sarah",
    "af_nicole": "af_nicole",
    "af_sky": "af_sky",
    "am_adam": "am_adam",
    "am_michael": "am_michael",
    "male_default": "am_adam",
}


class BritishFormalNarrator:
    """
    Thin wrapper around Kokoro's 82M pipeline with audiobook-friendly defaults.
    """

    def __init__(
        self,
        reference_audio: Optional[Union[str, Path]] = None,
        sample_rate: int = 24000,
        controls: Optional[StyleControls] = None,
        model_name: Optional[str] = None,
        voice_id: str = DEFAULT_VOICE,
    ) -> None:
        self.sample_rate = sample_rate
        self.controls = controls or StyleControls()
        self.voice_id = VOICE_ALIASES.get(voice_id.lower(), voice_id) if isinstance(voice_id, str) else DEFAULT_VOICE
        self._pipeline = KPipeline(lang_code="a")
        self.set_reference_audio(reference_audio)

    def set_reference_audio(self, reference_audio: Optional[Union[str, Path]]) -> None:
        """
        Kokoro does not currently support voice cloning, so reference audio is ignored.
        This method exists to preserve the previous API surface.
        """
        if reference_audio:
            logger.info("Reference audio '%s' supplied but ignored (Kokoro uses preset voices).", reference_audio)

    def synth(self, text: str, out_path: Union[str, Path]) -> None:
        """Synthesize text to the requested path."""
        if not text or not text.strip():
            raise ValueError("Text must be a non-empty string")

        target_path = Path(out_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        generator = self._pipeline(text.strip(), voice=self.voice_id)
        segments = []
        for _, _, audio in generator:
            segments.append(np.asarray(audio, dtype=np.float32))

        if not segments:
            raise RuntimeError("Kokoro pipeline returned no audio samples.")

        full_audio = np.concatenate(segments) if len(segments) > 1 else segments[0]
        processed = self._post_process(full_audio)
        sf.write(target_path, processed, self.sample_rate)
        logger.debug("Wrote %s (samples=%d)", target_path, processed.shape[0])

    # -------- Internal helpers -------- #

    def _post_process(self, audio: np.ndarray) -> np.ndarray:
        """
        Basic normalization to keep downstream processing consistent.
        """
        processed = np.copy(audio).astype(np.float32)
        peak = float(np.max(np.abs(processed))) or 1.0
        processed = processed / peak * 0.95
        return processed


__all__ = ["BritishFormalNarrator", "StyleControls", "VOICE_ALIASES"]
