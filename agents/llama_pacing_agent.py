"""
LlamaPacingAgent - An agent for analyzing text and providing pacing hints for TTS.

This agent is responsible for:
- Analyzing a chunk of text to understand its emotional and narrative tone.
- Providing pacing hints (e.g., "fast", "normal", "slow") to guide the TTS engine.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .llama_base import LlamaAgent

logger = logging.getLogger(__name__)


class LlamaPacingAgent(LlamaAgent):
    """
    Analyzes text and provides pacing hints for TTS synthesis.
    """

    def get_pacing_hint(self, text: str) -> str:
        """
        Uses an LLM to analyze the text and return a pacing hint.

        Returns:
            A string which can be "fast", "normal", "slow", or "dramatic_pause".
            Returns "normal" as a fallback.
        """
        prompt = (
            "You are a voice director for an audiobook. Your task is to analyze the following text "
            "and decide on the pacing for the narration. Consider the emotional tone, the level of action, "
            "and the overall narrative flow.\n\n"
            "**Text to Analyze:**\n"
            f'"{text}"\n\n'
            'Choose ONE of the following pacing hints: "fast", "normal", "slow", "dramatic_pause".\n'
            "- Use 'fast' for high-action, exciting, or urgent scenes.\n"
            "- Use 'normal' for neutral narration, dialogue, or standard prose.\n"
            "- Use 'slow' for introspective, sad, or momentous scenes.\n"
            "- Use 'dramatic_pause' for the end of a chapter, a major reveal, or a cliffhanger.\n\n"
            "Return a single JSON object with the key 'pacing_hint'. For example:\n"
            '{"pacing_hint": "slow"}\n\n'
            "Respond with valid JSON only."
        )

        response = self.query_json(prompt, max_tokens=50, temperature=0.2)

        if response.get("error"):
            logger.warning(f"Could not get pacing hint: {response.get('error')}")
            return "normal"

        pacing_hint = response.get("pacing_hint")
        if pacing_hint in ["fast", "normal", "slow", "dramatic_pause"]:
            return pacing_hint

        logger.warning(f"LLM returned an unexpected format for pacing hint: {response}")
        return "normal"

