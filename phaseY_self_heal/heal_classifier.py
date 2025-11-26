"""Self-heal classifier for Phase Y (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any


def classify(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify heal signals.
    Output schema:
    {
      "class": "structural|metadata|tts|planner|unknown",
      "explanation": str,
      "confidence": float,
      "related_fields": [...]
    }
    """
    sig = signals or {}
    sev = (sig.get("signals") or {}).get("severity") if isinstance(sig, dict) else None
    cls = "unknown"
    if sev == "high":
        cls = "structural"
    elif sev == "med":
        cls = "metadata"
    explanation = "Heuristic classification (non-destructive)."
    confidence = float((sig.get("signals") or {}).get("confidence", 0.5)) if isinstance(sig, dict) else 0.0
    related_fields = list((sig.get("failures") or {}).keys()) if isinstance(sig.get("failures"), dict) else []
    return {
        "class": cls,
        "explanation": explanation,
        "confidence": confidence,
        "related_fields": related_fields,
    }
