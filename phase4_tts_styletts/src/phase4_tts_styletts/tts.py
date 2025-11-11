"""
BritishFormalNarrator - StyleTTS2 wrapper tuned for audiobook narration.

This module keeps the StyleTTS2 specific logic isolated from the main
phase4 orchestration code so that Phase 6 can select the desired engine
at runtime without duplicating heavy dependencies.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import librosa
import numpy as np
import soundfile as sf
import torch

logger = logging.getLogger(__name__)


def _load_styletts2(model_name: str):
    """
    Load a pretrained StyleTTS2 model.

    The upstream package currently exposes different entry points depending
    on version. We prefer StyleTTS2.load_pretrained() when available and
    fall back to direct instantiation otherwise.
    """
    from styletts2 import tts as styletts2_tts

    StyleTTS2Class = getattr(styletts2_tts, "StyleTTS2")
    load_pretrained = getattr(StyleTTS2Class, "load_pretrained", None)

    original_load = torch.load

    def permissive_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    torch.load = permissive_load

    safe_globals = getattr(torch.serialization, "add_safe_globals", None)
    if safe_globals:
        allowed = [getattr]
        try:
            from torch.optim.lr_scheduler import OneCycleLR

            allowed.append(OneCycleLR)
        except Exception:
            logger.debug("Unable to import OneCycleLR for safe globals", exc_info=True)

        try:
            from torch.optim.adamw import AdamW

            allowed.append(AdamW)
        except Exception:
            logger.debug("Unable to import AdamW for safe globals", exc_info=True)

        try:
            from collections import defaultdict

            allowed.append(defaultdict)
        except Exception:
            logger.debug("Unable to import defaultdict for safe globals", exc_info=True)

        try:
            safe_globals(allowed)
        except Exception:
            logger.debug("Failed to register torch safe globals", exc_info=True)

    if load_pretrained:
        logger.info("Loading StyleTTS2 via load_pretrained('%s')", model_name)
        return load_pretrained(model_name)

    if model_name != "vctk_base":
        raise ValueError(f"Model '{model_name}' is not supported by this build")

    logger.info("Loading StyleTTS2 default model for '%s'", model_name)
    return StyleTTS2Class()


@dataclass
class StyleControls:
    rate: float = 1.0
    timbre: float = 0.18
    prosody_variance: float = 0.14
    formant_shift: float = 1.015
    remove_breaths: bool = True


class BritishFormalNarrator:
    """
    Thin wrapper around StyleTTS2 tuned for calmer British narration.

    The class loads a pretrained StyleTTS2 checkpoint, applies a fixed
    reference embedding, and exposes a synth() helper that writes WAV
    files that downstream phases expect.
    """

    def __init__(
        self,
        reference_audio: Union[str, Path] = Path("Voices/calm_narrator/reference.wav"),
        sample_rate: int = 24000,
        controls: Optional[StyleControls] = None,
        model_name: str = "vctk_base",
    ) -> None:
        self.sample_rate = sample_rate
        self.controls = controls or StyleControls()
        self._reference_audio = Path(reference_audio)
        self._model = _load_styletts2(model_name)
        self._style_vector = None
        self.set_reference_audio(self._reference_audio)

    def set_reference_audio(self, reference_audio: Union[str, Path]) -> None:
        """Cache style embedding from the provided reference clip."""
        reference_path = Path(reference_audio)
        if not reference_path.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_path}")

        self._reference_audio = reference_path.resolve()
        logger.info("Loading reference style from %s", self._reference_audio)
        self._style_vector = self._model.compute_style(str(self._reference_audio))

    def synth(self, text: str, out_path: Union[str, Path]) -> None:
        """Synthesize `text` to `out_path` using the configured controls."""
        if not text or not text.strip():
            raise ValueError("Text must be a non-empty string")

        target_path = Path(out_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug("Synthesizing chunk to %s", target_path)
        audio = self._model.inference(
            text=text.strip(),
            target_voice_path=str(self._reference_audio),
            output_sample_rate=self.sample_rate,
            alpha=self.controls.timbre,
            beta=self.controls.prosody_variance,
            embedding_scale=self.controls.formant_shift,
            ref_s=self._style_vector,
        )

        audio = np.asarray(audio, dtype=np.float32)
        audio = self._post_process(audio)
        sf.write(target_path, audio, self.sample_rate)

    # -------- Internal helpers -------- #

    def _post_process(self, audio: np.ndarray) -> np.ndarray:
        processed = np.copy(audio)

        if not math.isclose(self.controls.rate, 1.0, rel_tol=1e-3):
            processed = self._time_stretch(processed, self.controls.rate)

        if not math.isclose(self.controls.formant_shift, 1.0, rel_tol=1e-3):
            processed = self._pitch_shift(processed, self.controls.formant_shift)

        if self.controls.remove_breaths:
            processed = self._suppress_breaths(processed)

        peak = float(np.max(np.abs(processed))) or 1.0
        processed = processed / peak * 0.95
        return processed.astype(np.float32)

    @staticmethod
    def _time_stretch(audio: np.ndarray, rate: float) -> np.ndarray:
        rate = max(rate, 1e-2)
        try:
            return librosa.effects.time_stretch(audio, rate)
        except Exception as exc:  # pragma: no cover - librosa errors are rare
            logger.warning("Time stretch failed (%s). Returning original audio.", exc)
            return audio

    def _pitch_shift(self, audio: np.ndarray, ratio: float) -> np.ndarray:
        try:
            steps = 12 * math.log2(max(ratio, 1e-3))
            return librosa.effects.pitch_shift(audio, sr=self.sample_rate, n_steps=steps)
        except Exception as exc:  # pragma: no cover
            logger.warning("Pitch shift failed (%s). Returning original audio.", exc)
            return audio

    @staticmethod
    def _suppress_breaths(audio: np.ndarray) -> np.ndarray:
        """
        Apply a simple noise gate that removes short, low-energy breaths.
        """
        window = 1024
        energy = np.convolve(np.abs(audio), np.ones(window) / window, mode="same")
        mask = energy > 0.015
        return audio * mask


__all__ = ["BritishFormalNarrator", "StyleControls"]
