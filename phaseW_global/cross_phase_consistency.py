"""Cross-phase consistency analyzer for Phase W (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any, List


def analyze_consistency(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare outputs across phases 1→6.
    Returns:
    {
      "consistent": bool,
      "issues": [
         { "from_phase": str,
           "to_phase": str,
           "field": str,
           "problem": str }
      ],
      "summary": str
    }
    """
    issues: List[Dict[str, str]] = []
    phases = ["phase1", "phase2", "phase3", "phase4", "phase5", "phase6"]
    for i in range(len(phases) - 1):
        from_phase = phases[i]
        to_phase = phases[i + 1]
        from_payload = inputs.get(from_phase) if isinstance(inputs, dict) else None
        to_payload = inputs.get(to_phase) if isinstance(inputs, dict) else None
        if not isinstance(from_payload, dict) or not isinstance(to_payload, dict):
            issues.append(
                {
                    "from_phase": from_phase,
                    "to_phase": to_phase,
                    "field": "",
                    "problem": "missing_payload",
                }
            )
            continue
        # Basic consistency check: shared run_id if present
        from_run = from_payload.get("run_id")
        to_run = to_payload.get("run_id")
        if from_run and to_run and from_run != to_run:
            issues.append(
                {
                    "from_phase": from_phase,
                    "to_phase": to_phase,
                    "field": "run_id",
                    "problem": "run_id_mismatch",
                }
            )

    consistent = len(issues) == 0
    summary = "Cross-phase consistent" if consistent else "Cross-phase inconsistencies found"
    return {
        "consistent": consistent,
        "issues": issues,
        "summary": summary,
    }
