"""
Genre-specific chunking profiles for TTS optimization.

Each profile defines:
- Word/character ranges optimized for the genre
- Special rules for preserving semantic units
- TTS priorities (clarity, pacing, emotion)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class ChunkProfile:
    """Configuration for genre-specific chunking."""

    name: str
    min_words: int
    max_words: int
    min_chars: int
    max_chars: int
    rules: Dict[str, bool]
    description: str
    tts_priority: str
    genre_duration_overrides: Dict[str, Dict[str, int]] = field(
        default_factory=dict
    )

    def get_rule(self, rule_name: str, default: bool = False) -> bool:
        """Safely get a rule value with default fallback."""
        return self.rules.get(rule_name, default)


# Genre-specific chunking profiles
GENRE_DURATION_OVERRIDES: Dict[str, Dict[str, int]] = {
    "philosophy": {
        "min_duration": 12,
        "target_duration": 18,
        "max_duration": 28,
    },
    "fiction": {"min_duration": 10, "target_duration": 15, "max_duration": 22},
    "technical": {
        "min_duration": 8,
        "target_duration": 12,
        "max_duration": 18,
    },
}

PROFILES: Dict[str, ChunkProfile] = {
    "philosophy": ChunkProfile(
        name="philosophy",
        min_words=280,
        max_words=450,
        min_chars=1400,
        max_chars=2250,
        rules={
            "no_semicolon_splits": True,  # Preserve complex arguments
            "add_context": True,  # Include previous context
            "preserve_logical_units": True,  # Keep "if...then" together
            "no_mid_argument_splits": True,  # Keep reasoning chains intact
        },
        description="Measured tone for philosophical texts with complex arguments",
        tts_priority="clarity",
        genre_duration_overrides=GENRE_DURATION_OVERRIDES,
    ),
    "fiction": ChunkProfile(
        name="fiction",
        min_words=200,
        max_words=350,
        min_chars=1000,
        max_chars=1750,
        rules={
            "preserve_quotes": True,  # Keep dialogue intact
            "scene_break_splits": True,  # Split on scene boundaries
            "no_mid_dialogue_splits": True,  # Never split inside quotes
            "preserve_speaker_tags": True,  # Keep "he said" with dialogue
        },
        description="Warm, engaging for fiction with dialogue preservation",
        tts_priority="emotional_pacing",
        genre_duration_overrides=GENRE_DURATION_OVERRIDES,
    ),
    "academic": ChunkProfile(
        name="academic",
        min_words=150,
        max_words=300,
        min_chars=750,
        max_chars=1500,
        rules={
            "preserve_lists": True,  # Keep enumerated lists together
            "tag_code": True,  # Mark code/equations specially
            "preserve_citations": True,  # Keep citations with statements
            "no_mid_list_splits": True,  # Keep list items together
        },
        description="Clear, impartial for technical/academic content",
        tts_priority="precision",
        genre_duration_overrides=GENRE_DURATION_OVERRIDES,
    ),
    "memoir": ChunkProfile(
        name="memoir",
        min_words=220,
        max_words=360,
        min_chars=1100,
        max_chars=1800,
        rules={
            "short_direct_address": True,  # Shorter when addressing reader
            "preserve_anecdotes": True,  # Keep stories intact
            "emotional_breaks": True,  # Allow breaks at emotional shifts
        },
        description="Conversational pacing for memoirs and self-help",
        tts_priority="conversational",
        genre_duration_overrides=GENRE_DURATION_OVERRIDES,
    ),
    "technical": ChunkProfile(
        name="technical",
        min_words=150,
        max_words=300,
        min_chars=750,
        max_chars=1500,
        rules={
            "preserve_steps": True,  # Keep procedural steps together
            "preserve_code": True,  # Don't split code blocks
            "preserve_formulas": True,  # Keep mathematical formulas intact
            "tag_warnings": True,  # Mark warnings/cautions
        },
        description="Precise for technical manuals and how-to content",
        tts_priority="precision",
        genre_duration_overrides=GENRE_DURATION_OVERRIDES,
    ),
    "auto": ChunkProfile(
        name="auto",
        min_words=200,
        max_words=400,
        min_chars=1000,
        max_chars=2000,
        rules={
            "balanced_approach": True,  # Mix of all rules
            "adaptive_sizing": True,  # Adjust based on content
        },
        description="Heuristic detection with balanced approach",
        tts_priority="balanced",
        genre_duration_overrides=GENRE_DURATION_OVERRIDES,
    ),
}


def get_profile(profile_name: str) -> ChunkProfile:
    """
    Get a chunking profile by name.

    Args:
        profile_name: Name of the profile (e.g., 'philosophy', 'fiction')

    Returns:
        ChunkProfile object

    Raises:
        ValueError: If profile name is not found
    """
    profile_name = profile_name.lower()

    if profile_name not in PROFILES:
        available = ", ".join(PROFILES.keys())
        raise ValueError(
            f"Unknown profile: '{profile_name}'. "
            f"Available profiles: {available}"
        )

    return PROFILES[profile_name]


def list_profiles() -> List[str]:
    """Get list of available profile names."""
    return list(PROFILES.keys())


def get_profile_info(profile_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a profile.

    Args:
        profile_name: Name of the profile

    Returns:
        Dictionary with profile details
    """
    profile = get_profile(profile_name)
    return {
        "name": profile.name,
        "word_range": f"{profile.min_words}-{profile.max_words}",
        "char_range": f"{profile.min_chars}-{profile.max_chars}",
        "description": profile.description,
        "tts_priority": profile.tts_priority,
        "rules": profile.rules,
    }


# Export for convenience
__all__ = [
    "ChunkProfile",
    "PROFILES",
    "get_profile",
    "list_profiles",
    "get_profile_info",
]
