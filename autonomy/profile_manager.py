"""
Profile fusion utilities for Phase M (additive, reporting-only).

These helpers synthesize multiple profile sources into a read-only
"Autonomous Performance Profile" without modifying runtime behavior.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def fuse_profiles(
    stable_profiles: Optional[Dict[str, Any]],
    genre_profiles: Optional[Dict[str, Any]],
    memory_summary: Optional[Dict[str, Any]],
    reward_history: Optional[list[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Produce a synthesized 'Autonomous Performance Profile' (APP):
      - merges long-run stats
      - weights by reward trends
      - merges with memory-based heuristics
    Returns dict:
    {
      "engine_preference": ...,
      "chunk_size_preference": ...,
      "rewrite_policy_preference": ...,
      "weights": {...},
      "confidence": float
    }
    """
    stable_profiles = stable_profiles or {}
    genre_profiles = genre_profiles or {}
    reward_history = reward_history or []

    engine_pref = None
    chunk_pref = None
    rewrite_pref = None

    engine_profile = stable_profiles.get("engine") if isinstance(stable_profiles, dict) else {}
    chunk_profile = stable_profiles.get("chunking") if isinstance(stable_profiles, dict) else {}

    if engine_profile and isinstance(engine_profile, dict):
        engine_pref = engine_profile.get("preferred_engine")
    if chunk_profile and isinstance(chunk_profile, dict):
        chunk_pref = chunk_profile.get("recommended_chunk_size")

    if genre_profiles and isinstance(genre_profiles, dict):
        prefs = genre_profiles.get("prefs") or {}
        engine_pref = prefs.get("engine") or engine_pref
        chunk_pref = prefs.get("chunk_size") or chunk_pref
        rewrite_pref = prefs.get("rewrite_policy") or rewrite_pref

    rewards = [r.get("reward") for r in reward_history if isinstance(r, dict)]
    rewards = [r for r in rewards if isinstance(r, (int, float))]
    reward_weight = min(1.0, sum(1 for _ in rewards) / 10.0) if rewards else 0.0

    confidence_components = [
        engine_profile.get("confidence") if isinstance(engine_profile, dict) else 0.0,
        chunk_profile.get("confidence") if isinstance(chunk_profile, dict) else 0.0,
        genre_profiles.get("confidence") if isinstance(genre_profiles, dict) else 0.0,
        reward_weight,
    ]
    confidence = sum(c for c in confidence_components if isinstance(c, (int, float))) / max(
        1, len(confidence_components)
    )

    weights = {
        "stable_engine": engine_profile.get("confidence") if isinstance(engine_profile, dict) else 0.0,
        "stable_chunking": chunk_profile.get("confidence") if isinstance(chunk_profile, dict) else 0.0,
        "genre": genre_profiles.get("confidence") if isinstance(genre_profiles, dict) else 0.0,
        "rewards": reward_weight,
    }

    fused_profile = {
        "engine_preference": engine_pref,
        "chunk_size_preference": chunk_pref,
        "rewrite_policy_preference": rewrite_pref,
        "weights": weights,
        "confidence": confidence,
    }

    if memory_summary:
        fused_profile["memory_summary"] = memory_summary

    return fused_profile
