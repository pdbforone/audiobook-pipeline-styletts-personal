"""
Phase M: Profile computation utilities (additive-only, off by default).

These helpers aggregate long-run signals into lightweight, read-only profiles.
No pipeline behavior is changed; outputs are informational and stored under
``.pipeline/profiles`` or ``.pipeline/profile_history`` when explicitly enabled.
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional


def _safe_mean(values: List[float]) -> Optional[float]:
    nums = [v for v in values if isinstance(v, (int, float))]
    return mean(nums) if nums else None


def compute_engine_stability_profile(run_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate engine success/failure rates across many runs.
    Returns:
    {
      "engine_stats": {...},
      "preferred_engine": "...",
      "confidence": float
    }
    """
    engine_stats: Dict[str, Dict[str, Any]] = {}
    for run in run_history or []:
        evaluator = (run.get("payload") or {}).get("evaluator") or {}
        engine = evaluator.get("engine_used") or evaluator.get("engine")
        score = evaluator.get("score")
        failure_rate = (
            evaluator.get("metrics", {}).get("chunk_failure_rate", {}).get("rate")
            if isinstance(evaluator, dict)
            else None
        )
        if not engine:
            continue
        stats = engine_stats.setdefault(engine, {"count": 0, "scores": [], "failures": []})
        stats["count"] += 1
        if isinstance(score, (int, float)):
            stats["scores"].append(score)
        if isinstance(failure_rate, (int, float)):
            stats["failures"].append(failure_rate)

    preferred_engine = None
    if engine_stats:
        preferred_engine = max(engine_stats.items(), key=lambda kv: kv[1]["count"])[0]

    confidence = 0.0
    total = sum(stats.get("count", 0) for stats in engine_stats.values())
    if total:
        confidence = min(1.0, total / max(1.0, total + 5.0))

    # Summarize averages for convenience
    for stats in engine_stats.values():
        stats["avg_score"] = _safe_mean(stats.get("scores", []))
        stats["avg_failure_rate"] = _safe_mean(stats.get("failures", []))

    return {
        "engine_stats": engine_stats,
        "preferred_engine": preferred_engine,
        "confidence": confidence,
    }


