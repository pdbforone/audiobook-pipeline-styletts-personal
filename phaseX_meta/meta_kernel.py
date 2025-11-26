"""Meta kernel for Phase X (opt-in, read-only)."""

from __future__ import annotations

from typing import Any, Dict


def _clamp(val: Any) -> float:
    try:
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return 0.0


def evaluate_signal_layers(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate self_eval (Q), retro (R), and review (S) layers.

    Returns schema:
    {
      "layers": {
         "self_eval": {...},
         "retro": {...},
         "review": {...}
      },
      "meta_dimensions": {
         "coherence": float,
         "consistency": float,
         "stability": float,
         "quality": float
      },
      "overall_meta_score": float,
      "notes": str
    }
    """
    layers = {
        "self_eval": (inputs or {}).get("self_eval", {}) if isinstance(inputs, dict) else {},
        "retro": (inputs or {}).get("retro", {}) if isinstance(inputs, dict) else {},
        "review": (inputs or {}).get("review", {}) if isinstance(inputs, dict) else {},
    }
    meta_dimensions = {
        "coherence": _clamp(layers["self_eval"].get("coherence", 0.5)),
        "consistency": _clamp(layers["retro"].get("consistency", 0.5)),
        "stability": _clamp(layers["review"].get("stability", 0.5)),
        "quality": _clamp(layers["self_eval"].get("quality", 0.5)),
    }
    overall_meta_score = sum(meta_dimensions.values()) / len(meta_dimensions)
    return {
        "layers": layers,
        "meta_dimensions": meta_dimensions,
        "overall_meta_score": overall_meta_score,
        "notes": "Phase X meta-evaluation (informational only).",
    }
