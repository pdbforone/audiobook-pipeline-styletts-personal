"""Meta fusion for Phase X (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any, List


def fuse_meta_context(kernel_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fuse meta-evaluation context.

    Returns:
    {
      "signals": {
         "meta_score": float,
         "weak_dimensions": [...],
         "strong_dimensions": [...]
      },
      "summary": {
         "coherence": float,
         "consistency": float,
         "stability": float,
         "quality": float
      }
    }
    """
    dims = (kernel_output or {}).get("meta_dimensions") or {}
    meta_score = float((kernel_output or {}).get("overall_meta_score", 0.0))
    weak: List[str] = [k for k, v in dims.items() if isinstance(v, (int, float)) and v < 0.4]
    strong: List[str] = [k for k, v in dims.items() if isinstance(v, (int, float)) and v >= 0.7]
    return {
        "signals": {
            "meta_score": meta_score,
            "weak_dimensions": weak,
            "strong_dimensions": strong,
        },
        "summary": {
            "coherence": float(dims.get("coherence", 0.0)),
            "consistency": float(dims.get("consistency", 0.0)),
            "stability": float(dims.get("stability", 0.0)),
            "quality": float(dims.get("quality", 0.0)),
        },
    }
