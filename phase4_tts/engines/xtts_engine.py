"""
XTTS v2 Engine Wrapper
Mature, production-tested TTS with excellent voice cloning
"""

import logging
import numpy as np
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
        # Local default reference to satisfy XTTS builds that require speaker_wav
        self.default_reference = (
            Path(__file__).parent.parent
            / "voice_references"
            / "george_mckayland_trimmed.wav"
        )

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
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "pl",
            "tr",
            "ru",
            "nl",
            "cs",
            "ar",
            "zh-cn",
            "ja",
            "hu",
            "ko",
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
                gpu=(self.device == "cuda"),
            )

            # Attempt to attach bundled multi-speaker metadata (if available)
            try:
                from TTS.tts.utils.speakers import SpeakerManager
                import torch

                speakers_file = (
                    Path.home()
                    / "AppData"
                    / "Local"
                    / "tts"
                    / "tts_models--multilingual--multi-dataset--xtts_v2"
                    / "speakers_xtts.pth"
                )

                if speakers_file.exists():
                    raw = torch.load(speakers_file, map_location="cpu")
                    if isinstance(raw, dict) and raw:
                        manager = SpeakerManager()
                        manager.name_to_id = {
                            name: idx for idx, name in enumerate(raw.keys())
                        }
                        manager.embeddings = {}
                        manager.embeddings_by_names = {}
                        manager.clip_ids = []

                        for name, payload in raw.items():
                            emb = payload.get("speaker_embedding")
                            if emb is None:
                                continue
                            if hasattr(emb, "detach"):
                                emb = emb.detach().cpu().numpy()
                            if hasattr(emb, "tolist"):
                                emb = emb.tolist()
                            manager.embeddings[name] = {"name": name, "embedding": emb}
                            manager.embeddings_by_names.setdefault(name, []).append(
                                emb
                            )
                            manager.clip_ids.append(name)

                        if manager.name_to_id:
                            tts_model = self.model.synthesizer.tts_model
                            self.model.synthesizer.tts_model.speaker_manager = manager
                            # Mark config as d-vector based so Synthesizer uses speaker embeddings
                            self.model.synthesizer.tts_config.use_d_vector_file = True
                            self.model.synthesizer.tts_config.d_vector_file = str(
                                speakers_file
                            )
                            logger.info(
                                "Attached XTTS speaker_manager with %s speakers from %s",
                                len(manager.name_to_id),
                                speakers_file.name,
                            )
            except Exception as exc:
                logger.warning("Could not attach XTTS speaker metadata: %s", exc)

            # Log speaker capabilities for diagnostics
            is_multi = getattr(self.model, "is_multi_speaker", None)
            speaker_source = None
            speakers: List[str] = []
            if hasattr(self.model, "speakers") and isinstance(
                getattr(self.model, "speakers"), (list, tuple)
            ):
                speakers = list(getattr(self.model, "speakers"))
                speaker_source = "model.speakers"
            elif hasattr(self.model, "speaker_manager") and getattr(
                self.model.speaker_manager, "speakers", None
            ):
                speakers = list(self.model.speaker_manager.speakers)
                speaker_source = "model.speaker_manager.speakers"

            speaker_source_note = f" via {speaker_source}" if speaker_source else ""
            logger.info(
                "XTTS v2 model loaded successfully (multi_speaker=%s, speakers=%s%s)",
                is_multi,
                len(speakers),
                speaker_source_note,
            )
            if speakers:
                preview = speakers[:5]
                more = "" if len(speakers) <= 5 else f" (+{len(speakers)-5} more)"
                logger.info("XTTS available speakers sample: %s%s", preview, more)

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
        **kwargs,
    ) -> np.ndarray:
        """
        Synthesize speech using XTTS v2

        Args:
            text: Text to synthesize (recommended < 1000 chars for optimal quality)
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

        # Check if model actually supports multiple speakers
        speaker_supported = getattr(self.model, "is_multi_speaker", False)
        speaker_explicitly_requested = "speaker" in kwargs

        if speaker_explicitly_requested and speaker_supported:
            # Multi-speaker model: use speaker parameter (Mode 2)
            active_speaker = speaker
            logger.info(f"Using built-in XTTS speaker: {speaker}")
        else:
            # Single-speaker model OR no speaker requested: use voice cloning (Mode 1)
            active_speaker = None
            if speaker_explicitly_requested and not speaker_supported:
                logger.warning(
                    f"XTTS model is single-speaker; cannot use built-in speaker '{speaker}'. "
                    f"Using voice cloning instead."
                )

        # Fallback reference for voice cloning when no reference_audio provided
        # Fallback reference for cases where no explicit reference is provided
        fallback_reference = None
        if not reference_audio and self.default_reference.exists():
            fallback_reference = self.default_reference
            logger.info(
                f"No reference audio provided; using default: {self.default_reference.name}"
            )

        # Validate language
        if language not in self.get_supported_languages():
            logger.warning(
                f"Language {language} not in XTTS supported list, using 'en'"
            )
            language = "en"

        try:
            # Determine synthesis mode: voice cloning vs built-in voice
            ref_to_use = reference_audio or fallback_reference

            # Mode 1: Voice cloning with reference audio
            if ref_to_use and ref_to_use.exists():
                logger.info(
                    f"Using voice cloning with reference: {ref_to_use}"
                )
                wav = self.model.tts(
                    text=text,
                    speaker_wav=str(ref_to_use),
                    language=language,
                    speed=speed,
                    temperature=temperature,
                )
            # Mode 2: Built-in voice using speaker parameter
            elif active_speaker:
                speaker_wav = str(ref_to_use) if ref_to_use else None
                logger.info(
                    "Using built-in XTTS voice: %s (with reference_wav=%s)",
                    active_speaker,
                    speaker_wav if speaker_wav else "None",
                )
                wav = self.model.tts(
                    text=text,
                    speaker=active_speaker,  # Use speaker parameter for built-in voices
                    speaker_wav=speaker_wav,
                    language=language,
                    speed=speed,
                    temperature=temperature,
                )
            # Mode 3: Fallback to single-speaker model default
            else:
                if reference_audio and not ref_to_use:
                    logger.warning(
                        f"Reference audio not found: {reference_audio}, using model default"
                    )
                logger.info(
                    "XTTS model reports single-speaker; using built-in default voice"
                )
                # Single-speaker model - no speaker parameter needed
                wav = self.model.tts(
                    text=text,
                    language=language,
                    speed=speed,
                    temperature=temperature,
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
        """XTTS v2 practical text length limit for optimal quality.

        Note: XTTS v2 uses a GPT-based architecture with ~400 token context window.
        This translates to roughly 2000-2500 characters depending on language.

        We set a conservative limit of 10,000 characters to allow Phase 3's
        smart chunking system to make intelligent decisions based on research.
        XTTS will handle internal sentence splitting as needed.
        """
        return 10000  # Conservative limit - allows Phase 3 flexibility

    def supports_fine_tuning(self) -> bool:
        """XTTS supports fine-tuning for better voice adaptation"""
        return True
