"""
Phase 4 Audio Validation Module

Implements two-tier validation strategy:
- Tier 1: Fast checks (every chunk, ~2s each)
- Tier 2: Whisper validation (selective sampling, ~60s each)

Purpose: Detect TTS corruption immediately rather than discovering it days later in Phase 5
"""

import logging
import re
import time
import random
from collections import Counter
from typing import Any, Tuple, Dict, Optional, List
import librosa
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-TTS Text Quality Checks
# ---------------------------------------------------------------------------


@dataclass
class TextQualityResult:
    """Result of pre-TTS text quality checks."""

    is_valid: bool
    issue_type: Optional[str]  # "sentence_duplication", "word_repetition", etc.
    details: Dict[str, Any]
    deduped_text: Optional[str]  # Cleaned text if deduplication was possible


def detect_text_repetition(
    text: str,
    min_sentence_len: int = 20,
    similarity_threshold: float = 0.95,
) -> TextQualityResult:
    """
    Detect sentence-level duplication in chunk text BEFORE TTS synthesis.

    This catches Phase 3 chunking bugs where sentences are duplicated within
    a chunk, causing XTTS to produce shorter audio than expected (it skips
    or truncates repeated content), leading to duration_mismatch validation
    failures.

    Detection strategy:
    1. Split text into sentences
    2. Compare each sentence to all others using normalized matching
    3. Flag if any sentence appears more than once

    Args:
        text: Chunk text to analyze
        min_sentence_len: Minimum sentence length to consider (avoids false positives on short phrases)
        similarity_threshold: How similar sentences must be to count as duplicates (0.0-1.0)

    Returns:
        TextQualityResult with duplication details and optionally deduped text
    """
    if not text or len(text.strip()) < min_sentence_len:
        return TextQualityResult(
            is_valid=True,
            issue_type=None,
            details={"reason": "text_too_short"},
            deduped_text=None,
        )

    # Split into sentences using multiple delimiters
    # This is intentionally simple to avoid heavy NLP dependencies in Phase 4
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    raw_sentences = re.split(sentence_pattern, text.strip())

    # Normalize and filter sentences
    sentences = []
    for s in raw_sentences:
        s = s.strip()
        if len(s) >= min_sentence_len:
            sentences.append(s)

    if len(sentences) < 2:
        return TextQualityResult(
            is_valid=True,
            issue_type=None,
            details={"sentence_count": len(sentences)},
            deduped_text=None,
        )

    # Check for exact and near-exact duplicates
    def normalize_for_comparison(s: str) -> str:
        """Normalize sentence for comparison (lowercase, collapse whitespace, remove punctuation)."""
        s = s.lower()
        s = re.sub(r'\s+', ' ', s)
        s = re.sub(r'[^\w\s]', '', s)
        return s.strip()

    normalized = [normalize_for_comparison(s) for s in sentences]

    # Find duplicates
    duplicates = []
    seen = {}
    for i, norm in enumerate(normalized):
        if norm in seen:
            duplicates.append({
                "original_idx": seen[norm],
                "duplicate_idx": i,
                "text_preview": sentences[i][:80] + ("..." if len(sentences[i]) > 80 else ""),
            })
        else:
            seen[norm] = i

    if duplicates:
        # Calculate duplication severity
        unique_count = len(seen)
        total_count = len(sentences)
        duplication_ratio = 1 - (unique_count / total_count)

        # Create deduped text by keeping only first occurrence of each sentence
        deduped_sentences = []
        seen_normalized = set()
        for s, norm in zip(sentences, normalized):
            if norm not in seen_normalized:
                deduped_sentences.append(s)
                seen_normalized.add(norm)

        deduped_text = " ".join(deduped_sentences)

        logger.warning(
            "Text duplication detected: %d duplicates in %d sentences (%.1f%% redundant)",
            len(duplicates),
            total_count,
            duplication_ratio * 100,
        )

        return TextQualityResult(
            is_valid=False,
            issue_type="sentence_duplication",
            details={
                "duplicate_count": len(duplicates),
                "total_sentences": total_count,
                "unique_sentences": unique_count,
                "duplication_ratio": duplication_ratio,
                "duplicates": duplicates[:5],  # Limit to first 5 for logging
            },
            deduped_text=deduped_text,
        )

    # Check for word-level repetition (e.g., "the the the")
    words = text.lower().split()
    if len(words) >= 3:
        consecutive_repeats = 0
        max_consecutive = 0
        for i in range(1, len(words)):
            if words[i] == words[i - 1] and len(words[i]) > 2:
                consecutive_repeats += 1
                max_consecutive = max(max_consecutive, consecutive_repeats)
            else:
                consecutive_repeats = 0

        if max_consecutive >= 2:  # Same word 3+ times in a row
            logger.warning(
                "Word repetition detected: %d consecutive repeats",
                max_consecutive + 1,
            )
            return TextQualityResult(
                is_valid=False,
                issue_type="word_repetition",
                details={
                    "max_consecutive_repeats": max_consecutive + 1,
                },
                deduped_text=None,  # Word repetition is harder to auto-fix
            )

    return TextQualityResult(
        is_valid=True,
        issue_type=None,
        details={"sentence_count": len(sentences)},
        deduped_text=None,
    )


