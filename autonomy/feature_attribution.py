"""
Feature attribution for planner recommendations (Phase I, opt-in).
"""

from __future__ import annotations

from typing import Any, Dict


def explain_recommendations(
    recommendations: Dict[str, Any],
    policy_signals: Dict[str, Any],
    evaluator_summary: Dict[str, Any],
    diagnostics_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Produce a structured explanation of:
    - what inputs most influenced planner decisions
    - how confidence was derived
    - which signals mattered most
    - what factors were ignored
    Returns a JSON-serializable dict.
    """
    recs = recommendations or {}
    signals = policy_signals or {}

    influenced_by = []
    ignored = []

    if evaluator_summary.get("issues"):
        influenced_by.append("evaluator_issues")
    if diagnostics_summary.get("diagnostics", {}).get("anomalies"):
        influenced_by.append("diagnostics_anomalies")
    if signals:
        influenced_by.append("policy_signals")

    if not recs.get("suggested_changes"):
        ignored.append("no_changes_suggested")

    confidence = recs.get("confidence") if isinstance(recs, dict) else None
    if not isinstance(confidence, (int, float)):
        confidence = 0.5

    return {
        "influenced_by": influenced_by,
        "ignored": ignored,
        "confidence": confidence,
        "inputs": {
            "recommendations": recs,
            "policy_signals": signals,
            "evaluator": evaluator_summary or {},
            "diagnostics": diagnostics_summary or {},
        },
    }
