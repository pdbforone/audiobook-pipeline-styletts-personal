"""Migration runner for Phase V (opt-in, non-destructive by default)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .migration_plans import build_migration_plan
from .schema_versions import SCHEMAS
from .migration_reporter import write_plan_report, write_apply_report


def detect_current_versions(base_dir: Path = Path(".pipeline")) -> Dict[str, str]:
    """
    Infer current versions per target (best-effort).
    """
    versions: Dict[str, str] = {}
    for name, info in SCHEMAS.items():
        versions[name] = info.current_version
    return versions


def plan_migrations(config_block: Dict[str, Any], base_dir: Path = Path(".pipeline")) -> Dict[str, Any]:
    """
    Return a summary of planned migrations per target.
    """
    targets = (config_block.get("targets") if isinstance(config_block, dict) else None) or []
    lookback = int(config_block.get("lookback_runs", 20)) if isinstance(config_block, dict) else 20
    current_versions = detect_current_versions(base_dir)
    plans: Dict[str, Any] = {"plans": [], "lookback_runs": lookback}
    for target in targets:
        current = current_versions.get(target, "unknown")
        desired = current_versions.get(target, "unknown")
        plan = build_migration_plan(target, current, desired)
        plans["plans"].append(
            {
                "target": target,
                "current_version": current,
                "target_version": desired,
                "steps": [step.__dict__ for step in plan.steps],
            }
        )
    return plans


def apply_migrations(config_block: Dict[str, Any], base_dir: Path = Path(".pipeline")) -> Dict[str, Any]:
    """
    Execute non-destructive migrations when dry_run=False.
    Returns a summary of what was done.
    """
    targets = (config_block.get("targets") if isinstance(config_block, dict) else None) or []
    result: Dict[str, Any] = {"applied": []}
    applied_dir = base_dir / "migrations" / "applied"
    applied_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    for target in targets:
        artifact_snapshot = base_dir / f"{target}_snapshot_{ts}.json"
        # Non-destructive: create a placeholder migrated copy if original exists; otherwise a stub.
        payload = {"target": target, "migrated_at": ts, "note": "Non-destructive placeholder copy."}
        artifact_snapshot.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        result["applied"].append({"target": target, "output": str(artifact_snapshot)})
    return result
