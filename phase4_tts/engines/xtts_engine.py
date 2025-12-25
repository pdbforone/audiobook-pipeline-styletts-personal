"""
XTTS v2 Engine Wrapper
Mature, production-tested TTS with excellent voice cloning

Enhanced with segment-level synthesis to prevent repetition/hallucination
issues that occur when XTTS processes text exceeding its ~400 token limit.
"""

import gc
import logging
import random
import re
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from . import TTSEngine

logger = logging.getLogger(__name__)

# XTTS v2 safe synthesis limits
# The model warns at 250 chars/sentence and fails at 400 tokens (~1600 chars)
# We use conservative limits to prevent internal splitting (which causes repetition)
XTTS_SAFE_SEGMENT_CHARS = 220  # Stay well under 250 char warning
XTTS_MAX_SEGMENT_CHARS = 280   # Absolute max before we force split
XTTS_SEGMENT_SILENCE_MS = 80   # Silence between segments (ms)

# Post-Coqui Era optimized parameters (from community research Dec 2024)
# The "underscore trick" prevents end-of-sentence hallucinations
XTTS_USE_UNDERSCORE_TRICK = True

# Optimized repetition/length penalties for audiobook synthesis
# Research: rep_penalty 2.0-5.0 with length_penalty > 1.0 is the sweet spot
# Too high (10.0) causes terse output; too low causes loops
XTTS_REPETITION_PENALTY = 3.5   # Was 10.0 - more natural prosody
XTTS_LENGTH_PENALTY = 1.2       # Was 1.0 - encourages natural sequence length

# Deterministic synthesis seed (set to None for non-deterministic)
XTTS_SYNTHESIS_SEED = 42

