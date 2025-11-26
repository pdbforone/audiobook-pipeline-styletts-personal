"""
Stability bounds enforcement for Phase J (opt-in, additive-only).
"""

from __future__ import annotations

from typing import Any, Dict, List


def _within_pct(value: Any, bound: float) -> bool:
    try:
        return abs(float(value)) <= float(bound)
    except Exception:
        return True


def check_stability_bounds(overrides: Dict[str, Any], trends: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """
    Returns:
    {
      "valid": bool,
      "filtered_overrides": dict,
      "violations": list[str]
    }
    """
    if not overrides:
        return {"valid": True, "filtered_overrides": {}, "violations": []}

    bounds = getattr(config, "stability_bounds", None)
    enabled = getattr(bounds, "enable", False) if bounds else False
    if not enabled:
        return {"valid": True, "filtered_overrides": overrides, "violations": []}

    max_chunk_delta = getattr(bounds, "max_chunk_delta_pct", 0) or 0
    max_engine_switches = getattr(bounds, "max_engine_switches", 0) or 0
    max_rewrite_delta = getattr(bounds, "max_rewrite_delta_pct", 0) or 0

    filtered: Dict[str, Any] = {}
    violations: List[str] = []

    for key, value in overrides.items():
        if key in ("chunk_size", "phase3.chunk_size"):
            delta = None
            if isinstance(value, dict):
                delta = value.get("delta_percent") or value.get("value") or value.get("delta")
            if delta is not None and not _within_pct(delta, max_chunk_delta):
                violations.append("chunk_size_delta_exceeds_bounds")
                continue
        if key in ("engine_preference", "phase4.engine_preference"):
            if max_engine_switches == 0:
                violations.append("engine_switch_not_allowed")
                continue
        if key in ("rewrite_policy", "rewriter.default_policy"):
            delta = None
            if isinstance(value, dict):
                delta = value.get("delta_percent") or value.get("value")
            if delta is not None and not _within_pct(delta, max_rewrite_delta):
                violations.append("rewrite_policy_delta_exceeds_bounds")
                continue

        filtered[key] = value

    return {
        "valid": not violations,
        "filtered_overrides": filtered,
        "violations": violations,
    }
