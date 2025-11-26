"""
Policy Kernel - consolidates insights into a normalized structure (opt-in).

No planner actions are triggered here; planner may call this to get a stable
object containing evaluator/diagnostics/memory/benchmarks/genre signals.
"""

from __future__ import annotations

from typing import Any, Dict, List


def combine_insights(
    evaluator_summary: Dict[str, Any] | None = None,
    diagnostics: Dict[str, Any] | None = None,
    memory_summary: Dict[str, Any] | None = None,
    benchmarks: Dict[str, Any] | None = None,
    genre_info: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Consolidate raw signals into a unified, stable, non-destructive insight bundle.
    Produces structured fields without modifying pipeline behavior.
    """
    evaluator_summary = evaluator_summary or {}
    diagnostics = diagnostics or {}
    memory_summary = memory_summary or {}
    benchmarks = benchmarks or {}
    genre_info = genre_info or {}

    issues: List[str] = []
    hypotheses: List[str] = []

    diag_block = diagnostics.get("diagnostics") if isinstance(diagnostics, dict) else {}
    if isinstance(diag_block, dict):
        issues.extend(diag_block.get("anomalies") or [])
        hypotheses.extend(diag_block.get("hypotheses") or [])

    return {
        "score": evaluator_summary.get("score") if isinstance(evaluator_summary, dict) else None,
        "signals": {
            "evaluator": evaluator_summary,
            "diagnostics": diagnostics,
            "memory": memory_summary,
            "benchmarks": benchmarks if isinstance(benchmarks, list) else benchmarks,
            "genre": genre_info,
        },
        "issues": issues,
        "hypotheses": hypotheses,
        "notes": "No config changes. Kernel produces insights only.",
        "recommendations": [],
    }
