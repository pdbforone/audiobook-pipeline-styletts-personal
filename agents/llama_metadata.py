"""
LlamaMetadataGenerator - structured metadata agent for audiobooks.

Produces summaries, tags, and timestamps as dictionaries only.
Opt-in; safe fallbacks return low-confidence defaults when LLM is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .llama_base import LlamaAgent

logger = logging.getLogger(__name__)


class LlamaMetadataGenerator(LlamaAgent):
    """Generate structured metadata for audiobook content."""

    def _run_prompt(
        self,
        prompt: str,
        fallback: Dict[str, Any],
        *,
        max_tokens: int = 400,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        """Execute a JSON prompt with safe fallbacks."""
        defaults = dict(fallback)
        try:
            response = self.query_json(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:  # noqa: BLE001
            defaults["notes"] = f"LLM unavailable: {exc}"
            return defaults

        if not isinstance(response, dict) or response.get("error"):
            defaults["notes"] = (
                response.get("error", "LLM response invalid")
                if isinstance(response, dict)
                else "LLM response invalid"
            )
            return defaults

        merged = {**defaults, **response}
        try:
            merged["confidence"] = max(0.0, min(1.0, float(merged.get("confidence", 0.0))))
        except Exception:
            merged["confidence"] = 0.0
        return merged

    def generate_short_summary(self, text: str, max_words: int = 50) -> Dict[str, Any]:
        prompt = (
            f"Summarize the following text in under {max_words} words.\n"
            "Return JSON with keys: summary, notes, confidence (0-1)."
            f"\n\nText:\n{text}"
        )
        fallback = {"summary": "", "notes": "LLM unavailable", "confidence": 0.0}
        return self._run_prompt(prompt, fallback, max_tokens=200, temperature=0.35)

    def generate_long_summary(self, text: str, max_words: int = 200) -> Dict[str, Any]:
        prompt = (
            f"Create a longer summary (<= {max_words} words) capturing key themes.\n"
            "Return JSON: {\"summary\": \"...\", \"notes\": \"...\", \"confidence\": 0-1}.\n\n"
            f"Text:\n{text}"
        )
        fallback = {"summary": "", "notes": "LLM unavailable", "confidence": 0.0}
        return self._run_prompt(prompt, fallback, max_tokens=400, temperature=0.45)

    def generate_chapter_summary(
        self,
        chapter_title: str,
        text: str,
        max_words: int = 120,
    ) -> Dict[str, Any]:
        prompt = (
            f"Summarize chapter '{chapter_title}' in <= {max_words} words.\n"
            "Return JSON with keys summary, highlights (list), notes, confidence (0-1).\n\n"
            f"Text:\n{text}"
        )
        fallback = {
            "summary": "",
            "highlights": [],
            "notes": "LLM unavailable",
            "confidence": 0.0,
        }
        return self._run_prompt(prompt, fallback, max_tokens=350, temperature=0.4)

    def generate_youtube_metadata(
        self,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        prompt = (
            "Produce concise YouTube metadata for an audiobook excerpt.\n"
            "Return JSON with keys: title, description, tags (list), notes, confidence (0-1).\n\n"
            f"Base title: {title}\n"
            f"Description:\n{description}\n"
            f"Existing tags: {', '.join(tags or [])}"
        )
        fallback = {
            "title": title,
            "description": description,
            "tags": tags or [],
            "notes": "LLM unavailable",
            "confidence": 0.0,
        }
        return self._run_prompt(prompt, fallback, max_tokens=300, temperature=0.35)

    def generate_tags(self, text: str, max_tags: int = 10) -> Dict[str, Any]:
        prompt = (
            f"Extract up to {max_tags} descriptive tags from the text.\n"
            "Return JSON: {\"tags\": [\"...\"], \"notes\": \"...\", \"confidence\": 0-1}.\n\n"
            f"Text:\n{text}"
        )
        fallback = {"tags": [], "notes": "LLM unavailable", "confidence": 0.0}
        return self._run_prompt(prompt, fallback, max_tokens=200, temperature=0.25)

    def generate_timestamps(
        self,
        text: str,
        chunk_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        prompt = (
            "Create rough timestamps for narration segments.\n"
            f"Assume average segment length of ~{chunk_seconds:.0f}s.\n"
            "Return JSON: {\"timestamps\": [{\"label\": \"...\", \"start\": float, \"end\": float}],"
            " \"notes\": \"...\", \"confidence\": 0-1}.\n\n"
            f"Text:\n{text}"
        )
        fallback = {
            "timestamps": [],
            "notes": "LLM unavailable",
            "confidence": 0.0,
        }
        return self._run_prompt(prompt, fallback, max_tokens=300, temperature=0.3)