# Memory cleanup interval (chunks between gc.collect calls)
XTTS_MEMORY_CLEANUP_INTERVAL = 50


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
        # Built-in speaker latents loaded from speakers_xtts.pth
        # Contains {speaker_name: {'gpt_cond_latent': tensor, 'speaker_embedding': tensor}}
        self.builtin_speakers_data = None
        # Counter for memory cleanup interval
        self._synthesis_counter = 0

    def _set_deterministic_seed(self, seed: int = XTTS_SYNTHESIS_SEED) -> None:
        """
        Set random seeds for deterministic synthesis.

        Post-Coqui Era Fix: XTTS is non-deterministic by default. Without seed
        management, the same text may produce different pronunciations each time
        (e.g., "Cave" → "Cavave" on retry). This is disastrous for audiobook editing.

        Must be called before EVERY inference call for consistent results.
        """
        if seed is None:
            return  # Skip if non-deterministic mode desired

        random.seed(seed)
        np.random.seed(seed)
        if TORCH_AVAILABLE:
            import torch
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)

    def _cleanup_synthesis_memory(self, force: bool = False) -> None:
        """
        Prevent VRAM/RAM creep during long audiobook generation.

        Post-Coqui Era Fix: CUDA context corruption and memory leaks are common
        in long-running XTTS synthesis. Explicit garbage collection and cache
        clearing prevents crashes in 10+ hour audiobook runs.

        Args:
            force: If True, cleanup immediately. Otherwise, only cleanup every
                   XTTS_MEMORY_CLEANUP_INTERVAL chunks.
        """
        self._synthesis_counter += 1

        if not force and self._synthesis_counter % XTTS_MEMORY_CLEANUP_INTERVAL != 0:
            return

        gc.collect()
        if TORCH_AVAILABLE:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.debug(
                    f"XTTS memory cleanup after {self._synthesis_counter} segments"
                )

    def _apply_underscore_trick(self, text: str) -> str:
        """
        Apply the 'underscore trick' to prevent end-of-sentence hallucinations.

        Post-Coqui Era Fix: The GPT-2 backbone fails to predict EOS token correctly,
        causing gibberish/breathing at sentence end. Appending '_' biases the
        attention mechanism toward a 'silence' or 'stop' state.

        Research source: Coqui TTS community discussions, Dec 2024.
        """
        if not XTTS_USE_UNDERSCORE_TRICK:
            return text

        text = text.rstrip()
        if not text.endswith('_'):
            text = text + '_'
        return text

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

    def _split_text_for_safe_synthesis(
        self, text: str, max_chars: int = XTTS_SAFE_SEGMENT_CHARS
    ) -> List[str]:
        """
        Split text into XTTS-safe segments to prevent repetition/hallucination.

        XTTS v2 has known issues when processing text that exceeds its internal
        limits (~250 chars per sentence, ~400 tokens total). When this happens,
        XTTS does its own internal splitting which often causes:
        - Repeated phrases or sentences
        - Audio hallucination/looping
        - Truncated output

        This method pre-splits text at natural boundaries BEFORE sending to XTTS,
        giving us control over segment boundaries and preventing these issues.

        Args:
            text: Text to split
            max_chars: Maximum characters per segment (default: 220)

        Returns:
            List of text segments, each safe for XTTS synthesis
        """
        text = text.strip()
        if not text:
            return []

        # If text is already short enough, return as-is
        if len(text) <= max_chars:
            return [text]

        segments = []

        # Step 1: Split into sentences first
        # Match sentence endings: . ! ? followed by space or end
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]

        current_segment = ""

        for sentence in sentences:
            # FIRST: Check if the sentence itself is too long and needs splitting
            # This must happen BEFORE we try to add it to current_segment
            if len(sentence) > max_chars:
                # Save any accumulated segment first
                if current_segment.strip():
                    segments.append(current_segment.strip())
                    current_segment = ""

                # Split the long sentence into sub-segments
                sub_segments = self._split_long_sentence(sentence, max_chars)
                if sub_segments:
                    # Add all but the last as complete segments
                    segments.extend(sub_segments[:-1])
                    # Keep the last one as the start of next segment
                    current_segment = sub_segments[-1]
                continue

            # If adding this sentence would exceed limit
            if current_segment and len(current_segment) + len(sentence) + 1 > max_chars:
                # Save current segment and start fresh
                segments.append(current_segment.strip())
                current_segment = sentence
            else:
                # Add sentence to current segment
                if current_segment:
                    current_segment += " " + sentence
                else:
                    current_segment = sentence

        # Don't forget the last segment
        if current_segment.strip():
            segments.append(current_segment.strip())

        # SAFETY CHECK: Ensure ALL segments are under the limit
        # If any are still too long, force-split them at word boundaries
        final_segments = []
        for seg in segments:
            if len(seg) <= XTTS_MAX_SEGMENT_CHARS:
                final_segments.append(seg)
            else:
                # Force split at word boundary - this shouldn't happen but safety first
                logger.warning(
                    f"Segment still too long ({len(seg)} chars), force-splitting: '{seg[:50]}...'"
                )
                words = seg.split()
                current = ""
                for word in words:
                    if current and len(current) + len(word) + 1 > max_chars:
                        final_segments.append(current.strip())
                        current = word
                    else:
                        current = f"{current} {word}".strip() if current else word
                if current.strip():
                    final_segments.append(current.strip())

        # Log what we did
        if len(final_segments) > 1:
            oversized = [len(s) for s in final_segments if len(s) > XTTS_SAFE_SEGMENT_CHARS]
            if oversized:
                logger.warning(
                    f"Pre-split text into {len(final_segments)} segments but {len(oversized)} "
                    f"exceed soft limit ({XTTS_SAFE_SEGMENT_CHARS}): {oversized}"
                )
            logger.info(
                f"Pre-split text into {len(final_segments)} segments for safe XTTS synthesis "
                f"(original: {len(text)} chars, segments: {[len(s) for s in final_segments]})"
            )

        return final_segments

    def _split_long_sentence(self, sentence: str, max_chars: int) -> List[str]:
        """
        Split a single long sentence at clause boundaries.

        Tries these split points in order of preference:
        1. Semicolons (strongest boundary in classical texts)
        2. Colons
        3. Em-dashes
        4. Conjunctions (and, but, or, yet, for, nor, so)
        5. Relative pronouns (which, that, who, whom, whose)
        6. Subordinating conjunctions (because, although, while, etc.)
        7. Commas (weakest, last resort)

        Args:
            sentence: Long sentence to split
            max_chars: Maximum characters per segment

        Returns:
            List of sentence segments
        """
        if len(sentence) <= max_chars:
            return [sentence]

        segments = []
        remaining = sentence

        # Priority-ordered split patterns
        # Each pattern includes the delimiter handling
        split_patterns = [
            # Semicolons - keep with preceding text
            (r';(?:\s+)', ';'),
            # Colons - keep with preceding text
            (r':(?:\s+)', ':'),
            # Em-dashes (both styles)
            (r'\s*[—–]\s*', ' —'),
            (r'\s+--\s+', ' —'),
            # Coordinating conjunctions - split before, keep conjunction with following
            (r'\s+(?=(?:and|but|or|yet|for|nor|so)\s+)', ''),
            # Relative pronouns - split before
            (r'\s+(?=(?:which|that|who|whom|whose)\s+)', ''),
            # Subordinating conjunctions - split before
            (r'\s+(?=(?:because|although|though|while|since|when|where|whereas|unless|if)\s+)', ''),
            # Commas - weakest boundary, keep with preceding
            (r',(?:\s+)', ','),
        ]

        while len(remaining) > max_chars:
            best_split = None
            best_pos = 0

            # Try each pattern to find the best split point
            for pattern, delimiter_suffix in split_patterns:
                matches = list(re.finditer(pattern, remaining, re.IGNORECASE))

                for match in matches:
                    # Calculate position after the delimiter
                    split_pos = match.end()

                    # We want to split where the first part is as close to max_chars as possible
                    # but not exceeding it
                    if split_pos <= max_chars and split_pos > best_pos:
                        # Check that we'd have meaningful content on both sides
                        before = remaining[:match.start()].strip()
                        if len(before) >= 20:  # Minimum segment length
                            best_split = (match.start(), match.end(), delimiter_suffix)
                            best_pos = split_pos

            if best_split:
                start, end, suffix = best_split
                segment = remaining[:start].strip()
                if suffix and not segment.endswith(suffix.strip()):
                    segment += suffix.strip()
                segments.append(segment)
                remaining = remaining[end:].strip()
            else:
                # No good split point found - force split at word boundary near max_chars
                # Find the last space before max_chars
                space_pos = remaining.rfind(' ', 0, max_chars)
                if space_pos > 20:
                    segments.append(remaining[:space_pos].strip())
                    remaining = remaining[space_pos:].strip()
                else:
                    # Give up and take what we have (very long word or no spaces)
                    segments.append(remaining[:max_chars].strip())
                    remaining = remaining[max_chars:].strip()

        # Add the remaining text
        if remaining.strip():
            segments.append(remaining.strip())

        return segments

    def _concatenate_audio_segments(
        self, segments: List[np.ndarray], silence_ms: int = XTTS_SEGMENT_SILENCE_MS
    ) -> np.ndarray:
        """
        Concatenate audio segments with brief silence gaps.

        Args:
            segments: List of audio arrays (float32, mono)
            silence_ms: Milliseconds of silence between segments

        Returns:
            Concatenated audio array
        """
        if not segments:
            return np.array([], dtype=np.float32)

        if len(segments) == 1:
            return segments[0]

        # Create silence buffer
        silence_samples = int(self.sample_rate_val * silence_ms / 1000)
        silence = np.zeros(silence_samples, dtype=np.float32)

        # Concatenate with silence between segments
        result_parts = []
        for i, segment in enumerate(segments):
            result_parts.append(segment)
            if i < len(segments) - 1:
                result_parts.append(silence)

        return np.concatenate(result_parts)

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

            # Load built-in speaker latents from speakers_xtts.pth
            # These contain pre-computed gpt_cond_latent + speaker_embedding for each speaker
            try:
                import torch
                import platform

                # Find speakers_xtts.pth in the TTS cache directory
                if platform.system() == "Windows":
                    tts_cache = Path.home() / "AppData" / "Local" / "tts"
                else:
                    tts_cache = Path.home() / ".local" / "share" / "tts"

                speakers_file = (
                    tts_cache
                    / "tts_models--multilingual--multi-dataset--xtts_v2"
                    / "speakers_xtts.pth"
                )

                if speakers_file.exists():
                    raw = torch.load(speakers_file, map_location="cpu")
                    if isinstance(raw, dict) and raw:
                        # Store the full speaker data for use in inference
                        # Each entry has: {'gpt_cond_latent': tensor, 'speaker_embedding': tensor}
                        self.builtin_speakers_data = raw
                        logger.info(
                            "Loaded %d built-in speaker latents from %s",
                            len(raw),
                            speakers_file.name,
                        )
                else:
                    logger.warning(
                        "speakers_xtts.pth not found at %s - built-in speakers will not work",
                        speakers_file,
                    )
            except Exception as exc:
                logger.warning("Could not load XTTS speaker latents: %s", exc)

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
        Synthesize speech using XTTS v2 with automatic segment splitting.

        This method automatically splits long text into XTTS-safe segments
        to prevent the repetition/hallucination issues that occur when XTTS
        tries to process text exceeding its ~400 token internal limit.

        Args:
            text: Text to synthesize (any length - will be auto-split if needed)
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

        # Check if we have built-in speaker latents loaded
        # This is more reliable than checking model.is_multi_speaker
        speaker_supported = self.builtin_speakers_data is not None
        speaker_explicitly_requested = "speaker" in kwargs

        if speaker_explicitly_requested and speaker_supported:
            # Use built-in speaker with pre-computed latents
            active_speaker = speaker
            logger.info(f"Using built-in XTTS speaker: {speaker}")
        else:
            # No built-in speakers available OR no speaker requested: use voice cloning
            active_speaker = None
            if speaker_explicitly_requested and not speaker_supported:
                logger.warning(
                    f"Built-in speaker latents not loaded; cannot use speaker '{speaker}'. "
                    f"Using voice cloning instead."
                )

        # Fallback reference for voice cloning when no reference_audio provided
        # Only needed if NOT using a built-in speaker
        fallback_reference = None
        if not active_speaker and not reference_audio and self.default_reference.exists():
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

        # Determine synthesis mode
        ref_to_use = reference_audio or fallback_reference

        # Split text into safe segments BEFORE sending to XTTS
        # This prevents XTTS's buggy internal splitting from causing repetition
        segments = self._split_text_for_safe_synthesis(text)

        if not segments:
            logger.warning("No text segments to synthesize")
            return np.array([], dtype=np.float32)

        # Synthesize each segment individually
        audio_segments = []
        total_expected_dur = 0.0
        total_actual_dur = 0.0

        for i, segment_text in enumerate(segments):
            try:
                # Post-Coqui Era Fix: Apply the underscore trick for EOS handling
                # This is more effective than period→comma replacement
                synthesis_text = self._apply_underscore_trick(segment_text)

                # Set deterministic seed before each inference for consistent pronunciation
                self._set_deterministic_seed()

                # Estimate expected duration (~15 chars/second for speech)
                expected_dur = len(synthesis_text) / 15.0
                total_expected_dur += expected_dur

                if len(segments) > 1:
                    logger.debug(
                        f"Synthesizing segment {i+1}/{len(segments)}: "
                        f"{len(synthesis_text)} chars, expected ~{expected_dur:.1f}s"
                    )

                wav = self._synthesize_single_segment(
                    synthesis_text,
                    ref_to_use=ref_to_use,
                    active_speaker=active_speaker,
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

                # Calculate actual duration and check for anomalies
                actual_dur = len(audio) / self.sample_rate_val
                total_actual_dur += actual_dur

                # Warn if duration is suspiciously long (>2x expected) or short (<0.3x)
                ratio = actual_dur / expected_dur if expected_dur > 0 else 0
                if ratio > 2.0:
                    logger.warning(
                        f"Segment {i+1}/{len(segments)} SUSPICIOUSLY LONG: "
                        f"{actual_dur:.1f}s vs expected {expected_dur:.1f}s (ratio {ratio:.1f}x) - "
                        f"possible duplication. Text: '{segment_text[:50]}...'"
                    )
                elif ratio < 0.3:
                    logger.warning(
                        f"Segment {i+1}/{len(segments)} SUSPICIOUSLY SHORT: "
                        f"{actual_dur:.1f}s vs expected {expected_dur:.1f}s (ratio {ratio:.1f}x) - "
                        f"possible truncation. Text: '{segment_text[:50]}...'"
                    )
                elif len(segments) > 1:
                    logger.debug(
                        f"Segment {i+1}/{len(segments)} OK: {actual_dur:.1f}s (ratio {ratio:.1f}x)"
                    )

                audio_segments.append(audio)

                # Post-Coqui Era Fix: Periodic memory cleanup to prevent VRAM creep
                self._cleanup_synthesis_memory()

            except Exception as e:
                logger.error(
                    f"XTTS synthesis failed for segment {i+1}/{len(segments)}: {e}"
                )
                # Re-raise - let caller handle the failure
                raise

        # Log total duration summary
        if len(segments) > 1:
            total_ratio = total_actual_dur / total_expected_dur if total_expected_dur > 0 else 0
            logger.info(
                f"XTTS synthesis complete: {len(segments)} segments, "
                f"total {total_actual_dur:.1f}s (expected ~{total_expected_dur:.1f}s, ratio {total_ratio:.1f}x)"
            )
            if total_ratio > 1.8:
                logger.warning(
                    f"Total audio duration is {total_ratio:.1f}x expected - possible duplication issue!"
                )

        # Concatenate all segments with brief silence gaps
        combined_audio = self._concatenate_audio_segments(audio_segments)

        # Final normalization
        if len(combined_audio) > 0 and np.max(np.abs(combined_audio)) > 0:
            combined_audio = combined_audio / np.max(np.abs(combined_audio)) * 0.95

        return combined_audio

    def _synthesize_single_segment(
        self,
        text: str,
        ref_to_use: Optional[Path],
        active_speaker: Optional[str],
        language: str,
        speed: float,
        temperature: float,
    ) -> np.ndarray:
        """
        Synthesize a single text segment (internal method).

        This method handles the actual XTTS API call for a single segment
        that is known to be within safe limits.

        CRITICAL: All synthesis calls use split_sentences=False (for model.tts())
        or enable_text_splitting=False (for tts_model.inference()) to prevent
        XTTS from doing its own internal sentence splitting. Our external
        splitting via _split_text_for_safe_synthesis() already handles this,
        and double-splitting causes audio truncation and duplication issues.

        Args:
            text: Text segment to synthesize (should be < 250 chars)
            ref_to_use: Reference audio path for voice cloning
            active_speaker: Built-in speaker name (if using multi-speaker mode)
            language: Language code
            speed: Speech speed multiplier
            temperature: Generation temperature

        Returns:
            Raw audio array from XTTS
        """
        # Mode 1: Built-in voice using pre-computed latents (PRIORITY)
        # The high-level model.tts() API doesn't work with built-in speakers
        # (it always requires speaker_wav). We must use the low-level
        # tts_model.inference() API directly with pre-computed latents.
        if active_speaker and self.builtin_speakers_data:
            if active_speaker not in self.builtin_speakers_data:
                available = list(self.builtin_speakers_data.keys())[:5]
                raise ValueError(
                    f"Speaker '{active_speaker}' not found in built-in speakers. "
                    f"Available: {available}... ({len(self.builtin_speakers_data)} total)"
                )

            speaker_dict = self.builtin_speakers_data[active_speaker]
            gpt_cond_latent = speaker_dict["gpt_cond_latent"]
            speaker_embedding = speaker_dict["speaker_embedding"]

            # Call the low-level inference API directly
            tts_model = self.model.synthesizer.tts_model

            # HuggingFace generation kwargs to prevent phrase repetition
            # no_repeat_ngram_size=4 blocks any 4-word sequence from repeating
            hf_kwargs = {"no_repeat_ngram_size": 4}

            try:
                result = tts_model.inference(
                    text=text,
                    language=language,
                    gpt_cond_latent=gpt_cond_latent,
                    speaker_embedding=speaker_embedding,
                    temperature=temperature,
                    speed=speed,
                    # Post-Coqui Era optimized penalties (research Dec 2024)
                    # Sweet spot: 2.0-5.0 rep_penalty with length_penalty > 1.0
                    repetition_penalty=XTTS_REPETITION_PENALTY,
                    length_penalty=XTTS_LENGTH_PENALTY,
                    top_k=50,
                    top_p=0.85,
                    enable_text_splitting=False,  # We already split externally - CRITICAL
                    # Pass to HuggingFace generate() to block phrase looping
                    **hf_kwargs,
                )
            except TypeError:
                # Fallback if XTTS version doesn't support extra kwargs
                logger.debug("XTTS inference doesn't accept hf_generate_kwargs, using defaults")
                result = tts_model.inference(
                    text=text,
                    language=language,
                    gpt_cond_latent=gpt_cond_latent,
                    speaker_embedding=speaker_embedding,
                    temperature=temperature,
                    speed=speed,
                    repetition_penalty=XTTS_REPETITION_PENALTY,
                    length_penalty=XTTS_LENGTH_PENALTY,
                    top_k=50,
                    top_p=0.85,
                    enable_text_splitting=False,
                )

            # Result is a dict with 'wav' key
            if isinstance(result, dict) and "wav" in result:
                wav = result["wav"]
                # Convert torch tensor to numpy if needed
                if hasattr(wav, "cpu"):
                    wav = wav.cpu().numpy()
                return wav
            return result

        # Mode 2: Voice cloning with reference audio
        if ref_to_use and ref_to_use.exists():
            return self.model.tts(
                text=text,
                speaker_wav=str(ref_to_use),
                language=language,
                speed=speed,
                temperature=temperature,
                split_sentences=False,  # We already split externally - prevent double splitting
            )

        # Mode 3: Fallback - try default reference if available
        if self.default_reference.exists():
            logger.warning(
                "No active_speaker or reference audio - using default reference"
            )
            return self.model.tts(
                text=text,
                speaker_wav=str(self.default_reference),
                language=language,
                speed=speed,
                temperature=temperature,
                split_sentences=False,  # We already split externally - prevent double splitting
            )

        # Mode 4: Last resort - this will likely fail but let XTTS try
        raise RuntimeError(
            "XTTS synthesis requires either a built-in speaker name or "
            "a reference audio file for voice cloning. Neither was provided."
        )

    def get_max_text_length(self) -> Optional[int]:
        """XTTS v2 maximum text length (with internal segment handling).

        Note: XTTS v2 uses a GPT-based architecture with ~400 token context window.
        Raw XTTS would struggle with text > ~1600 chars, causing repetition/hallucination.

        However, this engine now includes automatic segment splitting that:
        - Pre-splits text at sentence/clause boundaries before synthesis
        - Synthesizes each segment individually (< 220 chars each)
        - Concatenates segments with appropriate silence gaps

        This allows accepting much longer text while preventing XTTS's
        internal splitting bugs from causing audio repetition.

        We still set a reasonable limit to prevent memory issues with
        very long chunks, but Phase 3 can safely create larger chunks now.
        """
        return 10000  # Safe with internal segment splitting

    def supports_fine_tuning(self) -> bool:
        """XTTS supports fine-tuning for better voice adaptation"""
        return True

    def get_builtin_speakers(self) -> List[str]:
        """Get list of available built-in speaker names.

        Returns:
            List of speaker names that can be used with the 'speaker' parameter.
            Empty list if built-in speakers are not available.
        """
        if self.builtin_speakers_data:
            return list(self.builtin_speakers_data.keys())
        return []
