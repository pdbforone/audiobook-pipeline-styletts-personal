"""Audit kernel for Phase T (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, List


def _clamp(val: float) -> float:
    try:
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return 0.0


def evaluate_run(run_summary: Dict, signals: Dict) -> Dict:
    """
    Return schema:
    {
      "dimensions": {
        "tts_quality": float,
        "chunk_flow": float,
        "reasoning_clarity": float,
        "engine_stability": float
      },
      "issues": [str],
      "confidence": float,
      "notes": str
    }
    """
    summary = run_summary or {}
    sig = signals or {}
    dims = {
        "tts_quality": _clamp(sig.get("tts_quality", summary.get("tts_quality", 0.75))),
        "chunk_flow": _clamp(sig.get("chunk_flow", summary.get("chunk_flow", 0.75))),
        "reasoning_clarity": _clamp(sig.get("reasoning_clarity", summary.get("reasoning_clarity", 0.75))),
        "engine_stability": _clamp(sig.get("engine_stability", summary.get("engine_stability", 0.75))),
    }
    issues: List[str] = []
    for name, value in dims.items():
        if value < 0.4:
            issues.append(f"{name}_low")
    confidence = sum(dims.values()) / 4.0
    notes = "Phase T audit kernel (informational only)."
    return {
        "dimensions": dims,
        "issues": issues,
        "confidence": _clamp(confidence),
        "notes": notes,
    }
