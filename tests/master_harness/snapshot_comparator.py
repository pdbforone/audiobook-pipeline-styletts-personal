"""Snapshot comparator for master test harness (Phase V harness)."""

from __future__ import annotations

from typing import Dict, Any


def compare_snapshots(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two snapshot dictionaries and surface key consistency signals.
    """
    differences = {}
    before_keys = set(before.keys())
    after_keys = set(after.keys())
    missing_in_after = before_keys - after_keys
    new_in_after = after_keys - before_keys
    if missing_in_after:
        differences["missing_in_after"] = sorted(missing_in_after)
    if new_in_after:
        differences["new_in_after"] = sorted(new_in_after)

    engine_consistency = before.get("engine") == after.get("engine")
    chunk_consistency = before.get("chunk_count") == after.get("chunk_count")

    phase_presence = {
        "before_phases": sorted(before.get("phases", [])) if isinstance(before.get("phases"), list) else [],
        "after_phases": sorted(after.get("phases", [])) if isinstance(after.get("phases"), list) else [],
    }

    schema_valid = not differences

    return {
        "schema_valid": schema_valid,
        "differences": differences,
        "phase_presence": phase_presence,
        "engine_consistency": engine_consistency,
        "chunk_consistency": chunk_consistency,
    }


def assert_consistency(snapshot: Dict[str, Any]) -> None:
    """
    Basic schema assertions for a single snapshot.
    """
    required_top = {"phases", "engine", "chunk_count"}
    if not required_top.issubset(snapshot.keys()):
        missing = required_top - set(snapshot.keys())
        raise AssertionError(f"Missing required keys in snapshot: {missing}")
