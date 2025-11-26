"""Phase Q: rating explainer (textual, non-intrusive)."""

from __future__ import annotations

from typing import Dict


def explain_rating(dimensions: Dict[str, float], overall: float) -> Dict:
    """
    Return:
    {
      "explanation": "...",
      "dimension_breakdown": {
        "coherence": "...",
        "alignment": "...",
        "stability": "...",
        "efficiency": "..."
      }
    }
    """
    dims = dimensions or {}
    explanation = f"Overall rating {overall:.2f} derived from coherence, alignment, stability, and efficiency."
    breakdown = {
        "coherence": f"Coherence score {dims.get('coherence', 0.0):.2f}",
        "alignment": f"Alignment score {dims.get('alignment', 0.0):.2f}",
        "stability": f"Stability score {dims.get('stability', 0.0):.2f}",
        "efficiency": f"Efficiency score {dims.get('efficiency', 0.0):.2f}",
    }
    return {"explanation": explanation, "dimension_breakdown": breakdown}
