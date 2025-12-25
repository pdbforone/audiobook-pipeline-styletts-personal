"""
LlamaSemanticRepetition - Semantic-level repetition detection.

Goes beyond simple n-gram matching to detect:
- Semantically similar phrases (paraphrased repetition)
- Thematic loops (same idea expressed differently)
- Intentional vs accidental repetition
- XTTS-style looping patterns

Complements the pattern-based detection in asr_validator.py with
deeper semantic understanding.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .llama_base import LlamaAgent

logger = logging.getLogger(__name__)


class LlamaSemanticRepetition(LlamaAgent):
    """
    Semantic repetition detector using LLM analysis.

    Identifies repetition that simple pattern matching misses:
    - "The king was angry" / "The monarch felt rage" (semantic similarity)
    - Sentence-level loops where TTS repeated with slight variations
    - Distinguishes intentional literary repetition from errors
    """

    def detect_repetition(
        self,
        text: str,
        context: Optional[str] = None,
        is_transcription: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze text for semantic repetition.

        Args:
            text: Text to analyze (chunk text or ASR transcription)
            context: Optional context (book title, genre) for better analysis
            is_transcription: True if text is ASR output (more likely to have TTS errors)

        Returns:
            dict with keys:
                - has_repetition: bool
                - repetition_type: "none" | "semantic" | "exact" | "tts_loop"
                - severity: "none" | "low" | "medium" | "high"
                - instances: List of detected repetitions
                - is_intentional: bool (literary device vs error)
                - confidence: float
                - recommendation: str
        """
        fallback = {
            "has_repetition": False,
            "repetition_type": "none",
            "severity": "none",
            "instances": [],
            "is_intentional": False,
            "confidence": 0.0,
            "recommendation": "No action needed",
        }

        # Quick pre-check with pattern matching
        quick_result = self._quick_pattern_check(text)
        if quick_result["severity"] == "none" and not is_transcription:
            # No obvious repetition, skip LLM for speed
            return fallback

        # Truncate for prompt
        text_preview = text[:1500] if len(text) > 1500 else text

        source_type = "ASR transcription (TTS output)" if is_transcription else "source text"
        context_info = f"\nContext: {context}" if context else ""

        prompt = (
            f"Analyze this {source_type} for repetition issues.{context_info}\n\n"
            f"**Text ({len(text)} chars):**\n{text_preview}\n\n"
            "**Analyze for:**\n"
            "1. **Exact repetition**: Same words/phrases repeated\n"
            "2. **Semantic repetition**: Same meaning expressed differently\n"
            "3. **TTS loop patterns**: Characteristic of text-to-speech errors:\n"
            "   - Phrases repeated 3+ times in sequence\n"
            "   - Slight variations of same sentence back-to-back\n"
            "   - Trailing off into repeated fragments\n"
            "4. **Intentional repetition**: Literary devices (anaphora, emphasis)\n\n"
            "**Important distinctions:**\n"
            "- Intentional: 'I have a dream... I have a dream...' (rhetorical)\n"
            "- TTS error: 'The man walked walked walked the street street'\n"
            "- Semantic loop: 'He was angry. The man felt rage. His fury grew.'\n\n"
            "Respond with JSON:\n"
            "{\n"
            '  "has_repetition": true/false,\n'
            '  "repetition_type": "none" | "exact" | "semantic" | "tts_loop",\n'
            '  "severity": "none" | "low" | "medium" | "high",\n'
            '  "instances": [\n'
            '    {"text": "repeated phrase", "count": N, "type": "exact|semantic|loop"}\n'
            "  ],\n"
            '  "is_intentional": true/false,\n'
            '  "confidence": 0.0-1.0,\n'
            '  "recommendation": "what to do"\n'
            "}"
        )

        try:
            response = self.query_json(prompt, max_tokens=400, temperature=0.2)
        except Exception as exc:
            logger.warning("LlamaSemanticRepetition query failed: %s", exc)
            # Return quick check results if LLM fails
            fallback.update(quick_result)
            return fallback

        if not isinstance(response, dict) or response.get("error"):
            fallback.update(quick_result)
            return fallback

        return {
            "has_repetition": response.get("has_repetition", False),
            "repetition_type": response.get("repetition_type", "none"),
            "severity": response.get("severity", "none"),
            "instances": response.get("instances", []),
            "is_intentional": response.get("is_intentional", False),
            "confidence": float(response.get("confidence", 0.0)),
            "recommendation": response.get("recommendation", ""),
            "quick_check": quick_result,
        }

    def _quick_pattern_check(self, text: str) -> Dict[str, Any]:
        """
        Fast pattern-based repetition check (no LLM).

        Returns basic repetition indicators for pre-filtering.
        """
        result = {
            "severity": "none",
            "exact_repeats": [],
            "word_repeats": [],
            "ngram_repeats": [],
        }

        words = text.lower().split()
        if len(words) < 10:
            return result

        # Check for immediate word repetition (word word)
        for i in range(len(words) - 1):
            if words[i] == words[i + 1] and len(words[i]) > 2:
                result["word_repeats"].append(words[i])

        # Check for n-gram repetition (3-6 word phrases)
        for n in range(3, 7):
            if len(words) < n * 2:
                continue
            ngrams = [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]
            counts = Counter(ngrams)
            for ngram, count in counts.most_common(5):
                if count >= 3:
                    result["ngram_repeats"].append({"phrase": ngram, "count": count})

        # Check for sentence-level repetition
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 20]
        sentence_counts = Counter(sentences)
        for sent, count in sentence_counts.most_common(3):
            if count >= 2:
                result["exact_repeats"].append({"sentence": sent[:50], "count": count})

        # Determine severity
        if result["ngram_repeats"] and any(r["count"] >= 5 for r in result["ngram_repeats"]):
            result["severity"] = "high"
        elif result["ngram_repeats"] or result["exact_repeats"]:
            result["severity"] = "medium"
        elif len(result["word_repeats"]) > 3:
            result["severity"] = "low"

        return result

    def compare_source_and_transcription(
        self,
        source_text: str,
        transcription: str,
    ) -> Dict[str, Any]:
        """
        Compare source text with ASR transcription to detect TTS-induced repetition.

        This catches cases where the TTS engine introduced repetition that
        wasn't in the original text.

        Args:
            source_text: Original text sent to TTS
            transcription: What Whisper heard from the audio

        Returns:
            dict with analysis of introduced repetition
        """
        fallback = {
            "tts_introduced_repetition": False,
            "repetition_in_source": False,
            "repetition_in_transcription": False,
            "likely_tts_error": False,
            "details": [],
            "confidence": 0.0,
        }

        # Quick check both texts
        source_check = self._quick_pattern_check(source_text)
        trans_check = self._quick_pattern_check(transcription)

        # If transcription has more repetition than source, likely TTS error
        source_severity = {"none": 0, "low": 1, "medium": 2, "high": 3}
        source_score = source_severity.get(source_check["severity"], 0)
        trans_score = source_severity.get(trans_check["severity"], 0)

        if trans_score > source_score:
            fallback["tts_introduced_repetition"] = True
            fallback["likely_tts_error"] = True
            fallback["confidence"] = 0.8

        fallback["repetition_in_source"] = source_score > 0
        fallback["repetition_in_transcription"] = trans_score > 0

        # If significant difference, use LLM for deeper analysis
        if trans_score >= 2 and trans_score > source_score:
            try:
                prompt = (
                    "Compare these two texts to determine if TTS introduced repetition.\n\n"
                    f"**Original text sent to TTS:**\n{source_text[:800]}\n\n"
                    f"**ASR transcription of audio:**\n{transcription[:800]}\n\n"
                    "**Analyze:**\n"
                    "1. Does the transcription have repetition not in the source?\n"
                    "2. Is this likely a TTS looping error?\n"
                    "3. What specific phrases were repeated?\n\n"
                    "Respond with JSON:\n"
                    "{\n"
                    '  "tts_introduced_repetition": true/false,\n'
                    '  "likely_tts_error": true/false,\n'
                    '  "repeated_phrases": ["phrase1", "phrase2"],\n'
                    '  "confidence": 0.0-1.0,\n'
                    '  "diagnosis": "brief explanation"\n'
                    "}"
                )

                response = self.query_json(prompt, max_tokens=300, temperature=0.2)

                if isinstance(response, dict) and not response.get("error"):
                    fallback["tts_introduced_repetition"] = response.get("tts_introduced_repetition", False)
                    fallback["likely_tts_error"] = response.get("likely_tts_error", False)
                    fallback["details"] = response.get("repeated_phrases", [])
                    fallback["confidence"] = float(response.get("confidence", 0.0))
                    fallback["diagnosis"] = response.get("diagnosis", "")

            except Exception as exc:
                logger.warning("Comparison analysis failed: %s", exc)

        return fallback

    def quick_check(self, text: str) -> Tuple[bool, str]:
        """
        Fast check without LLM for batch processing.

        Returns:
            Tuple of (has_significant_repetition, severity)
        """
        result = self._quick_pattern_check(text)
        has_repetition = result["severity"] in ("medium", "high")
        return has_repetition, result["severity"]