# Try to import Whisper (optional for Tier 2)
WHISPER_AVAILABLE = False
try:
    import whisper

    WHISPER_AVAILABLE = True
    logger.info("✅ Whisper available for Tier 2 validation")
except ImportError:
    logger.warning("⚠️  Whisper not installed - Tier 2 validation disabled")


@dataclass
class ValidationConfig:
    """Configuration for validation checks."""

    # Tier 1: Quick checks (always enabled)
    enable_tier1: bool = True
    duration_tolerance_sec: float = 120.0  # Allow ±120s difference (handles title pages, indexes, etc.)
    silence_threshold_sec: float = 2.0  # Flag gaps >2s
    min_amplitude_db: float = -40.0  # Flag audio quieter than -40dB
    min_chars_for_duration_check: int = (
        400  # Skip duration validation for very short chunks
    )

    # Tier 2: Whisper validation (selective)
    enable_tier2: bool = True
    whisper_model: str = "base"  # base, small, medium, large
    whisper_sample_rate: float = 0.05  # 5% random sample
    whisper_first_n: int = 10  # Always validate first 10 chunks
    whisper_last_n: int = 10  # Always validate last 10 chunks
    max_wer: float = 0.10  # Max Word Error Rate (10%)
    chars_per_minute: int = 1050  # Shared speaking rate assumption

    # Known error phrases to detect
    error_phrases: list = None

    # Pre-synthesis validation (proactive)
    enable_llama_pre_validator: bool = True  # Scan text before TTS
    pre_validator_auto_expand: bool = True   # Auto-expand abbreviations
    pre_validator_use_llm: bool = False      # Use LLM for complex rewrites

    # ASR-driven rewriting (reactive)
    enable_llama_asr_rewrite: bool = True    # Use LlamaRewriter for ASR issues

    def __post_init__(self):
        if self.error_phrases is None:
            self.error_phrases = [
                "you need to add some text for me to talk",
                "i need text to speak",
                "please provide text",
                "add text for me",
                "need some text",
            ]


@dataclass
class ValidationResult:
    """Result of validation checks."""

    is_valid: bool
    tier: int  # 1 or 2
    reason: (
        str  # e.g., "duration_mismatch", "error_phrase_detected", "high_wer"
    )
    details: Dict  # Additional metrics
    duration_sec: float  # Time taken for validation


# Lazy-load Whisper model
_whisper_model = None


def get_whisper_model(model_name: str = "base"):
    """Lazy-load Whisper model for Tier 2 validation."""
    global _whisper_model
    if _whisper_model is None and WHISPER_AVAILABLE:
        logger.info(f"Loading Whisper model: {model_name}")
        _whisper_model = whisper.load_model(model_name)
        logger.info(f"✅ Whisper {model_name} loaded")
    return _whisper_model


