"""
LlamaVoiceMatcher - Intelligent voice selection using LLM analysis.

Analyzes book content (title, synopsis, sample text) and recommends
the best voice from the available voice registry based on:
- Genre and tone of the content
- Voice characteristics (gender, accent, style)
- Narrator experience with similar content
- Engine compatibility
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .llama_base import LlamaAgent

logger = logging.getLogger(__name__)


class LlamaVoiceMatcher(LlamaAgent):
    """
    Intelligent voice matcher that uses LLM to recommend voices.

    Analyzes book content and matches it with available voices based on
    tone, genre, and voice characteristics.
    """

    def __init__(self, voice_registry_path: Optional[Path] = None, **kwargs):
        super().__init__(**kwargs)
        self.voice_registry = self._load_voice_registry(voice_registry_path)

    def _load_voice_registry(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Load voice registry from configs/voices.json."""
        if path is None:
            # Search for voices.json
            search_paths = [
                Path(__file__).parent.parent / "configs" / "voices.json",
                Path("configs/voices.json"),
                Path("../configs/voices.json"),
            ]
            for p in search_paths:
                if p.exists():
                    path = p
                    break

        if path is None or not path.exists():
            logger.warning("Voice registry not found, using empty registry")
            return {"voices": {}}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to load voice registry: %s", exc)
            return {"voices": {}}

    def _get_voice_summaries(self, engine_filter: Optional[str] = None) -> str:
        """Create condensed voice summaries for LLM prompt."""
        voices = self.voice_registry.get("voices", {})
        summaries = []

        for voice_id, voice_data in voices.items():
            # Filter by engine if specified
            if engine_filter:
                voice_engine = voice_data.get("engine", "xtts")
                if voice_engine != engine_filter:
                    continue

            # Build compact summary
            desc = voice_data.get("description", "")
            gender = voice_data.get("gender", "unknown")
            accent = voice_data.get("accent", "neutral")
            profiles = voice_data.get("preferred_profiles", [])

            summary = f"- {voice_id}: {desc} | {gender}/{accent} | profiles: {', '.join(profiles[:3])}"
            summaries.append(summary)

        return "\n".join(summaries[:30])  # Limit to top 30 for prompt size

    def recommend_voice(
        self,
        title: str,
        sample_text: str,
        detected_genre: Optional[str] = None,
        author: Optional[str] = None,
        engine: Optional[str] = None,
        top_n: int = 3,
    ) -> Dict[str, Any]:
        """
        Recommend best voices for the given book content.

        Args:
            title: Book title
            sample_text: First 500-1000 chars of book text
            detected_genre: Pre-detected genre (optional)
            author: Author name (optional)
            engine: Filter voices by engine (xtts, kokoro)
            top_n: Number of recommendations to return

        Returns:
            dict with keys:
                - recommendations: List of {voice_id, reason, confidence}
                - analysis: Content analysis summary
                - confidence: Overall confidence in recommendations
        """
        fallback = {
            "recommendations": [{"voice_id": "neutral_narrator", "reason": "fallback", "confidence": 0.0}],
            "analysis": "LLM unavailable",
            "confidence": 0.0,
        }

        voice_summaries = self._get_voice_summaries(engine)
        if not voice_summaries:
            logger.warning("No voices available for matching")
            return fallback

        # Truncate sample text
        sample = sample_text[:800] if sample_text else ""

        prompt = (
            "You are an audiobook voice casting expert. Analyze the book content and recommend "
            f"the {top_n} best voices from the available options.\n\n"
            f"**Book Title:** {title}\n"
            f"**Author:** {author or 'Unknown'}\n"
            f"**Detected Genre:** {detected_genre or 'Unknown'}\n\n"
            f"**Sample Text (first 800 chars):**\n{sample}\n\n"
            "**Available Voices:**\n"
            f"{voice_summaries}\n\n"
            "**Your Task:**\n"
            "1. Analyze the tone, style, and genre of the content\n"
            "2. Consider what type of narrator voice would best serve this content:\n"
            "   - Academic/philosophical texts need measured, authoritative voices\n"
            "   - Fiction needs expressive, engaging voices\n"
            "   - Gothic/horror benefits from dramatic, deep voices\n"
            "   - Memoir/personal works suit warm, relatable voices\n"
            "3. Match voice characteristics (gender, accent, style) to content needs\n"
            "4. Recommend the best voices with reasoning\n\n"
            "Respond with JSON:\n"
            "{\n"
            '  "analysis": "Brief content analysis (tone, style, genre)",\n'
            '  "recommendations": [\n'
            '    {"voice_id": "exact_voice_id", "reason": "why this voice fits", "confidence": 0.0-1.0},\n'
            "    ...\n"
            "  ],\n"
            '  "confidence": 0.0-1.0\n'
            "}"
        )

        try:
            response = self.query_json(prompt, max_tokens=500, temperature=0.3)
        except Exception as exc:
            logger.warning("LlamaVoiceMatcher query failed: %s", exc)
            fallback["analysis"] = f"LLM error: {exc}"
            return fallback

        if not isinstance(response, dict) or response.get("error"):
            note = response.get("error") if isinstance(response, dict) else "Invalid response"
            fallback["analysis"] = note
            return fallback

        # Validate and normalize recommendations
        recommendations = response.get("recommendations", [])
        validated_recs = []
        voices = self.voice_registry.get("voices", {})

        for rec in recommendations[:top_n]:
            voice_id = rec.get("voice_id", "")
            # Normalize voice_id
            normalized_id = voice_id.lower().replace(" ", "_")

            if normalized_id in voices or voice_id in voices:
                validated_recs.append({
                    "voice_id": normalized_id if normalized_id in voices else voice_id,
                    "reason": rec.get("reason", ""),
                    "confidence": float(rec.get("confidence", 0.5)),
                })

        if not validated_recs:
            # LLM recommended voices not in registry, fallback
            validated_recs = [{"voice_id": "neutral_narrator", "reason": "LLM recommendations invalid", "confidence": 0.0}]

        return {
            "recommendations": validated_recs,
            "analysis": response.get("analysis", ""),
            "confidence": float(response.get("confidence", 0.0)),
        }

    def quick_match(
        self,
        genre: str,
        tone: Optional[str] = None,
        gender_preference: Optional[str] = None,
        accent_preference: Optional[str] = None,
        engine: Optional[str] = None,
    ) -> List[str]:
        """
        Fast rule-based voice matching without LLM (for batch processing).

        Args:
            genre: Content genre (philosophy, fiction, gothic, etc.)
            tone: Content tone (academic, dramatic, warm, etc.)
            gender_preference: male, female, or None
            accent_preference: British, American, neutral, etc.
            engine: Filter by engine (xtts, kokoro)

        Returns:
            List of matching voice_ids, ordered by relevance
        """
        voices = self.voice_registry.get("voices", {})
        scored_voices: List[Tuple[str, int]] = []

        for voice_id, voice_data in voices.items():
            score = 0

            # Engine filter
            voice_engine = voice_data.get("engine", "xtts")
            if engine and voice_engine != engine:
                continue

            # Genre/profile match
            profiles = voice_data.get("preferred_profiles", [])
            if genre.lower() in [p.lower() for p in profiles]:
                score += 10

            # Gender preference
            if gender_preference:
                voice_gender = voice_data.get("gender", "").lower()
                if voice_gender == gender_preference.lower():
                    score += 5

            # Accent preference
            if accent_preference:
                voice_accent = voice_data.get("accent", "").lower()
                if accent_preference.lower() in voice_accent:
                    score += 5

            # Tone matching via characteristics
            characteristics = voice_data.get("characteristics", {})
            if tone:
                if tone.lower() in str(characteristics).lower():
                    score += 3

            if score > 0:
                scored_voices.append((voice_id, score))

        # Sort by score descending
        scored_voices.sort(key=lambda x: x[1], reverse=True)

        return [v[0] for v in scored_voices[:5]]

    def get_voice_details(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get full details for a voice."""
        voices = self.voice_registry.get("voices", {})
        normalized = voice_id.lower().replace(" ", "_")
        return voices.get(normalized) or voices.get(voice_id)

    def list_voices_by_genre(self, genre: str) -> List[Dict[str, Any]]:
        """List all voices suitable for a genre."""
        voices = self.voice_registry.get("voices", {})
        results = []

        for voice_id, voice_data in voices.items():
            profiles = voice_data.get("preferred_profiles", [])
            if genre.lower() in [p.lower() for p in profiles]:
                results.append({
                    "voice_id": voice_id,
                    "description": voice_data.get("description", ""),
                    "gender": voice_data.get("gender"),
                    "accent": voice_data.get("accent"),
                    "engine": voice_data.get("engine", "xtts"),
                })

        return results
