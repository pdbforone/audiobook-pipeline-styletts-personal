"""
Strict autonomy policy limits (opt-in).
"""

from __future__ import annotations

from typing import Any, Dict

AUTONOMY_POLICY = {
    "allowed_fields": [
        "phase3.chunk_size",
        "phase4.engine_preference",
        "rewriter.default_policy",
        "rewrite_policy",
    ],
    "bounds": {
        "phase3.chunk_size": {
            "min_percent_delta": -10,
            "max_percent_delta": 10,
        },
        "phase4.engine_preference": {
            "allowed_engines": ["xtts", "kokoro"],
        },
    },
}


def check_policy(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that recommended changes fall within policy limits.
    Returns a filtered version of the recommendation or {} if invalid.
    """
    if not recommendation:
        return {}

    filtered = {}
    allowed = set(AUTONOMY_POLICY["allowed_fields"])
    bounds = AUTONOMY_POLICY.get("bounds", {})

    for key, value in (recommendation or {}).items():
        if key not in allowed:
            continue
        if key == "phase3.chunk_size":
            delta = value.get("delta_percent") if isinstance(value, dict) else None
            try:
                delta_val = float(delta)
            except (TypeError, ValueError):
                continue
            lo = bounds["phase3.chunk_size"]["min_percent_delta"]
            hi = bounds["phase3.chunk_size"]["max_percent_delta"]
            if delta_val < lo or delta_val > hi:
                continue
            filtered[key] = value
        elif key == "phase4.engine_preference":
            engine = value.get("preferred") if isinstance(value, dict) else None
            if engine in bounds["phase4.engine_preference"]["allowed_engines"]:
                filtered[key] = value
        elif key == "rewriter.default_policy":
            filtered[key] = value
        elif key == "rewrite_policy":
            filtered[key] = value

    return filtered
