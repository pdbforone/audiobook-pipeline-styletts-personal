"""Integrity kernel for Phase U (opt-in, read-only)."""

from __future__ import annotations

from typing import Any, Dict, List


def _clamp(val: Any) -> float:
    try:
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return 0.0


def evaluate_integrity(
    run_summary: Dict | None,
    readiness: Dict | None,
    stability: Dict | None,
    drift: Dict | None,
    self_eval: Dict | None,
    retrospection: Dict | None,
    review: Dict | None,
    audit: Dict | None,
) -> Dict:
    """
    Compute a unified integrity view.
    Schema:
    {
      "integrity_rating": float (0–1),
      "dimensions": {
        "readiness": float,
        "stability": float,
        "drift": float,
        "self_eval": float,
        "retrospection": float,
        "review": float,
        "audit": float
      },
      "issues": [...],
      "notes": "string"
    }
    """
    dims = {
        "readiness": _clamp((readiness or {}).get("score", 0.5)),
        "stability": _clamp((stability or {}).get("score", 0.5)),
        "drift": _clamp((drift or {}).get("drift_score", 0.5)),
        "self_eval": _clamp((self_eval or {}).get("overall_rating", 0.5)),
        "retrospection": _clamp((retrospection or {}).get("integrity", 0.5)),
        "review": _clamp((review or {}).get("confidence", 0.5)),
        "audit": _clamp((audit or {}).get("confidence", 0.5)),
    }
    integrity_rating = sum(dims.values()) / len(dims)
    issues: List[str] = []
    for name, val in dims.items():
        if val < 0.3:
            issues.append(f"{name}_low")
    notes = "Unified integrity evaluation (Phase U, opt-in; no runtime impact)."
    return {
        "integrity_rating": _clamp(integrity_rating),
        "dimensions": dims,
        "issues": issues,
        "notes": notes,
    }
