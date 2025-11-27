"""Conflict resolver for Phase AC (safety-first, conservative)."""

from __future__ import annotations

from typing import Dict, Any, List


def resolve_conflicts(merged: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve conflicts with safety-first precedence.
    - safety overrides others
    - supervised before autonomous
    - most conservative wins (False over True where applicable)
    Annotates decisions in 'conflicts_resolved'.
    """
    resolved = dict(merged or {})
    decisions: List[Dict[str, Any]] = []
    merged_view = resolved.get("merged_view") or {}
    conflicts = resolved.get("conflicts") or []
    for conflict in conflicts:
        field = conflict.get("field")
        existing = conflict.get("existing")
        new = conflict.get("new")
        decision = existing
        # safety-first: prefer False over True when boolean
        if isinstance(existing, bool) and isinstance(new, bool):
            decision = existing and new  # False if any False
        merged_view[field] = decision
        decisions.append({"field": field, "decision": decision, "reason": "safety_first"})
    resolved["merged_view"] = merged_view
    resolved["conflicts_resolved"] = decisions
    return resolved
