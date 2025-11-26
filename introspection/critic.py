"""
Self-critique agent (analysis only, opt-in).
"""

from __future__ import annotations

from typing import Any, Dict, List


def self_critique(
    evaluator_summary: Dict[str, Any] | None,
    diagnostics_summary: Dict[str, Any] | None,
    planner_recommendations: Dict[str, Any] | None,
    clusters: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Produces a structured self-critique:
    {
       "strengths": [...],
       "weaknesses": [...],
       "missed_opportunities": [...],
       "surprising_outcomes": [...],
       "confidence": float
    }
    """
    strengths: List[Any] = []
    weaknesses: List[Any] = []
    missed: List[Any] = []
    surprises: List[Any] = []

    score = (evaluator_summary or {}).get("score")
    issues = (evaluator_summary or {}).get("issues") or []
    diagnostics = ((diagnostics_summary or {}).get("diagnostics") or {}).get("anomalies") or []
    reg = (clusters or {}).get("regressions") or []

    if isinstance(score, (int, float)) and score >= 80:
        strengths.append(f"High evaluator score ({score})")
    if issues:
        weaknesses.extend([str(i) for i in issues])
    if diagnostics:
        weaknesses.extend([f"diag:{a}" for a in diagnostics])
    if reg:
        surprises.extend([f"regression:{r}" for r in reg])

    if planner_recommendations and planner_recommendations.get("suggested_changes"):
        missed.append("Planner suggested changes remain untested (recommend-only).")

    confidence = 0.5
    if weaknesses or surprises:
        confidence = 0.6

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missed_opportunities": missed,
        "surprising_outcomes": surprises,
        "confidence": confidence,
    }
