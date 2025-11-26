"""
Anomaly clustering for Phase I (opt-in, additive only).
"""

from __future__ import annotations

from typing import Any, Dict, List


def cluster_anomalies(
    evaluator_summary: Dict[str, Any] | None,
    diagnostics_summary: Dict[str, Any] | None,
    recent_history: List[Dict[str, Any]] | None,
) -> Dict[str, Any]:
    """
    Returns a clustering structure identifying:
      - repeated issues
      - new anomalies
      - clusters of related failures
      - possible regression groups
    Shape:
    {
       "clusters": [
          {"label": str, "members": [...], "frequency": int}
       ],
       "new_anomalies": [...],
       "regressions": [...],
    }
    """
    clusters: List[Dict[str, Any]] = []
    new_anomalies: List[Any] = []
    regressions: List[Any] = []

    eval_issues = (evaluator_summary or {}).get("issues") or []
    diag_anomalies = ((diagnostics_summary or {}).get("diagnostics") or {}).get("anomalies") or []

    issue_counts: Dict[str, int] = {}
    for issue in eval_issues:
        if isinstance(issue, str):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    for anomaly in diag_anomalies:
        if isinstance(anomaly, str):
            issue_counts[anomaly] = issue_counts.get(anomaly, 0) + 1

    for label, freq in issue_counts.items():
        clusters.append({"label": label, "members": [label], "frequency": freq})

    # Determine new anomalies by comparing against recent history
    historical = set()
    for entry in recent_history or []:
        hist_issues = (entry.get("payload") or {}).get("evaluator", {}).get("issues") or []
        hist_anomalies = ((entry.get("payload") or {}).get("diagnostics") or {}).get("anomalies") or []
        for item in hist_issues + hist_anomalies:
            if isinstance(item, str):
                historical.add(item)

    for anomaly in diag_anomalies:
        if isinstance(anomaly, str) and anomaly not in historical:
            new_anomalies.append(anomaly)

    # Simple regression detection: issues repeating more than once recently
    for label, freq in issue_counts.items():
        if freq > 1:
            regressions.append(label)

    return {
        "clusters": clusters,
        "new_anomalies": new_anomalies,
        "regressions": regressions,
    }
