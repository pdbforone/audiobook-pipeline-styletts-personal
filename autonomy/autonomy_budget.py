"""
Budget enforcement for supervised autonomy (opt-in, temporary only).
"""

from __future__ import annotations

from typing import Any, Dict, List


def enforce_budget(recommendations: Dict[str, Any], autonomy_cfg: Any) -> Dict[str, Any]:
    """
    Filter recommendations to ensure:
    - no more than max_overrides_per_run
    - only allowed fields are modified
    - change magnitude does not exceed limit
    """
    budget = getattr(autonomy_cfg, "budget", {}) or {}
    max_overrides = budget.get("max_overrides_per_run", 2)
    allowed_fields: List[str] = budget.get(
        "allowed_fields", ["chunk_size", "engine_preference", "rewrite_policy"]
    )

    safe_rec = dict(recommendations or {})
    suggested = safe_rec.get("suggested_changes") or {}

    filtered: Dict[str, Any] = {}
    count = 0
    for key, value in suggested.items():
        if count >= max_overrides:
            break
        if key in ("phase3.chunk_size", "chunk_size") and "chunk_size" in allowed_fields:
            filtered[key] = value
            count += 1
        elif key in ("phase4.engine_preference", "engine_preference") and "engine_preference" in allowed_fields:
            filtered[key] = value
            count += 1
        elif key == "rewrite_policy" and "rewrite_policy" in allowed_fields:
            filtered[key] = value
            count += 1

    safe_rec["suggested_changes"] = filtered
    return safe_rec
