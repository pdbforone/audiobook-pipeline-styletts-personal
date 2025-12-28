"""
AudiobookDirector - A high-level agent for creating a unified creative plan for an audiobook.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .llama_base import LlamaAgent
from .llama_pronunciation_assistant import LlamaPronunciationAssistant
from .llama_voice_matcher import LlamaVoiceMatcher

logger = logging.getLogger(__name__)


class AudiobookDirector(LlamaAgent):
    """
    Analyzes a book's text to create a "Production Bible", guiding the entire audiobook creation process.
    """

    def __init__(self, book_text: str, **kwargs):
        super().__init__(**kwargs)
        # Use a smaller, faster model for the director if available
        self.model = kwargs.get("director_model", "llama3.1:8b-instruct-q4_K_M")
        self.book_text = book_text
        # Truncate for analysis to avoid excessive token usage
        self.analysis_text = self._get_analysis_text(book_text)
        self.pronunciation_assistant = LlamaPronunciationAssistant(**kwargs)
        self.voice_matcher = LlamaVoiceMatcher(**kwargs)

    def _get_analysis_text(self, text: str, max_chars: int = 40000) -> str:
        """Returns a representative sample of the text for analysis."""
        if len(text) <= max_chars:
            return text

        # Get the beginning, middle, and end
        start = text[: max_chars // 3]
        middle_start = len(text) // 2 - max_chars // 6
        middle_end = len(text) // 2 + max_chars // 6
        middle = text[middle_start:middle_end]
        end = text[-max_chars // 3 :]
        return f"{start}\n\n...\n\n{middle}\n\n...\n\n{end}"

    def _generate_narrative_profile(self) -> Dict[str, Any]:
        """Uses an LLM to determine the overall tone, pace, and style of the book."""
        prompt = (
            "You are a literary analyst and audiobook director. Based on the provided text, "
            "generate a narrative profile for the audiobook production. Analyze the writing style, "
            "themes, and overall mood.\n\n"
            "**Text for Analysis:**\n"
            f"{self.analysis_text[:8000]}\n\n"  # Use a smaller chunk for this part
            "**Your Task:**\n"
            "Describe the book's narrative style and recommend a production approach.\n\n"
            "Respond with a single JSON object with the following keys:\n"
            "- 'primary_tone': The dominant emotion or mood (e.g., 'suspenseful', 'academic', 'comedic').\n"
            "- 'secondary_tone': A subordinate but important mood (e.g., 'romantic', 'melancholic').\n"
            