def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds."""
    try:
        y, sr = librosa.load(audio_path, sr=None)
        return len(y) / sr
    except Exception as e:
        logger.error(f"Failed to get audio duration: {e}")
        return 0.0


def predict_expected_duration(
    text: str, chars_per_minute: int = 1050
) -> float:
    """
    Predict expected speech duration from text.

    Args:
        text: Input text
        chars_per_minute: Average speaking rate (characters per minute)

    Returns:
        Expected duration in seconds
    """
    if not text:
        return 0.0
    if chars_per_minute <= 0:
        return 0.0

    char_count = len(text)
    duration_minutes = char_count / chars_per_minute
    duration_seconds = duration_minutes * 60

    return duration_seconds


def deduplicate_sentences(text: str) -> Tuple[str, int]:
    """
    Remove duplicate sentences from text.

    When Phase 3 chunking creates duplicates (e.g., same sentence appears 2x),
    this function removes the duplicates while preserving order.

    Args:
        text: Input text with potential duplicate sentences

    Returns:
        Tuple of (cleaned_text, number_of_duplicates_removed)
    """
    # Split into sentences, preserving the delimiter
    sentence_pattern = r'([.!?]+\s*)'
    parts = re.split(sentence_pattern, text)

    # Reconstruct sentences with their delimiters
    sentences = []
    i = 0
    while i < len(parts):
        sentence = parts[i].strip()
        delimiter = parts[i + 1] if i + 1 < len(parts) else ""
        if sentence:
            sentences.append((sentence, delimiter))
        i += 2

    # Track seen sentences (normalized for comparison)
    seen = set()
    unique_sentences = []
    duplicates_removed = 0

    for sentence, delimiter in sentences:
        # Normalize for comparison (lowercase, collapse whitespace)
        normalized = re.sub(r'\s+', ' ', sentence.lower().strip())

        if normalized not in seen:
            seen.add(normalized)
            unique_sentences.append(sentence + delimiter)
        else:
            duplicates_removed += 1

    cleaned_text = "".join(unique_sentences).strip()
    return cleaned_text, duplicates_removed


def normalize_spaced_abbreviations(text: str) -> str:
    """
    Normalize spaced abbreviations back to compact form.

    Converts "I E P" -> "IEP", "R E E D" -> "REED", etc.
    These spaced forms cause XTTS to pronounce each letter slowly.

    Args:
        text: Input text with potential spaced abbreviations

    Returns:
        Text with normalized abbreviations
    """
    # Common education/special-ed abbreviations
    known_abbrevs = {
        "I E P": "IEP",
        "A R D": "ARD",
        "R E E D": "REED",
        "B I P": "BIP",
        "F B A": "FBA",
        "L R E": "LRE",
        "F A P E": "FAPE",
        "I D E A": "IDEA",
        "S L D": "SLD",
        "O H I": "OHI",
        "E S Y": "ESY",
        "P W N": "PWN",
        "N O D": "NOD",
    }

    result = text
    for spaced, compact in known_abbrevs.items():
        result = result.replace(spaced, compact)

    # Generic pattern: single uppercase letters separated by spaces (3+ letters)
    # "A B C D" -> "ABCD"
    def compact_spaced(match):
        letters = match.group().replace(" ", "")
        # Only compact if it looks like an abbreviation (all caps)
        if letters.isupper() and len(letters) >= 3:
            return letters
        return match.group()

    # Pattern: 3+ single uppercase letters separated by single spaces
    result = re.sub(r'\b([A-Z] ){2,}[A-Z]\b', compact_spaced, result)

    return result


def has_silence_gap(
    audio_path: str,
    threshold_sec: float = 2.0,
    silence_threshold_db: float = -40.0,
) -> Tuple[bool, float]:
    """
    Check for long silence gaps in audio.

    Args:
        audio_path: Path to audio file
        threshold_sec: Flag gaps longer than this (default 2s)
        silence_threshold_db: dB threshold for silence (default -40dB)

    Returns:
        (has_gap: bool, max_gap_duration: float)
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)

        # Convert to dB
        amplitude = librosa.amplitude_to_db(np.abs(y), ref=np.max)

        # Find silent regions
        silent_frames = amplitude < silence_threshold_db

        # Find contiguous silent regions
        silent_regions = []
        in_silence = False
        silence_start = 0

        for i, is_silent in enumerate(silent_frames):
            if is_silent and not in_silence:
                # Start of silence
                silence_start = i
                in_silence = True
            elif not is_silent and in_silence:
                # End of silence
                silence_duration = (i - silence_start) / sr
                silent_regions.append(silence_duration)
                in_silence = False

        # Handle silence at end
        if in_silence:
            silence_duration = (len(silent_frames) - silence_start) / sr
            silent_regions.append(silence_duration)

        if not silent_regions:
            return False, 0.0

        max_gap = max(silent_regions)
        has_gap = max_gap > threshold_sec

        return has_gap, max_gap

    except Exception as e:
        logger.error(f"Failed to check silence gaps: {e}")
        return False, 0.0


