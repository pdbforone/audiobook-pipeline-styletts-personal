"""
Narrative explainer for Phase I (opt-in, additive only).
"""

from __future__ import annotations

from typing import Any, Dict


def generate_narrative(
    clusters: Dict[str, Any] | None,
    evaluator_summary: Dict[str, Any] | None,
    diagnostics_summary: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Produces a human-readable narrative describing:
      - what likely happened
      - why issues grouped the way they did
      - which parts of pipeline might need attention
    Returns:
      {
         "narrative": str,
         "confidence": float,
         "sections": [...]
      }
    """
    clusters = clusters or {}
    eval_score = (evaluator_summary or {}).get("score")
    issues = (evaluator_summary or {}).get("issues") or []
    diag_anomalies = ((diagnostics_summary or {}).get("diagnostics") or {}).get("anomalies") or []

    sections = []
    if issues:
        sections.append(f"Issues observed: {', '.join([str(i) for i in issues])}")
    if diag_anomalies:
        sections.append(f"Diagnostics anomalies: {', '.join([str(a) for a in diag_anomalies])}")
    if clusters.get("regressions"):
        sections.append(f"Potential regressions: {', '.join([str(r) for r in clusters.get('regressions', [])])}")

    base_narrative = "Run appears stable."
    if issues or diag_anomalies:
        base_narrative = "Run encountered anomalies grouped into clusters."

    if eval_score is not None:
        base_narrative += f" Evaluator score: {eval_score}."

    confidence = 0.5
    if issues or diag_anomalies:
        confidence = 0.6

    return {
        "narrative": base_narrative,
        "confidence": confidence,
        "sections": sections,
    }
