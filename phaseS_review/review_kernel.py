"""Phase S: review kernel (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, List


def _clamp(val: float) -> float:
    try:
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return 0.0


def review_run(run_summary: Dict) -> Dict:
    """
    Produce a lightweight review of a run.
    Schema:
    {
      "signals": { "coherence": float, "stability": float, "quality": float },
      "issues": [...],
      "confidence": float,
      "notes": "..."
    }
    """
    summary = run_summary or {}
    signals = {
        "coherence": _clamp(summary.get("coherence", 0.75)),
        "stability": _clamp(summary.get("stability", 0.75)),
        "quality": _clamp(summary.get("quality", 0.75)),
    }

    issues: List[str] = []
    if signals["stability"] < 0.5:
        issues.append("stability_low")
    if signals["coherence"] < 0.5:
        issues.append("coherence_low")
    if signals["quality"] < 0.5:
        issues.append("quality_low")

    confidence = sum(signals.values()) / (3.0)
    notes = "Informational review (Phase S, opt-in only)."

    return {
        "signals": signals,
        "issues": issues,
        "confidence": _clamp(confidence),
        "notes": notes,
    }