def is_too_quiet(
    audio_path: str, threshold_db: float = -40.0
) -> Tuple[bool, float]:
    """
    Check if audio is too quiet (possible TTS failure).

    Args:
        audio_path: Path to audio file
        threshold_db: Minimum acceptable amplitude in dB

    Returns:
        (too_quiet: bool, mean_amplitude_db: float)
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)

        # Calculate mean amplitude in dB
        amplitude = librosa.amplitude_to_db(np.abs(y), ref=np.max)
        mean_db = np.mean(amplitude)

        too_quiet = mean_db < threshold_db

        return too_quiet, mean_db

    except Exception as e:
        logger.error(f"Failed to check amplitude: {e}")
        return False, 0.0


def has_error_phrase_pattern(
    audio_path: str, error_phrases: list
) -> Tuple[bool, Optional[str]]:
    """
    Check for known error phrases in audio using simple pattern detection.

    Note: This is a heuristic check using audio features, not transcription.
    For accurate phrase detection, use Tier 2 Whisper validation.

    Args:
        audio_path: Path to audio file
        error_phrases: List of known error phrases

    Returns:
        (suspected: bool, reason: str or None)
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)
        duration = len(y) / sr

        # Heuristic: Error phrases are typically 3-8 seconds long
        # If audio is suspiciously short for the expected content, flag it
        if duration < 3.0:
            return True, "audio_too_short"

        # Check for unnatural pauses (silence → speech → silence pattern)
        # This pattern often occurs when TTS says error phrase mid-sentence
        amplitude = librosa.amplitude_to_db(np.abs(y), ref=np.max)
        silent_frames = amplitude < -40.0

        # Count transitions (silence → speech)
        transitions = 0
        for i in range(1, len(silent_frames)):
            if not silent_frames[i] and silent_frames[i - 1]:
                transitions += 1

        # Multiple transitions in short audio = suspicious
        if duration < 30.0 and transitions > 3:
            return True, "unnatural_pauses"

        return False, None

    except Exception as e:
        logger.error(f"Failed to check error phrase pattern: {e}")
        return False, None