def compute_chunking_stability_profile(run_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate chunk-size effectiveness across runs:
    - error rates
    - evaluator improvements
    - stability indicators
    Returns {
      "size_stats": {...},
      "recommended_chunk_size": int,
      "confidence": float
    }
    """
    size_stats: Dict[int, Dict[str, Any]] = {}
    for run in run_history or []:
        evaluator = (run.get("payload") or {}).get("evaluator") or {}
        chunk_size = evaluator.get("chunk_size")
        score = evaluator.get("score")
        failure_rate = (
            evaluator.get("metrics", {}).get("chunk_failure_rate", {}).get("rate")
            if isinstance(evaluator, dict)
            else None
        )
        if not isinstance(chunk_size, (int, float)):
            continue
        stats = size_stats.setdefault(int(chunk_size), {"count": 0, "scores": [], "failures": []})
        stats["count"] += 1
        if isinstance(score, (int, float)):
            stats["scores"].append(score)
        if isinstance(failure_rate, (int, float)):
            stats["failures"].append(failure_rate)

    recommended_chunk_size = None
    if size_stats:
        recommended_chunk_size = max(size_stats.items(), key=lambda kv: kv[1]["count"])[0]

    confidence = 0.0
    total = sum(stats.get("count", 0) for stats in size_stats.values())
    if total:
        confidence = min(1.0, total / max(1.0, total + 5.0))

    for stats in size_stats.values():
        stats["avg_score"] = _safe_mean(stats.get("scores", []))
        stats["avg_failure_rate"] = _safe_mean(stats.get("failures", []))

    return {
        "size_stats": size_stats,
        "recommended_chunk_size": recommended_chunk_size,
        "confidence": confidence,
    }


def compute_genre_profile(
    run_history: List[Dict[str, Any]],
    metadata_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build long-run profile of:
      - genre-performant engine
      - rewrite policies by genre
      - chunk size patterns per genre
    Returns {
      "genre": "philosophy" | "fiction" | ...,
      "prefs": {
        "engine": ...,
        "chunk_size": ...,
        "rewrite_policy": ...
      },
      "confidence": float
    }
    """
    genre_counts: Dict[str, int] = {}
    genre_engine: Dict[str, Dict[str, int]] = {}
    genre_chunk_sizes: Dict[str, List[int]] = {}

    for run in run_history or []:
        evaluator = (run.get("payload") or {}).get("evaluator") or {}
        genre = evaluator.get("genre")
        engine = evaluator.get("engine_used")
        chunk_size = evaluator.get("chunk_size")
        if genre:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
            if engine:
                stats = genre_engine.setdefault(genre, {})
                stats[engine] = stats.get(engine, 0) + 1
            if isinstance(chunk_size, (int, float)):
                genre_chunk_sizes.setdefault(genre, []).append(int(chunk_size))

    for meta in metadata_history or []:
        genre = meta.get("genre")
        if genre:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    genre_selected = None
    if genre_counts:
        genre_selected = max(genre_counts.items(), key=lambda kv: kv[1])[0]

    engine_pref = None
    if genre_selected and genre_selected in genre_engine:
        engine_pref = max(genre_engine[genre_selected].items(), key=lambda kv: kv[1])[0]

    chunk_pref = None
    if genre_selected and genre_selected in genre_chunk_sizes:
        chunk_pref = _safe_mean(genre_chunk_sizes[genre_selected])
        chunk_pref = int(chunk_pref) if chunk_pref else None

    confidence = 0.0
    total = sum(genre_counts.values())
    if total:
        confidence = min(1.0, total / max(1.0, total + 5.0))

    return {
        "genre": genre_selected,
        "prefs": {
            "engine": engine_pref,
            "chunk_size": chunk_pref,
        "rewrite_policy": None,  # Placeholder for future policies
        },
        "confidence": confidence,
    }


def choose_overrides_from_profile(profile: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given an active profile, return a suggested overrides dict:
    {
      "chunk_size": ...,
      "engine_preference": ...,
      "rewrite_policy": ...
    }
    This is the 'exploit' path (use what historically worked).
    """
    prefs = profile.get("prefs") or {}
    overrides: Dict[str, Any] = {}
    if prefs.get("chunk_size") is not None:
        overrides["chunk_size"] = {"value": prefs.get("chunk_size"), "source": "profile"}
    if prefs.get("engine"):
        overrides["engine_preference"] = {"preferred": prefs.get("engine"), "source": "profile"}
    if prefs.get("rewrite_policy"):
        overrides["rewrite_policy"] = prefs.get("rewrite_policy")
    if profile.get("engine_preference") and "engine_preference" not in overrides:
        overrides["engine_preference"] = {"preferred": profile.get("engine_preference"), "source": "profile"}
    if profile.get("chunk_size_preference") and "chunk_size" not in overrides:
        overrides["chunk_size"] = {"value": profile.get("chunk_size_preference"), "source": "profile"}
    if profile.get("rewrite_policy_preference") and "rewrite_policy" not in overrides:
        overrides["rewrite_policy"] = profile.get("rewrite_policy_preference")
    return overrides


def maybe_explore(profile: Dict[str, Any], base_overrides: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    With a small probability (exploration_rate), tweak one of the profile-driven
    parameters slightly (e.g., +/- small delta on chunk_size, or alternate rewriter policy).
    Always respect autonomy policy bounds and budget.
    Returns possibly-modified overrides.
    """
    profiles_cfg = (config or {}).get("profiles") if isinstance(config, dict) else {}
    exploration_rate = profiles_cfg.get("exploration_rate", 0.05) if isinstance(profiles_cfg, dict) else 0.05
    overrides = dict(base_overrides or {})
    if not overrides or exploration_rate <= 0:
        return overrides

    if random.random() >= exploration_rate:
        return overrides

    if "chunk_size" in overrides and isinstance(overrides["chunk_size"], dict):
        try:
            value = overrides["chunk_size"].get("value")
            if isinstance(value, (int, float)):
                delta = max(1, int(value * 0.05))
                overrides["chunk_size"]["value"] = max(1, value + random.choice([-delta, delta]))
                overrides["chunk_size"]["source"] = "profile_explore"
        except Exception:
            pass
    elif "rewrite_policy" in overrides and isinstance(overrides["rewrite_policy"], str):
        overrides["rewrite_policy"] = f"{overrides['rewrite_policy']}_explore"
    elif "engine_preference" in overrides and isinstance(overrides["engine_preference"], dict):
        alt_engine = profile.get("alternate_engine")
        if alt_engine:
            overrides["engine_preference"]["preferred"] = alt_engine
            overrides["engine_preference"]["source"] = "profile_explore"

    return overrides


def export_profiles(path: str) -> None:
    """
    Export current profiles data to a given path (e.g.,
    .pipeline/profiles/exports/profiles_export_<timestamp>.json).
    Used for manual inspection; non-destructive.
    """
    try:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_path = Path(path)
        export_path = export_path / f"profiles_export_{ts}.json" if export_path.is_dir() else export_path
        export_path.parent.mkdir(parents=True, exist_ok=True)
        profiles_dir = Path(".pipeline") / "profiles"
        payload: Dict[str, Any] = {"exported_at": ts, "files": []}
        if profiles_dir.exists():
            for p in profiles_dir.glob("*.json"):
                try:
                    payload["files"].append({"name": p.name, "data": json.loads(p.read_text(encoding="utf-8"))})
                except Exception:
                    continue
        export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        return


def reset_profiles() -> None:
    """
    Reset profiles by archiving/removing the profiles.json file.
    This does NOT affect any other pipeline state.
    """
    profiles_dir = Path(".pipeline") / "profiles"
    profiles_file = profiles_dir / "profiles.json"
    if not profiles_file.exists():
        return
    try:
        archive_dir = profiles_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        profiles_file.replace(archive_dir / f"profiles_reset_{ts}.json")
    except Exception:
        return
