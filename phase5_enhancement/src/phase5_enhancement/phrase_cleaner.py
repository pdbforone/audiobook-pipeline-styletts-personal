"""
Phase 5: Phrase Cleaner Module

Integrated audio phrase detection and removal for Phase 5.
Detects and removes unwanted TTS phrases before enhancement.
"""

import logging
import threading
import time
from pathlib import Path
from typing import ClassVar, Dict, List, Literal, Optional, Tuple

import numpy as np
from faster_whisper import WhisperModel
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class PhraseCleanerConfig:
    """Configuration for phrase cleaning."""

    def __init__(
        self,
        enabled: bool = True,
        target_phrases: List[str] = None,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        crossfade_ms: int = 200,
        save_transcripts: bool = False,
        cleanup_scope: Literal[
            "none", "first_n_chunks", "all", "final_only"
        ] = "all",
        cleanup_first_n: int = 3,
    ):
        self.enabled = enabled
        self.target_phrases = target_phrases or [
            "You need to add some text for me to talk",
            "You need to add some text for me to talk.",
            "You need to add text for me to talk",
            "You need to add text for me to talk.",
        ]
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.crossfade_ms = crossfade_ms
        self.save_transcripts = save_transcripts
        self.cleanup_scope = cleanup_scope
        self.cleanup_first_n = cleanup_first_n