def tier1_validate(
    chunk_text: str,
    audio_path: str,
    config: ValidationConfig,
    chars_per_minute: Optional[int] = None,
) -> ValidationResult:
    """
    Tier 1: Fast validation checks (duration, silence, amplitude).

    Runs on EVERY chunk. Takes ~2-3 seconds.

    Args:
        chunk_text: Original text input to TTS
        audio_path: Path to generated audio
        config: Validation configuration

    Returns:
        ValidationResult with pass/fail and details
    """
    start = time.perf_counter()

    # 1. Duration sanity check (skip for very short chunks)
    text_length = len(chunk_text or "")
    effective_cpm = (
        chars_per_minute
        if chars_per_minute and chars_per_minute > 0
        else config.chars_per_minute
    )
    actual_duration = get_audio_duration(audio_path)
    if text_length < config.min_chars_for_duration_check:
        elapsed = time.perf_counter() - start
        return ValidationResult(
            is_valid=True,
            tier=1,
            reason="short_chunk_skip",
            details={
                "actual_duration": float(actual_duration),
                "text_length": text_length,
                "threshold": config.min_chars_for_duration_check,
            },
            duration_sec=elapsed,
        )
    expected_duration = actual_duration
    if text_length >= config.min_chars_for_duration_check:
        expected_duration = predict_expected_duration(
            chunk_text, chars_per_minute=effective_cpm
        )
        duration_diff = abs(expected_duration - actual_duration)

        # Proportional tolerance: allow more variance for longer chunks
        # - Short chunks (<20s): up to 80% variance (current behavior)
        # - Medium chunks (20-60s): up to 25% variance
        # - Long chunks (60s+): up to 20% variance
        # Always at least config.duration_tolerance_sec (default 120s)
        if expected_duration < 20.0:
            proportional_tolerance = expected_duration * 0.8
        elif expected_duration < 60.0:
            proportional_tolerance = expected_duration * 0.25
        else:
            proportional_tolerance = expected_duration * 0.20

        allowed_diff = max(config.duration_tolerance_sec, proportional_tolerance)

        if duration_diff > allowed_diff:
            elapsed = time.perf_counter() - start
            return ValidationResult(
                is_valid=False,
                tier=1,
                reason="duration_mismatch",
                details={
                    "expected_duration": float(expected_duration),
                    "actual_duration": float(actual_duration),
                    "difference": float(duration_diff),
                    "allowed_tolerance": float(allowed_diff),
                },
                duration_sec=elapsed,
            )

    # 2. Silence gap check
    has_gap, max_gap = has_silence_gap(
        audio_path, config.silence_threshold_sec
    )

    if has_gap:
        elapsed = time.perf_counter() - start
        return ValidationResult(
            is_valid=False,
            tier=1,
            reason="silence_gap",
            details={
                "max_gap_duration": float(max_gap),
                "threshold": float(config.silence_threshold_sec),
            },
            duration_sec=elapsed,
        )

    # 3. Amplitude check
    too_quiet, mean_db = is_too_quiet(audio_path, config.min_amplitude_db)

    if too_quiet:
        elapsed = time.perf_counter() - start
        return ValidationResult(
            is_valid=False,
            tier=1,
            reason="too_quiet",
            details={
                "mean_amplitude_db": float(mean_db),
                "threshold_db": float(config.min_amplitude_db),
            },
            duration_sec=elapsed,
        )

    # 4. Error phrase pattern check (heuristic)
    suspected, pattern_reason = has_error_phrase_pattern(
        audio_path, config.error_phrases
    )

    if suspected:
        elapsed = time.perf_counter() - start
        return ValidationResult(
            is_valid=False,
            tier=1,
            reason=f"error_phrase_suspected_{pattern_reason}",
            details={
                "pattern": pattern_reason,
            },
            duration_sec=elapsed,
        )

    # All checks passed
    elapsed = time.perf_counter() - start
    return ValidationResult(
        is_valid=True,
        tier=1,
        reason="valid",
        details={
            "expected_duration": float(expected_duration),
            "actual_duration": float(actual_duration),
            "max_silence_gap": float(max_gap),
            "mean_amplitude_db": float(mean_db),
        },
        duration_sec=elapsed,
    )


