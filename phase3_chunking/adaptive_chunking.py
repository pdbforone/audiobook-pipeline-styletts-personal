"""
Adaptive chunking helper (opt-in).

Does not modify chunking behavior; returns suggested chunk sizes only.
"""

from __future__ import annotations

from typing import Any, Dict


def choose_chunk_size(
    base_size: int,
    genre: Dict[str, Any],
    memory_summary: Dict[str, Any],
    diagnostics: Dict[str, Any],
    evaluator_summary: Dict[str, Any],
    engine: str,
) -> Dict[str, Any]:
    """
    Returns:
    {
      "chosen": int,
      "reason": str,
      "confidence": float
    }
    """
    chosen = base_size
    reason = "base_size"
    confidence = 0.5

    # Heuristic adjustments (non-binding)
    top_genre = None
    if isinstance(genre, dict):
        top_genre = max(genre.items(), key=lambda kv: kv[1])[0] if genre else None

    if top_genre == "philosophy":
        chosen = int(base_size * 0.9)
        reason = "philosophy_dense_content"
        confidence = 0.6
    elif top_genre == "fiction" and engine == "kokoro":
        chosen = int(base_size * 1.1)
        reason = "fiction_fast_engine"
        confidence = 0.6

    # If evaluator showed high failure rate, nudge smaller
    failure_rate = None
    if isinstance(evaluator_summary, dict):
        failure_rate = (
            evaluator_summary.get("metrics", {})
            .get("chunk_failure_rate", {})
            .get("rate")
        )
    if failure_rate and failure_rate > 0.05:
        chosen = int(base_size * 0.9)
        reason = "reduce_due_to_failures"
        confidence = 0.65

    return {
        "chosen": max(1, chosen),
        "reason": reason,
        "confidence": confidence,
    }
