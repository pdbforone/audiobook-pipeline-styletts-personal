"""Risk classifier for Phase T (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict


def classify(evaluation_output: Dict) -> Dict:
    """
    Return schema:
    {
      "risk_level": "low" | "medium" | "high",
      "signals": {
        "tts": str,
        "engine": str,
        "chunking": str,
        "llm": str
      },
      "confidence": float,
      "notes": str
    }
    """
    ev = evaluation_output or {}
    conf = float(ev.get("combined_confidence", 0.0))
    risk_level = "low"
    if conf < 0.4:
        risk_level = "medium"
    if conf < 0.2:
        risk_level = "high"

    signals = {
        "tts": "ok",
        "engine": "ok",
        "chunking": "ok",
        "llm": "ok",
    }
    if risk_level == "high":
        signals = {k: "risk" for k in signals}
    elif risk_level == "medium":
        signals = {k: "watch" for k in signals}

    return {
        "risk_level": risk_level,
        "signals": signals,
        "confidence": conf,
        "notes": "Heuristic, informational-only risk classifier.",
    }
