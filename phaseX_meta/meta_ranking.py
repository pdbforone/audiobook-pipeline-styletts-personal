"""Meta ranking for Phase X (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any, List


def rank_meta_findings(kernel_output: Dict[str, Any], fusion_output: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
    """
    Rank meta findings.

    Returns:
    {
      "ranked_factors": [
          {"factor": str, "impact": float, "notes": str}
      ],
      "top_issue": str,
      "top_strength": str,
      "confidence": float
    }
    """
    dims = (kernel_output or {}).get("meta_dimensions") or {}
    fusion_signals = (fusion_output or {}).get("signals") or {}
    weak_dims = fusion_signals.get("weak_dimensions") or []
    strong_dims = fusion_signals.get("strong_dimensions") or []

    ranked: List[Dict[str, Any]] = []
    for name in weak_dims[: max_depth]:
        ranked.append({"factor": name, "impact": -1.0, "notes": "Weak dimension"})
    for name in strong_dims[: max_depth]:
        ranked.append({"factor": name, "impact": 1.0, "notes": "Strong dimension"})

    top_issue = weak_dims[0] if weak_dims else ""
    top_strength = strong_dims[0] if strong_dims else ""
    confidence = float((fusion_signals.get("meta_score") or 0.0))

    return {
        "ranked_factors": ranked,
        "top_issue": top_issue,
        "top_strength": top_strength,
        "confidence": confidence,
    }
