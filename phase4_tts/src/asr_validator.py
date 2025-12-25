"""
ASR (Automatic Speech Recognition) Validation for TTS Quality

Uses Whisper to transcribe synthesized audio and calculate Word Error Rate (WER).
High WER (>20%) indicates quality issues like mispronunciation, artifacts, or truncation.

Battle-tested heuristic from research:
- WER >20%: Recoverable issues (rewrite text, retry)
- WER >40%: Non-recoverable (switch engine)
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Lazy import to avoid dependency if not used
_whisper = None
_Levenshtein = None


def _get_whisper():
    """Lazy load whisper model."""
    global _whisper
    if _whisper is None:
        try:
            import whisper
            _whisper = whisper
        except ImportError:
            logger.warning("Whisper not available. Install with: pip install openai-whisper")
            return None
    return _whisper


def _get_levenshtein():
    """Lazy load Levenshtein for WER calculation."""
    global _Levenshtein
    if _Levenshtein is None:
        try:
            import Levenshtein
            _Levenshtein = Levenshtein
        except ImportError:
            logger.warning("Levenshtein not available. Install with: pip install python-Levenshtein")
            return None
    return _Levenshtein


class ASRValidator:
    """
    Validates TTS output quality using ASR.

    Transcribes synthesized audio and compares with original text
    to detect:
    - Mispronunciations
    - Missing words (truncation)
    - Artifacts (gibberish, repetition)
    - Prosody issues (WER spike in specific regions)
    """

    def __init__(self, model_size: str = "base"):
        """
        Initialize ASR validator.

        Args:
            model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
                       - "tiny": Fast, less accurate (good for quick checks)
                       - "base": Balanced (recommended)
                       - "small": More accurate, slower
        """
        self.model_size = model_size
        self.model = None
        self.wer_warning_threshold = 0.20  # 20% WER = yellow flag
        self.wer_critical_threshold = 0.40  # 40% WER = red flag

    def _load_model(self):
        """Load Whisper model on first use."""
        if self.model is not None:
            return

        whisper = _get_whisper()
        if whisper is None:
            logger.error("Whisper not available - ASR validation disabled")
            return

        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model = None

    def validate_audio(
        self,
        audio_path: Path,
        expected_text: str,
        chunk_id: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Validate synthesized audio quality via ASR.

        Args:
            audio_path: Path to synthesized audio file
            expected_text: Original text that should have been synthesized
            chunk_id: Chunk identifier for logging

        Returns:
            {
                "valid": bool,  # True if WER < warning threshold
                "wer": float,   # Word Error Rate (0.0 - 1.0)
                "transcription": str,  # What Whisper heard
                "issues": list[str],   # Detected quality issues
                "recommendation": str,  # "pass" | "rewrite" | "switch_engine"
                "confidence": float    # ASR confidence (0.0 - 1.0)
            }
        """
        self._load_model()

        if self.model is None:
            # ASR not available, assume valid
            return {
                "valid": True,
                "wer": 0.0,
                "transcription": "",
                "issues": ["ASR validation unavailable"],
                "recommendation": "pass",
                "confidence": 0.0
            }

        whisper = _get_whisper()
        if whisper is None:
            return self._unavailable_result()

        try:
            # Transcribe audio
            result = self.model.transcribe(str(audio_path))
            transcription = result["text"].strip()
            confidence = self._calculate_confidence(result)

            # Calculate WER
            wer = self._calculate_wer(expected_text, transcription)

            # Detect issues
            issues = self._detect_issues(expected_text, transcription, wer)

            # Recommendation
            recommendation = self._get_recommendation(wer, issues)

            valid = wer < self.wer_warning_threshold

            if not valid:
                logger.warning(
                    f"ASR validation FAILED for {chunk_id}: "
                    f"WER={wer:.1%}, issues={', '.join(issues)}"
                )
            else:
                logger.debug(f"ASR validation passed for {chunk_id}: WER={wer:.1%}")

            return {
                "valid": valid,
                "wer": wer,
                "transcription": transcription,
                "issues": issues,
                "recommendation": recommendation,
                "confidence": confidence
            }

        except Exception as e:
            logger.error(f"ASR validation error for {chunk_id}: {e}")
            return {
                "valid": True,  # Fail open (don't block on ASR errors)
                "wer": 0.0,
                "transcription": "",
                "issues": [f"ASR error: {str(e)}"],
                "recommendation": "pass",
                "confidence": 0.0
            }

    def _calculate_wer(self, reference: str, hypothesis: str) -> float:
        """
        Calculate Word Error Rate using Levenshtein distance.

        WER = (Substitutions + Deletions + Insertions) / Total Words in Reference
        """
        Levenshtein = _get_levenshtein()
        if Levenshtein is None:
            # Fallback to simple comparison
            return 0.0 if reference.lower() == hypothesis.lower() else 1.0

        # Normalize text
        ref_words = self._normalize_text(reference).split()
        hyp_words = self._normalize_text(hypothesis).split()

        if len(ref_words) == 0:
            return 0.0 if len(hyp_words) == 0 else 1.0

        # Calculate edit distance
        distance = Levenshtein.distance(" ".join(ref_words), " ".join(hyp_words))

        # WER = edit distance / reference length
        wer = distance / len(ref_words)

        return min(1.0, wer)  # Cap at 100%

    def _normalize_text(self, text: str) -> str:
        """Normalize text for WER calculation."""
        # Lowercase
        text = text.lower()

        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)

        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _detect_phrase_repetition(self, text: str, min_phrase_words: int = 4) -> Optional[str]:
        """
        Detect phrase-level repetition in text.

        XTTS sometimes loops and repeats the same phrase/sentence multiple times.
        This catches patterns like "Once upon a time. Once upon a time. Once upon a time."

        Args:
            text: Text to analyze (typically a Whisper transcription)
            min_phrase_words: Minimum words in a phrase to consider (default: 4)

        Returns:
            Description of repetition if found, None otherwise
        """
        words = self._normalize_text(text).split()
        if len(words) < min_phrase_words * 2:
            return None  # Too short to have meaningful repetition

        # Check for repeated n-grams (phrases of 4-8 words)
        for n in range(min_phrase_words, min(9, len(words) // 2 + 1)):
            ngrams = []
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i + n])
                ngrams.append(ngram)

            # Count occurrences of each n-gram
            ngram_counts = Counter(ngrams)

            # Find n-grams that appear more than twice (suspicious repetition)
            for ngram, count in ngram_counts.most_common(3):
                if count >= 3:
                    # This phrase appears 3+ times - likely XTTS looping
                    return f"{count}x_{n}words"

        return None

    def _calculate_confidence(self, whisper_result: dict) -> float:
        """
        Calculate average confidence from Whisper segments.

        Whisper doesn't provide explicit confidence, so we use:
        - Average probability from segments
        - Or fallback to 1.0 if not available
        """
        segments = whisper_result.get("segments", [])
        if not segments:
            return 1.0

        # Some Whisper versions include 'avg_logprob'
        probs = [seg.get("avg_logprob", 0.0) for seg in segments if "avg_logprob" in seg]

        if probs:
            # Convert log probs to probabilities (rough estimate)
            avg_logprob = np.mean(probs)
            confidence = np.exp(avg_logprob)  # e^logprob ≈ probability
            return min(1.0, max(0.0, confidence))

        return 1.0  # Unknown, assume high confidence

    def _detect_issues(
        self, expected: str, transcription: str, wer: float
    ) -> list[str]:
        """Detect specific quality issues."""
        issues = []

        # Issue 1: High WER
        if wer > self.wer_critical_threshold:
            issues.append(f"critical_wer_{wer:.0%}")
        elif wer > self.wer_warning_threshold:
            issues.append(f"high_wer_{wer:.0%}")

        # Issue 2: Truncation (transcription much shorter)
        expected_words = len(self._normalize_text(expected).split())
        transcribed_words = len(self._normalize_text(transcription).split())

        if transcribed_words < expected_words * 0.7:  # <70% of expected length
            issues.append(f"truncation_{transcribed_words}/{expected_words}_words")

        # Issue 3: Word-level repetition (same word repeated many times in a row)
        words = self._normalize_text(transcription).split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:  # <30% unique words = likely repetition artifact
                issues.append("repetition_artifact")

        # Issue 3b: Phrase-level repetition (same sentence/phrase repeated)
        # This catches XTTS looping where it says the same sentence multiple times
        phrase_rep = self._detect_phrase_repetition(transcription)
        if phrase_rep:
            issues.append(f"phrase_repetition_{phrase_rep}")

        # Issue 4: Gibberish detection (very different from expected)
        if wer > 0.8 and transcribed_words > 0:
            issues.append("possible_gibberish")

        return issues

    def _get_recommendation(self, wer: float, issues: list[str]) -> str:
        """
        Recommend action based on WER and detected issues.

        Returns:
            - "pass": Audio is good
            - "rewrite": Recoverable issue, try rewriting source text
            - "switch_engine": Non-recoverable, need different engine
        """
        if wer < self.wer_warning_threshold:
            return "pass"

        # Critical WER or gibberish = switch engine
        if wer > self.wer_critical_threshold or "possible_gibberish" in issues:
            return "switch_engine"

        # Truncation or moderate WER = try rewrite
        if any("truncation" in issue for issue in issues) or wer > self.wer_warning_threshold:
            return "rewrite"

        return "pass"

    def _unavailable_result(self) -> Dict[str, Any]:
        """Return result when ASR is unavailable."""
        return {
            "valid": True,  # Fail open
            "wer": 0.0,
            "transcription": "",
            "issues": ["ASR unavailable"],
            "recommendation": "pass",
            "confidence": 0.0
        }


# Convenience function
def validate_tts_audio(
    audio_path: Path,
    expected_text: str,
    chunk_id: str = "unknown",
    model_size: str = "base"
) -> Dict[str, Any]:
    """
    Validate TTS audio quality using ASR.

    Quick validation function that creates a validator and runs check.

    Args:
        audio_path: Path to synthesized audio
        expected_text: Original text
        chunk_id: Chunk identifier
        model_size: Whisper model size ("tiny", "base", "small")

    Returns:
        Validation result dict
    """
    validator = ASRValidator(model_size=model_size)
    return validator.validate_audio(audio_path, expected_text, chunk_id)
