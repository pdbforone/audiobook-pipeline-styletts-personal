"""Migration plan definitions for Phase V (opt-in, non-destructive)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class MigrationStep:
    id: str
    from_version: str
    to_version: str
    description: str


@dataclass
class MigrationPlan:
    target: str  # e.g. "pipeline_state"
    current_version: str
    target_version: str
    steps: List[MigrationStep]


def build_migration_plan(target: str, current_version: str, desired_version: str) -> MigrationPlan:
    """
    Build a logical migration plan. Currently, most migrations are no-op but explicit.
    """
    steps: List[MigrationStep] = []
    if current_version == desired_version:
        steps.append(
            MigrationStep(
                id=f"{target}-noop",
                from_version=current_version,
                to_version=desired_version,
                description="No migration needed; already at desired version.",
            )
        )
    else:
        steps.append(
            MigrationStep(
                id=f"{target}-{current_version}-to-{desired_version}",
                from_version=current_version,
                to_version=desired_version,
                description="Upgrade artifact schema non-destructively.",
            )
        )
    return MigrationPlan(
        target=target,
        current_version=current_version,
        target_version=desired_version,
        steps=steps,
    )
