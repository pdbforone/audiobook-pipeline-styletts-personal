"""Phase Q: cross-phase fusion (read-only, opt-in)."""

from __future__ import annotations

from typing import Dict


def _clamp(val: float) -> float:
    try:
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return 0.0


def fuse_phase_outputs(phase_outputs: Dict) -> Dict:
    """
    Return:
    {
      "signals": {
        "phase_success": float,
        "consistency": float,
        "llm_quality": float,
        "chunk_flow": float
      },
      "summary": str
    }
    """
    outputs = phase_outputs or {}
    signals = {
        "phase_success": _clamp(outputs.get("phase_success", 0.8)),
        "consistency": _clamp(outputs.get("consistency", 0.75)),
        "llm_quality": _clamp(outputs.get("llm_quality", 0.7)),
        "chunk_flow": _clamp(outputs.get("chunk_flow", 0.7)),
    }
    summary = "Fused signals across phases; informational only."
    return {"signals": signals, "summary": summary}
