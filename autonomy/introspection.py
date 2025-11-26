"""
Interpretability summary builder (Phase I, opt-in).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


def build_introspection_summary(
    planner_output: Dict[str, Any],
    evaluator_summary: Dict[str, Any],
    diagnostics_summary: Dict[str, Any],
    readiness: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a unified explanation file:
    - planner rationale
    - top issues found by evaluator
    - anomalies from diagnostics
    - if available, readiness flags and reasons
    - if available, feature attribution top factors
    Returns dict.
    """
    attribution = planner_output.get("attribution") if isinstance(planner_output, dict) else {}
    suggested = planner_output.get("suggested_changes") if isinstance(planner_output, dict) else None
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "planner": {
            "recommendations": suggested,
            "confidence": planner_output.get("confidence") if isinstance(planner_output, dict) else None,
            "attribution": attribution,
        },
        "evaluator": {
            "score": evaluator_summary.get("score") if isinstance(evaluator_summary, dict) else None,
            "issues": evaluator_summary.get("issues") if isinstance(evaluator_summary, dict) else [],
        },
        "diagnostics": (diagnostics_summary or {}).get("diagnostics", {}),
        "readiness": readiness or {},
    }
