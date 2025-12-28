"""
LlamaPronunciationAssistant - An agent for generating and managing pronunciations.

This agent is responsible for:
- Identifying words that may be difficult for a TTS engine to pronounce.
- Using an LLM to generate phonetic spellings (IPA, ARPAbet) for these words.
- Storing these pronunciations in a project-specific dictionary.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llama_base import LlamaAgent

logger = logging.getLogger(__name__)

PRONUNCIATION_DICT_PATH = Path(".pipeline") / "pronunciation_dictionary.json"


class LlamaPronunciationAssistant(LlamaAgent):
    """
    Identifies difficult words and generates phonetic pronunciations.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pronunciation_dict = self._load_pronunciation_dict()

    def _load_pronunciation_dict(self) -> Dict[str, Any]:
        """Loads the pronunciation dictionary from a JSON file."""
        if PRONUNCIATION_DICT_PATH.exists():
            try:
                with PRONUNCIATION_DICT_PATH.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Could not load pronunciation dictionary: {e}")
                return {{}}
        return {{}}

    def _save_pronunciation_dict(self) -> None:
        """Saves the pronunciation dictionary to a JSON file."""
        try:
            with PRONUNCIATION_DICT_PATH.open("w", encoding="utf-8") as f:
                json.dump(self.pronunciation_dict, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Could not save pronunciation dictionary: {e}")

    def identify_difficult_words(self, text: str) -> List[str]:
        """
        Uses an LLM to identify words in the text that may be difficult to pronounce.
        """
        prompt = (
            "You are an expert in phonetics and linguistics. Your task is to analyze the following text "
            "and identify any words that a standard text-to-speech (TTS) engine might mispronounce. "
            "Focus on proper nouns, neologisms, technical jargon, fantasy names, or words with ambiguous pronunciations.\n\n"
            "**Text to Analyze:**\n"
            f'"{text}"\n\n'
            "Return a JSON list of the identified words. For example: "
            '["Siobhan", "Cthulhu", "Worcestershire"]\n\n'
            "Respond with valid JSON only."
        )

        response = self.query_json(prompt, max_tokens=200, temperature=0.1)

        if response.get("error"):
            logger.warning(f"Could not identify difficult words: {response.get('error')}")
            return []

        # The response should be a list of strings.
        if isinstance(response, list) and all(isinstance(word, str) for word in response):
            return response

        logger.warning(f"LLM returned an unexpected format for difficult words: {response}")
        return []

    def generate_pronunciation(self, word: str) -> Optional[Dict[str, str]]:
        """
        Generates phonetic pronunciations for a given word.
        """
        if word in self.pronunciation_dict:
            return self.pronunciation_dict[word]

        prompt = (
            "You are a phonetician. For the given word, provide its pronunciation in three formats: "
            "IPA (International Phonetic Alphabet), ARPAbet, and a human-readable 'say-as' hint.\n\n"
            f"**Word:** {word}\n\n"
            "Return the result as a JSON object with the keys 'ipa', 'arpabet', and 'say_as'. For example:\n"
            "{\n"
            '  "ipa": "ʃəˈvɔːn",\n'
            '  "arpabet": "SH AH V AO N",\n'
            '  "say_as": "shuh-VAWN"\n'
            "}\n\n"
            "Respond with valid JSON only."
        )

        response = self.query_json(prompt, max_tokens=150, temperature=0.1)

        if response.get("error"):
            logger.warning(f"Could not generate pronunciation for '{word}': {response.get('error')}")
            return None

        if "ipa" in response and "arpabet" in response and "say_as" in response:
            pronunciation = {
                "ipa": response["ipa"],
                "arpabet": response["arpabet"],
                "say_as": response["say_as"],
            }
            self.pronunciation_dict[word] = pronunciation
            self._save_pronunciation_dict()
            return pronunciation

        logger.warning(f"LLM returned an unexpected format for pronunciation: {response}")
        return None

    def process_text(self, text: str) -> None:
        """
        Identifies difficult words in a text and generates pronunciations for them.
        """
        difficult_words = self.identify_difficult_words(text)
        if not difficult_words:
            return

        for word in difficult_words:
            # Check if we already have the pronunciation.
            if word in self.pronunciation_dict:
                continue

            logger.info(f"Generating pronunciation for difficult word: '{word}'")
            self.generate_pronunciation(word)

