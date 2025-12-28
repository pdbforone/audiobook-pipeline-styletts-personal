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
            "- 'pace': Recommended reading pace (e.g., 'slow and deliberate', 'fast-paced and energetic').\n"
            "- 'target_audience': The likely audience for this book (e.g., 'young adults', 'academics', 'history enthusiasts').\n"
            "- 'production_notes': A brief summary of recommendations for the audio engineer (e.g., 'Use subtle sound effects for atmosphere', 'Keep the narration dry and unadorned')."
        )
        return self.query_json(prompt)

    def identify_characters(self) -> List[Dict[str, str]]:
        """Identifies main and recurring characters from the text."""
        prompt = (
            "You are a literary analyst. Read the following text and identify the main and recurring characters. "
            "For each character, provide a brief description of their role and personality.\n\n"
            "**Text for Analysis:**\n"
            f"{self.analysis_text}\n\n"
            "**Your Task:**\n"
            "Return a JSON array of objects, where each object represents a character and has the following keys:\n"
            "- 'name': The character's name.\n"
            "- 'description': A brief description of their personality, role, and any notable voice characteristics (e.g., 'gruff old general', 'anxious young scholar')."
        )
        response = self.query_json(prompt)
        return response if isinstance(response, list) else []

    def create_casting_suggestions(self, characters: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        For each character, suggests a suitable voice from the available voice library.
        """
        if not characters:
            return {}

        character_profiles = "\n".join(
            [f"- {c['name']}: {c['description']}" for c in characters]
        )

        prompt = (
            "You are an audiobook casting director. Given a list of characters and their descriptions, "
            "your task is to recommend a suitable voice for each. You will be provided with a list of available voices and their attributes.\n\n"
            "**Characters to Cast:**\n"
            f"{character_profiles}\n\n"
            "**Your Task:**\n"
            "Analyze the characters and recommend the best voice for the narrator and each major character. "
            "Return a single JSON object mapping character names to voice IDs. "
            "Example: {'Narrator': 'en_male_deep', 'Gandalf': 'en_male_old_wise', 'Frodo': 'en_male_young_adventurous'}"
        )

        # In a real implementation, you would pass the available voices to the prompt.
        # For now, we'll let the LLM hallucinate reasonable voice IDs.
        response = self.query_json(prompt)
        return response if isinstance(response, dict) else {}

    def generate_pronunciation_guide(self) -> Dict[str, Any]:
        """
        Identifies potentially difficult or ambiguous words and provides pronunciation guidance.
        """
        return self.pronunciation_assistant.process_text(self.analysis_text)

    def create_production_bible(self) -> Dict[str, Any]:
        """
        Orchestrates the creation of the complete Production Bible.
        """
        logger.info("Creating Production Bible...")
        narrative_profile = self._generate_narrative_profile()
        characters = self.identify_characters()
        casting_suggestions = self.create_casting_suggestions(characters)
        pronunciation_guide = self.generate_pronunciation_guide()

        production_bible = {
            "narrative_profile": narrative_profile,
            "character_map": {
                "characters": characters,
                "casting_suggestions": casting_suggestions,
            },
            "pronunciation_guide": pronunciation_guide,
            "pacing_guide": {
                "default": narrative_profile.get("pace", "normal"),
            },
            "version": "1.0",
            "created_at": self.get_timestamp(),
        }

        logger.info("Production Bible created successfully.")
        return production_bible