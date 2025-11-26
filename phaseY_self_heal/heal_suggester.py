"""Self-heal suggester for Phase Y (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any, List


def suggest_corrections(run_summary: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suggest non-destructive corrections. Does NOT apply anything.
    Output schema:
    {
      "suggestions": [
        { "type": "...", "field": "...", "recommended_value": "...", "confidence": float }
      ],
      "notes": str
    }
    """
    suggestions: List[Dict[str, Any]] = []
    related = classification.get("related_fields") if isinstance(classification, dict) else []
    if related:
        for field in related:
            suggestions.append(
                {
                    "type": classification.get("class", "unknown"),
                    "field": field,
                    "recommended_value": "review_required",
                    "confidence": float(classification.get("confidence", 0.5)),
                }
            )
    notes = "Informational suggestions only; no automatic changes."
    return {"suggestions": suggestions, "notes": notes}