class PhraseCleaner:
    """
    Removes unwanted TTS phrases from audio chunks.
    Integrated into Phase 5 enhancement pipeline.
    """

    _MODEL_CACHE: ClassVar[dict[tuple[str, str, str], WhisperModel]] = {}
    _CACHE_LOCK: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, config: PhraseCleanerConfig):
        """Initialize cleaner with configuration."""
        self.config = config
        self.target_phrases = [
            p.lower().strip() for p in config.target_phrases
        ]

        if config.enabled:
            logger.info(
                f"Initializing Whisper model for phrase cleaning: {config.model_size}"
            )
            self.model = self._get_or_load_model(
                config.model_size, config.device, config.compute_type
            )
        else:
            self.model = None
            logger.info("Phrase cleaning disabled")

    @classmethod
    def _get_or_load_model(
        cls, model_size: str, device: str, compute_type: str
    ) -> WhisperModel:
        """Load Whisper once and reuse it to avoid repeated GPU/CPU initialization."""
        cache_key = (model_size, device, compute_type)
        with cls._CACHE_LOCK:
            if cache_key not in cls._MODEL_CACHE:
                cls._MODEL_CACHE[cache_key] = WhisperModel(
                    model_size, device=device, compute_type=compute_type
                )
            return cls._MODEL_CACHE[cache_key]

    def _should_skip_cleanup(
        self,
        chunk_index: Optional[int],
        is_final_pass: bool,
    ) -> bool:
        """Return True when cleanup should be skipped based on configured scope."""
        scope = self.config.cleanup_scope
        if scope == "none":
            return True
        if scope == "final_only" and not is_final_pass:
            return True
        if scope == "first_n_chunks" and chunk_index is not None:
            return chunk_index > self.config.cleanup_first_n
        return False

    def clean_audio(
        self,
        audio_path: Path,
        *,
        chunk_index: Optional[int] = None,
        is_final_pass: bool = False,
    ) -> Tuple[Optional[np.ndarray], int, Dict]:
        """
        Clean audio file by removing target phrases.

        Args:
            audio_path: Path to audio file
            chunk_index: 1-based index of the chunk in the current batch (for scope control)
            is_final_pass: True when running after final concatenation

        Returns:
            Tuple of (cleaned_audio_array, sample_rate, metadata)
            If no cleaning needed, returns (None, 0, metadata)
        """
        if not self.config.enabled:
            return (
                None,
                0,
                {"status": "disabled", "scope": self.config.cleanup_scope},
            )

        if self._should_skip_cleanup(chunk_index, is_final_pass):
            return (
                None,
                0,
                {"status": "skipped", "scope": self.config.cleanup_scope},
            )

        start_time = time.perf_counter()

        try:
            # Transcribe audio
            segments = self._transcribe(audio_path)

            # Find target phrases
            matches = self._find_phrases(segments)

            if not matches:
                elapsed = time.perf_counter() - start_time
                logger.debug(
                    f"No phrases found in {audio_path.name} ({elapsed:.1f}s)"
                )
                return (
                    None,
                    0,
                    {
                        "status": "clean",
                        "processing_time": elapsed,
                        "scope": self.config.cleanup_scope,
                    },
                )

            # Remove phrases
            cleaned_audio, sr = self._remove_segments(audio_path, matches)

            elapsed = time.perf_counter() - start_time
            logger.info(
                f"Cleaned {len(matches)} phrase(s) from {audio_path.name} ({elapsed:.1f}s)"
            )

            return (
                cleaned_audio,
                sr,
                {
                    "status": "cleaned",
                    "phrases_removed": len(matches),
                    "processing_time": elapsed,
                    "matches": matches,
                    "scope": self.config.cleanup_scope,
                },
            )

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.warning(
                f"Phrase cleaning failed for {audio_path.name}: {e}"
            )
            return (
                None,
                0,
                {
                    "status": "error",
                    "error": str(e),
                    "processing_time": elapsed,
                    "scope": self.config.cleanup_scope,
                },
            )

    def _transcribe(self, audio_path: Path) -> List[Dict]:
        """Transcribe audio with word-level timestamps."""
        if not self.model:
            raise RuntimeError(
                "Phrase cleaner is disabled or model failed to load."
            )

        segments, info = self.model.transcribe(
            str(audio_path),
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            language="en",
        )

        segments_list = []
        for segment in segments:
            segments_list.append(
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                }
            )

        # Save transcript if enabled
        if self.config.save_transcripts:
            self._save_transcript(audio_path, segments_list)

        return segments_list

    def _save_transcript(self, audio_path: Path, segments: List[Dict]):
        """Save SRT transcript for debugging."""
        transcript_path = (
            audio_path.parent / f"{audio_path.stem}_transcript.srt"
        )

        def format_timestamp(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        with open(transcript_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, start=1):
                f.write(f"{i}\n")
                f.write(
                    f"{format_timestamp(segment['start'])} --> "
                    f"{format_timestamp(segment['end'])}\n"
                )
                f.write(f"{segment['text'].strip()}\n\n")

    def _find_phrases(self, segments: List[Dict]) -> List[Dict]:
        """Find target phrases in transcribed segments."""
        matches = []

        for segment in segments:
            segment_text = segment["text"].lower().strip()

            for phrase in self.target_phrases:
                if phrase in segment_text:
                    matches.append(
                        {
                            "start": segment["start"],
                            "end": segment["end"],
                            "phrase": phrase,
                            "text": segment["text"],
                        }
                    )
                    logger.debug(
                        f"Found '{phrase}' at {segment['start']:.2f}s"
                    )
                    break

        return matches

    def _remove_segments(
        self, audio_path: Path, segments_to_remove: List[Dict]
    ) -> Tuple[np.ndarray, int]:
        """Remove segments from audio and return as numpy array."""
        # Load audio with pydub
        audio = AudioSegment.from_file(str(audio_path))
        sr = audio.frame_rate

        # Sort segments by start time
        segments = sorted(segments_to_remove, key=lambda x: x["start"])

        # Build clean audio
        result = AudioSegment.empty()
        last_end_ms = 0

        for segment in segments:
            start_ms = int(segment["start"] * 1000)
            end_ms = int(segment["end"] * 1000)

            # Keep audio between segments
            if start_ms > last_end_ms:
                chunk = audio[last_end_ms:start_ms]

                if len(result) > 0 and self.config.crossfade_ms > 0:
                    result = result.append(
                        chunk, crossfade=self.config.crossfade_ms
                    )
                else:
                    result += chunk

            last_end_ms = end_ms

        # Add remaining audio
        if last_end_ms < len(audio):
            chunk = audio[last_end_ms:]
            if len(result) > 0 and self.config.crossfade_ms > 0:
                result = result.append(
                    chunk, crossfade=self.config.crossfade_ms
                )
            else:
                result += chunk

        # Convert to numpy array
        samples = np.array(result.get_array_of_samples(), dtype=np.float32)
        # Normalize to [-1, 1]
        samples = samples / (2 ** (result.sample_width * 8 - 1))

        # Convert to mono if stereo
        if result.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)

        return samples, sr