def calculate_word_error_rate(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER) between reference and hypothesis.

    WER = (Substitutions + Insertions + Deletions) / Total Words

    Args:
        reference: Original text (ground truth)
        hypothesis: Transcribed text from Whisper

    Returns:
        WER as a float (0.0 = perfect, 1.0 = completely wrong)
    """
    # Normalize texts
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()

    # Use dynamic programming to calculate edit distance
    m, n = len(ref_words), len(hyp_words)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],  # Deletion
                    dp[i][j - 1],  # Insertion
                    dp[i - 1][j - 1],  # Substitution
                )

    # WER = edit distance / reference length
    if m == 0:
        return 0.0 if n == 0 else 1.0

    wer = dp[m][n] / m
    return wer


def tier2_validate(
    chunk_text: str, audio_path: str, config: ValidationConfig
) -> ValidationResult:
    """
    Tier 2: Whisper validation (transcribe and compare).

    Runs on SAMPLED chunks only. Takes ~30-60 seconds on CPU.

    Args:
        chunk_text: Original text input to TTS
        audio_path: Path to generated audio
        config: Validation configuration

    Returns:
        ValidationResult with WER and transcription details
    """
    if not WHISPER_AVAILABLE:
        logger.warning("Whisper not available, skipping Tier 2 validation")
        return ValidationResult(
            is_valid=True,
            tier=2,
            reason="whisper_unavailable",
            details={},
            duration_sec=0.0,
        )

    start = time.perf_counter()

    try:
        # Load Whisper model
        model = get_whisper_model(config.whisper_model)

        # Transcribe audio
        logger.info(
            f"Transcribing audio with Whisper {config.whisper_model}..."
        )
        result = model.transcribe(audio_path)
        transcription = result["text"]

        # Calculate WER
        wer = calculate_word_error_rate(chunk_text, transcription)

        elapsed = time.perf_counter() - start

        # Check for known error phrases in transcription
        detected_phrase = None
        for phrase in config.error_phrases:
            if phrase.lower() in transcription.lower():
                detected_phrase = phrase
                break

        if detected_phrase:
            return ValidationResult(
                is_valid=False,
                tier=2,
                reason="error_phrase_detected",
                details={
                    "wer": float(wer),
                    "transcription": transcription,
                    "detected_phrase": detected_phrase,
                    "reference_text": chunk_text[:200],
                },
                duration_sec=elapsed,
            )

        if wer > config.max_wer:
            return ValidationResult(
                is_valid=False,
                tier=2,
                reason="high_wer",
                details={
                    "wer": float(wer),
                    "transcription": transcription,
                    "reference_text": chunk_text[:200],
                    "max_allowed_wer": float(config.max_wer),
                },
                duration_sec=elapsed,
            )

        # Passed
        return ValidationResult(
            is_valid=True,
            tier=2,
            reason="valid",
            details={
                "wer": float(wer),
                "transcription_length": len(transcription),
            },
            duration_sec=elapsed,
        )

    except Exception as e:
        elapsed = time.perf_counter() - start
        logger.error(f"Tier 2 validation failed: {e}")
        return ValidationResult(
            is_valid=False,
            tier=2,
            reason="validation_error",
            details={
                "error": str(e),
            },
            duration_sec=elapsed,
        )


def should_run_tier2_validation(
    chunk_idx: int, total_chunks: int, config: ValidationConfig
) -> bool:
    """
    Determine if Tier 2 (Whisper) validation should run for this chunk.

    Strategy:
    - First N chunks: Always validate
    - Last N chunks: Always validate
    - Middle chunks: Random sample based on sample_rate

    Args:
        chunk_idx: Current chunk index (0-based)
        total_chunks: Total number of chunks
        config: Validation configuration

    Returns:
        True if Tier 2 validation should run
    """
    if not config.enable_tier2 or not WHISPER_AVAILABLE:
        return False

    # First N chunks
    if chunk_idx < config.whisper_first_n:
        return True

    # Last N chunks
    if chunk_idx >= total_chunks - config.whisper_last_n:
        return True

    # Random sample
    if random.random() < config.whisper_sample_rate:
        return True

    return False


def validate_audio_chunk(
    chunk_text: str,
    audio_path: str,
    chunk_idx: int,
    total_chunks: int,
    config: ValidationConfig,
) -> Tuple[ValidationResult, Optional[ValidationResult]]:
    """
    Run validation checks on generated audio chunk.

    Returns both Tier 1 (always) and Tier 2 (if sampled) results.

    Args:
        chunk_text: Original text input to TTS
        audio_path: Path to generated audio
        chunk_idx: Current chunk index (0-based)
        total_chunks: Total number of chunks
        config: Validation configuration

    Returns:
        (tier1_result, tier2_result or None)
    """
    # Tier 1: Always run
    tier1_result = tier1_validate(
        chunk_text,
        audio_path,
        config,
        chars_per_minute=config.chars_per_minute,
    )

    logger.info(
        f"Tier 1 validation: {'✅ PASS' if tier1_result.is_valid else '❌ FAIL'} "
        f"({tier1_result.reason}) in {tier1_result.duration_sec:.2f}s"
    )

    # Tier 2: Selective
    tier2_result = None
    if should_run_tier2_validation(chunk_idx, total_chunks, config):
        logger.info(
            f"Running Tier 2 validation (chunk {chunk_idx+1}/{total_chunks})..."
        )
        tier2_result = tier2_validate(chunk_text, audio_path, config)

        logger.info(
            f"Tier 2 validation: {'✅ PASS' if tier2_result.is_valid else '❌ FAIL'} "
            f"({tier2_result.reason}) in {tier2_result.duration_sec:.2f}s"
        )

    return tier1_result, tier2_result
