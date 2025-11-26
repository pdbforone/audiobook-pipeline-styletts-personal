"""
Global safety envelope unification for Phase AA.
Aggregates signals from downstream safety layers without changing behavior.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _is_blocked(value: Any) -> bool:
    """Return True when a safety signal indicates blocking."""
    if value is False:
        return True
    if isinstance(value, str) and value.lower() in {"fail", "failed", "block", "blocked", "error"}:
        return True
    return False


def enforce_global_safety(
    run_summary: Dict[str, Any],
    readiness: Dict[str, Any],
    safety_envelope: Dict[str, Any],
    escalation: Dict[str, Any],
    drift: Dict[str, Any],
    stability: Dict[str, Any],
    budget: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Unify safety signals across autonomous phases.

    Returns:
        {
          "allow_autonomy": bool,
          "blocked_reasons": list[str],
          "downgrade_to_supervised": bool
        }
    """
    blocked: List[str] = []
    downgrade = False

    if readiness and not readiness.get("ready", True):
        blocked.append("readiness_failed")
        downgrade = True

    if safety_envelope and not safety_envelope.get("safe", True):
        blocked.append("safety_envelope_block")
        downgrade = True

    if escalation.get("lockout"):
        blocked.append("escalation_lockout")
        downgrade = True

    if drift.get("drift_detected"):
        blocked.append("drift_detected")

    if stability.get("violations"):
        blocked.append("stability_violations")

    if budget and not budget.get("allows", True):
        blocked.append("budget_block")

    # Phase-level signals (K/L/Q/S/T/U/V/W/X/Y/Z) funnel through run_summary
    phase_flags = {
        "phaseK_memory_feedback": run_summary.get("memory_feedback_safe"),
        "phaseL_autonomy_core": run_summary.get("autonomy_safe"),
        "phaseQ_self_eval": run_summary.get("self_eval_passed"),
        "phaseS_consistency": run_summary.get("consistency_passed"),
        "phaseT_audit": run_summary.get("audit_passed"),
        "phaseU_schema": run_summary.get("schema_valid"),
        "phaseV_harness": run_summary.get("master_safety_passed"),
        "phaseW_global": run_summary.get("phaseW_safe"),
        "phaseX_meta": run_summary.get("phaseX_safe"),
        "phaseY_self_heal": run_summary.get("phaseY_safe"),
        "phaseZ_meta": run_summary.get("phaseZ_safe"),
    }
    for flag, value in phase_flags.items():
        if _is_blocked(value):
            blocked.append(flag)
            downgrade = True

    allow_autonomy = not blocked

    return {
        "allow_autonomy": allow_autonomy,
        "blocked_reasons": blocked,
        "downgrade_to_supervised": downgrade,
    }
