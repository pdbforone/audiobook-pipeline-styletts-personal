"""Schema version registry for key artifacts (Phase V, opt-in)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class SchemaVersionInfo:
    name: str
    current_version: str
    supported_versions: Dict[str, str]  # version -> notes


SCHEMAS: Dict[str, SchemaVersionInfo] = {
    "pipeline_state": SchemaVersionInfo(
        name="pipeline_state",
        current_version="1.0.0",
        supported_versions={
            "1.0.0": "Current pipeline.json schema",
            "0.9.0": "Legacy verification_pipeline.json structure",
        },
    ),
    "policy_logs": SchemaVersionInfo(
        name="policy_logs",
        current_version="1.0.0",
        supported_versions={
            "1.0.0": "Policy logs with per-run summaries",
            "0.9.0": "Basic policy log entries",
        },
    ),
    "stability_profiles": SchemaVersionInfo(
        name="stability_profiles",
        current_version="1.0.0",
        supported_versions={
            "1.0.0": "Profiles with stability metrics",
            "0.8.0": "Early stability snapshot format",
        },
    ),
    "memory": SchemaVersionInfo(
        name="memory",
        current_version="1.0.0",
        supported_versions={
            "1.0.0": "Memory summaries with recency weighting",
            "0.9.0": "Legacy memory snapshots",
        },
    ),
    "self_eval": SchemaVersionInfo(
        name="self_eval",
        current_version="1.0.0",
        supported_versions={
            "1.0.0": "Phase Q self-eval reports",
            "0.9.0": "Initial self-eval summaries",
        },
    ),
    "research": SchemaVersionInfo(
        name="research",
        current_version="1.0.0",
        supported_versions={
            "1.0.0": "Phase P/R research reports",
            "0.9.0": "Early research evidence bundles",
        },
    ),
}


def get_schema_info(name: str) -> Optional[SchemaVersionInfo]:
    """Return schema version info for a given name, if known."""
    return SCHEMAS.get(name)
