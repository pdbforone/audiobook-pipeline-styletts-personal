"""Consistency unifier for Phase U (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, List


def unify(signals: Dict, integrity: Dict) -> dict:
    """
    Return schema:
    {
      "run_id": "...",
      "summary": {
        "integrity_rating": float,
        "critical_issues": [...],
        "warnings": [...],
        "notes": "..."
      },
      "signals": signals,
      "integrity": integrity
    }
    """
    run_id = signals.get("run_id") if isinstance(signals, dict) else None
    integrity_rating = float((integrity or {}).get("integrity_rating", 0.0))
    issues = (integrity or {}).get("issues", [])
    critical_issues: List[str] = [i for i in issues if isinstance(i, str) and "low" in i]
    warnings: List[str] = []
    if integrity_rating < 0.5:
        warnings.append("integrity_below_threshold")
    summary = {
        "integrity_rating": integrity_rating,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "notes": "Unified consistency summary (Phase U, read-only).",
    }
    return {
        "run_id": run_id,
        "summary": summary,
        "signals": signals,
        "integrity": integrity,
    }
