"""
Phase AB classifier: derive a unified assessment from fused signals.
"""

from __future__ import annotations

from typing import Any, Dict


def classify_state(fused: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a bounded assessment with score, classification, confidence, and notes.
    """
    total_sources = len(fused) if fused else 1
    positive = 0
    notes = []

    for key, value in (fused or {}).items():
        if isinstance(value, dict) and value:
            positive += 1
        elif value:
            positive += 0.5
        else:
            notes.append(f"{key}: missing")

    score = min(1.0, max(0.0, positive / total_sources))
    if score >= 0.7:
        classification = "healthy"
    elif score >= 0.4:
        classification = "caution"
    else:
        classification = "unstable"

    confidence = min(1.0, max(0.1, score))

    return {
        "score": float(score),
        "classification": classification,
        "confidence": float(confidence),
        "notes": "; ".join(notes) if notes else "Signals aggregated successfully.",
    }
