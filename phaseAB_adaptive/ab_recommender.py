"""
Phase AB recommender: propose bounded actions (read-only, no auto-apply).
"""

from __future__ import annotations

from typing import Any, Dict, List


def recommend_actions(fused: Dict[str, Any], classification: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate advisory actions. Always marked as bounded_by_safety_envelope.
    """
    actions: List[Dict[str, Any]] = []
    class_label = (classification or {}).get("classification", "caution")
    base_conf = float((classification or {}).get("confidence", 0.0) or 0.0)
    base_score = float((classification or {}).get("score", 0.0) or 0.0)

    if class_label == "healthy":
        actions.append(
            {
                "category": "monitoring",
                "action": "Maintain current settings; review autonomy readiness report.",
                "confidence": min(1.0, base_conf + 0.1),
                "bounded_by_safety_envelope": True,
            }
        )
    elif class_label == "caution":
        actions.append(
            {
                "category": "guardrails",
                "action": "Increase safety envelope checks and re-run self-evaluation before applying changes.",
                "confidence": max(0.3, base_conf),
                "bounded_by_safety_envelope": True,
            }
        )
        if fused.get("stability"):
            actions.append(
                {
                    "category": "stability",
                    "action": "Review stability bounds and drift indicators before enabling autonomy.",
                    "confidence": max(0.3, base_score),
                    "bounded_by_safety_envelope": True,
                }
            )
    else:
        actions.append(
            {
                "category": "pause",
                "action": "Pause autonomy, run audits, and resolve schema/health issues.",
                "confidence": max(0.2, base_conf),
                "bounded_by_safety_envelope": True,
            }
        )
        actions.append(
            {
                "category": "investigation",
                "action": "Deep-dive into self-eval, audit, and health reports to identify blockers.",
                "confidence": max(0.2, base_score),
                "bounded_by_safety_envelope": True,
            }
        )

    return actions
