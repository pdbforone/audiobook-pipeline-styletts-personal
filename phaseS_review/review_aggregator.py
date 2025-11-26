"""Phase S: cross-run review aggregator (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, List


def aggregate_reviews(review_outputs: List[Dict]) -> Dict:
    """
    Aggregates multiple review outputs.
    Schema:
    {
      "aggregate_rating": float,
      "dimensions": { ... },
      "outliers": [...],
      "notes": "..."
    }
    """
    reviews = review_outputs or []
    if not reviews:
        return {"aggregate_rating": 0.0, "dimensions": {}, "outliers": [], "notes": "No reviews provided."}

    dims_sum: Dict[str, float] = {}
    count = 0
    outliers: List[Dict] = []

    for rev in reviews:
        signals = rev.get("signals") or {}
        if signals:
            count += 1
            for k, v in signals.items():
                dims_sum[k] = dims_sum.get(k, 0.0) + float(v)
            if any(float(v) < 0.3 for v in signals.values()):
                outliers.append(rev)

    dimensions = {k: (v / count) if count else 0.0 for k, v in dims_sum.items()}
    aggregate_rating = sum(dimensions.values()) / len(dimensions) if dimensions else 0.0

    return {
        "aggregate_rating": aggregate_rating,
        "dimensions": dimensions,
        "outliers": outliers,
        "notes": "Informational aggregate (Phase S, opt-in only).",
    }
