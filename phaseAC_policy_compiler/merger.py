"""Policy merger for Phase AC (non-destructive)."""

from __future__ import annotations

from typing import Dict, Any, List


def merge_policies(policy_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple policy blocks non-destructively.
    Conflicts are recorded; no fields are deleted.
    """
    merged: Dict[str, Any] = {"policies": [], "conflicts": []}
    seen_keys: Dict[str, Any] = {}
    for block in policy_blocks or []:
        merged["policies"].append(block)
        if not isinstance(block, dict):
            continue
        for key, value in block.items():
            if key in seen_keys and seen_keys[key] != value:
                merged["conflicts"].append({"field": key, "existing": seen_keys[key], "new": value})
            else:
                seen_keys[key] = value
    merged["merged_view"] = seen_keys
    return merged
