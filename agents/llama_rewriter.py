"""
LlamaRewriter - rewrites text to be TTS-friendly.

Returns structured dictionaries only; all fields are safe defaults when the
LLM is unavailable. This class is opt-in and does not run unless called.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .llama_base import LlamaAgent

logger = logging.getLogger(__name__)


class LlamaRewriter(LlamaAgent):
    """Rewrite text for safer TTS synthesis (length + clarity)."""

    def rewrite_for_tts(
        self,
        text: str,
        max_chars: int = 1000,
        issues: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Rewrite text to fit within max_chars while improving TTS friendliness.

        Returns:
            dict with keys: rewritten, notes, confidence
        """
        issues = issues or []
        fallback = {
            "rewritten": text[:max_chars],
            "notes": "LLM unavailable; returned original text",
            "confidence": 0.0,
        }

        prompt = (
            "Rewrite the text for speech synthesis. Goals:\n"
            f"- Keep length <= {max_chars} characters\n"
            "- Preserve meaning and chronology\n"
            "- Remove markup/footnotes\n"
            "- Smooth out awkward phrasing for TTS\n"
            "- Keep punctuation modest to avoid choppiness\n\n"
            f"Issues observed: {', '.join(issues) if issues else 'none'}\n\n"
            "Respond with JSON: {\"rewritten\": \"...\", \"notes\": \"...\", \"confidence\": 0-1}\n\n"
            f"Text:\n{text}"
        )

        try:
            response = self.query_json(prompt, max_tokens=400, temperature=0.3)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LlamaRewriter failed: %s", exc)
            fallback["notes"] = f"{fallback['notes']} (error: {exc})"
            return fallback

        if not isinstance(response, dict) or response.get("error"):
            note = response.get("error") if isinstance(response, dict) else "LLM response invalid"
            fallback["notes"] = note
            return fallback

        rewritten = str(response.get("rewritten") or text)[:max_chars]
        notes = str(response.get("notes") or "")
        try:
            confidence = float(response.get("confidence", 0.0))
        except Exception:
            confidence = 0.0

        return {
            "rewritten": rewritten,
            "notes": notes,
            "confidence": max(0.0, min(1.0, confidence)),
        }

    def rewrite_from_asr_feedback(
        self,
        original_text: str,
        asr_transcription: str,
        asr_issues: List[str],
        wer: float,
        max_chars: int = 1000,
    ) -> Dict[str, Any]:
        """
        Rewrite text based on ASR validation feedback.

        Uses the ASR transcription to understand what the TTS engine
        actually produced, then rewrites the text to fix the issues.

        Args:
            original_text: The text that was synthesized
            asr_transcription: What Whisper heard (the actual audio)
            asr_issues: Detected issues (e.g., ["truncation", "high_wer_32%"])
            wer: Word Error Rate (0.0 - 1.0)
            max_chars: Maximum length for rewritten text

        Returns:
            dict with keys: rewritten, notes, confidence, strategy
        """
        fallback = {
            "rewritten": original_text[:max_chars],
            "notes": "LLM unavailable; returned original text",
            "confidence": 0.0,
            "strategy": "fallback"
        }

        # Build diagnostic context
        issues_desc = ", ".join(asr_issues) if asr_issues else "high WER"

        prompt = (
            "You are fixing text for TTS synthesis based on ASR validation feedback.\n\n"
            "**Original Text (what we wanted to say):**\n"
            f"{original_text}\n\n"
            "**ASR Transcription (what the TTS actually produced):**\n"
            f"{asr_transcription}\n\n"
            f"**Word Error Rate:** {wer:.1%}\n"
            f"**Issues Detected:** {issues_desc}\n\n"
            "**Your Task:**\n"
            "1. Compare the original text vs what was actually synthesized\n"
            "2. Identify what caused the TTS to fail (complex words, punctuation, length, etc.)\n"
            "3. Rewrite the text to be TTS-friendly while preserving meaning\n"
            "4. Keep length <= {max_chars} characters\n\n"
            "**Guidelines:**\n"
            "- Simplify complex words that were mispronounced\n"
            "- Break up long sentences that caused truncation\n"
            "- Remove problematic punctuation (ellipses, nested quotes, em-dashes)\n"
            "- Replace abbreviations/acronyms with full words\n"
            "- If truncation occurred, identify where and why\n\n"
            "Respond with JSON:\n"
            "{\n"
            '  "rewritten": "The fixed text...",\n'
            '  "notes": "Explanation of what you fixed and why",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "strategy": "simplify_words" | "break_sentences" | "remove_punctuation" | "expand_abbreviations"\n'
            "}\n"
        )

        try:
            response = self.query_json(prompt, max_tokens=500, temperature=0.2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LlamaRewriter ASR feedback failed: %s", exc)
            fallback["notes"] = f"{fallback['notes']} (error: {exc})"
            return fallback

        if not isinstance(response, dict) or response.get("error"):
            note = response.get("error") if isinstance(response, dict) else "LLM response invalid"
            fallback["notes"] = note
            return fallback

        rewritten = str(response.get("rewritten") or original_text)[:max_chars]
        notes = str(response.get("notes") or "")
        strategy = str(response.get("strategy") or "unknown")

        try:
            confidence = float(response.get("confidence", 0.0))
        except Exception:
            confidence = 0.0

        return {
            "rewritten": rewritten,
            "notes": notes,
            "confidence": max(0.0, min(1.0, confidence)),
            "strategy": strategy
        }
