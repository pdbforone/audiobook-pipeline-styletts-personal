"""
Text cleaner for TTS preprocessing using NVIDIA NeMo Text Processing.

Provides a NeMo-backed cleaner when available, with a regex fallback otherwise.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Dict, Match, Optional

try:
    from nemo_text_processing.text_normalization.normalize import Normalizer

    NEMO_AVAILABLE = True
except ImportError:
    Normalizer = None  # type: ignore
    NEMO_AVAILABLE = False

try:
    from num2words import num2words

    NUM2WORDS_AVAILABLE = True
except ImportError:
    NUM2WORDS_AVAILABLE = False

logger = logging.getLogger(__name__)


class TTSTextCleaner:
    """
    Production-grade text cleaner for TTS preprocessing.
    Uses NVIDIA NeMo Text Normalization when available.
    """

    def __init__(self, language: str = "en", use_context: bool = False) -> None:
        """
        Initialize the text cleaner.

        Args:
            language: Language code (default: "en" for English)
            use_context: If True, uses context-aware normalization (slower but more accurate)
                        If False, uses fast deterministic normalization
        """
        self.language = language
        self.use_context = use_context
        self.normalizer: Optional[Normalizer] = None

        if NEMO_AVAILABLE and Normalizer:
            self.normalizer = Normalizer(
                input_case="cased",
                lang=language,
                cache_dir=None,
                overwrite_cache=False,
            )
            logger.info("✓ NeMo Text Normalizer initialized")
        else:
            logger.warning("NeMo Text Processing not installed. Using regex cleaner.")

    def clean_for_tts(self, raw_text: str) -> str:
        """
        Clean and normalize text for TTS.

        This is the main entry point. It:
        1. Fixes encoding artifacts
        2. Removes OCR noise (stray characters)
        3. Normalizes with NeMo TN (if available)
        4. Falls back to basic regex cleaning (if NeMo unavailable)
        """
        text = self._fix_encoding(raw_text)
        text = self._remove_ocr_artifacts(text)

        if self.normalizer:
            text = self._normalize_with_nemo(text)
        else:
            text = self._basic_normalization(text)

        text = self._normalize_whitespace(text)
        return text.strip()

    def _fix_encoding(self, text: str) -> str:
        """Fix common PDF encoding artifacts."""
        text = text.replace("â€œ", '"').replace("â€", '"')
        text = text.replace("â€™", "'").replace("â€˜", "'")
        text = text.replace("â€\"", "—").replace("â€\"", "–")

        try:
            from unidecode import unidecode

            text = unidecode(text)
        except ImportError:
            pass

        return text

    def _remove_ocr_artifacts(self, text: str) -> str:
        """Remove OCR noise like single letters on their own lines."""
        text = re.sub(r"^\s*[a-zA-Z]\s*$", "", text, flags=re.MULTILINE)

        def collapse_single_letters(match: Match[str]) -> str:
            parts = match.group(0).split()
            return " ".join([p for p in parts if len(p) > 1]) or ""

        text = re.sub(r"\b[a-zA-Z]\b(?:\s+\b[a-zA-Z]\b){2,}", collapse_single_letters, text)
        return text

    def _normalize_with_nemo(self, text: str) -> str:
        """Normalize text using NeMo Text Processing."""
        if not self.normalizer:
            return text

        try:
            sentences = re.split(r"([.!?]+\s+)", text)
            normalized_sentences = []

            for sentence in sentences:
                if sentence.strip():
                    normalized = self.normalizer.normalize(
                        sentence,
                        verbose=False,
                        punct_post_process=True,
                    )
                    normalized_sentences.append(normalized)

            return "".join(normalized_sentences)

        except Exception as exc:  # pragma: no cover - depends on NeMo runtime
            logger.warning(f"NeMo normalization failed: {exc}; falling back to basic normalization.")
            return self._basic_normalization(text)

    def _basic_normalization(self, text: str) -> str:
        """
        Fallback normalization using regex (if NeMo unavailable).

        This is a BASIC fallback and doesn't handle complex cases.
        Install NeMo Text Processing for proper TTS normalization.
        """

        def normalize_currency(match: Match[str]) -> str:
            amount_str = match.group(1).replace(" ", "")
            try:
                if NUM2WORDS_AVAILABLE:
                    amount = float(amount_str)
                    return num2words(amount, to="currency", currency="USD")
            except ValueError:
                return match.group(0)
            return match.group(0)

        text = re.sub(r"\$\s*(\d+\.\d{2})", normalize_currency, text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace (collapse multiple spaces, preserve paragraphs)."""
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n\n+", "\n\n", text)
        text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
        # Fix spaced characters (e.g., "T h e G i f t" → "The Gift")
        # Matches 2+ single letters separated by spaces (PDF header/title artifact)
        text = re.sub(r"\b[a-zA-Z]\b(?:\s+\b[a-zA-Z]\b)+", lambda m: m.group(0).replace(" ", ""), text)
        return text

    def clean_text_file(self, input_path: Path, output_path: Path) -> Dict[str, float]:
        """
        Clean a text file and return metrics.

        Args:
            input_path: Path to raw extracted text
            output_path: Path to save cleaned text
        """
        start_time = time.perf_counter()
        raw_text = input_path.read_text(encoding="utf-8")
        cleaned_text = self.clean_for_tts(raw_text)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(cleaned_text, encoding="utf-8")

        duration = time.perf_counter() - start_time
        return {
            "cleaning_duration": duration,
            "original_chars": len(raw_text),
            "cleaned_chars": len(cleaned_text),
            "reduction_percent": 100 * (1 - len(cleaned_text) / len(raw_text)) if raw_text else 0.0,
            "normalizer": "NeMo" if self.normalizer else "Fallback",
        }


def clean_for_tts(raw_text: str, language: str = "en") -> str:
    """Quick convenience function for cleaning text."""
    cleaner = TTSTextCleaner(language=language)
    return cleaner.clean_for_tts(raw_text)


__all__ = ["TTSTextCleaner", "clean_for_tts"]
