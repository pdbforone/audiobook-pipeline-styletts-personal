"""
Master unifier for autonomy outputs (Phase AA).
Combines planner, self-eval, audit, retro, and consistency signals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def merge_autonomy_outputs(
    planner: Optional[Dict[str, Any]],
    self_eval: Optional[Dict[str, Any]],
    audit: Optional[Dict[str, Any]],
    retro: Optional[Dict[str, Any]],
    consistency: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merge autonomy outputs without changing individual module behavior.
    Prefers planner outputs, then folds in supporting evidence.
    """
    final_recs: List[Any] = []
    rationale_parts: List[str] = []
    supporting: Dict[str, Any] = {}
    confidence: float = 0.0

    if planner:
        recs = planner.get("autonomous_recommendations", {}).get("changes") or planner.get("suggested_changes") or []
        if isinstance(recs, dict):
            final_recs = [recs]
        elif isinstance(recs, list):
            final_recs = recs
        confidence = float(planner.get("confidence", planner.get("autonomous_recommendations", {}).get("confidence", 0.0)) or 0.0)
        rationale_parts.append("Planner recommendations available")
        supporting["planner"] = planner

    if self_eval:
        supporting["self_eval"] = self_eval
        rationale_parts.append("Self-evaluation signals aggregated")
        confidence = max(confidence, float(self_eval.get("confidence", 0.0) or 0.0))

    if audit:
        supporting["audit"] = audit
        rationale_parts.append("Audit findings reviewed")

    if retro:
        supporting["retro"] = retro
        rationale_parts.append("Retrospective insights included")

    if consistency:
        supporting["consistency"] = consistency
        rationale_parts.append("Consistency checks applied")

    rationale = "; ".join(rationale_parts) if rationale_parts else "No autonomy outputs available"

    return {
        "final_recommendations": final_recs,
        "rationale": rationale,
        "confidence": float(confidence),
        "supporting_evidence": supporting,
    }
