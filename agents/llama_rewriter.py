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
