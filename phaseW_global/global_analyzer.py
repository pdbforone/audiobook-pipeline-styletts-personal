"""Global analyzer for Phase W (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any, List


def global_analysis(lint: Dict[str, Any], consistency: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine lint and consistency signals.
    Schema:
    {
      "valid": bool,
      "problems": [...],
      "warnings": [...],
      "recommendations": [...],
      "score": float
    }
    """
    lint_valid = bool((lint or {}).get("valid", False))
    consistent = bool((consistency or {}).get("consistent", False))

    problems: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []

    if not lint_valid:
        problems.append("schema_lint_failed")
    if not consistent:
        problems.append("cross_phase_inconsistency")
    if (lint or {}).get("warnings"):
        warnings.append("lint_warnings_present")
    if (consistency or {}).get("issues"):
        warnings.append("consistency_issues_present")

    # score is weighted combo: lint_valid (0.6) + consistency (0.4)
    score = (0.6 if lint_valid else 0.0) + (0.4 if consistent else 0.0)

    if not problems:
        recommendations.append("Maintain current schemas and monitoring.")
    else:
        recommendations.append("Investigate schema/consistency issues before changes.")

    return {
        "valid": len(problems) == 0,
        "problems": problems,
        "warnings": warnings,
        "recommendations": recommendations,
        "score": score,
    }
