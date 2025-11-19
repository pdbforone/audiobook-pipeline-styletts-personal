"""Utilities for adapting legacy pipeline.json files to the canonical schema."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from .schema import (
    CANONICAL_SCHEMA_VERSION,
    PHASE_KEYS,
    canonicalize_state,
    validate_pipeline_schema,
)
from .state_manager import PipelineState, StateError


def adapt_payload(payload: Dict[str, Any], *, touch_timestamps: bool = True) -> Dict[str, Any]:
    """Return a normalized copy of a legacy pipeline payload."""
    normalized = canonicalize_state(
        payload,
        schema_version=CANONICAL_SCHEMA_VERSION,
        touch_timestamps=touch_timestamps,
    )
    validate_pipeline_schema(normalized)
    return normalized


def upgrade_pipeline_file(
    path: Path,
    *,
    dry_run: bool = False,
    touch_timestamps: bool = True,
) -> Dict[str, Any]:
    """Normalize a pipeline.json file in-place (writes are transactional)."""
    state = PipelineState(path, validate_on_read=False)
    try:
        current = state.read(validate=False)
    except StateError:
        current = {}

    upgraded = adapt_payload(current, touch_timestamps=touch_timestamps)
    if dry_run:
        return upgraded

    state.write(upgraded, validate=True)
    return upgraded


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Upgrade pipeline.json to the canonical schema.",
    )
    parser.add_argument(
        "--pipeline",
        type=Path,
        default=Path("pipeline.json"),
        help="Path to pipeline.json (default: ./pipeline.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Normalize in-memory and print a summary without writing.",
    )
    parser.add_argument(
        "--no-touch-timestamps",
        action="store_true",
        help="Preserve existing created_at/last_updated values.",
    )
    args = parser.parse_args()

    upgraded = upgrade_pipeline_file(
        args.pipeline,
        dry_run=args.dry_run,
        touch_timestamps=not args.no_touch_timestamps,
    )
    phase_count = sum(1 for phase in PHASE_KEYS if upgraded.get(phase))
    batch_runs = len(upgraded.get("batch_runs", []))
    mode = "DRY-RUN" if args.dry_run else "UPDATED"
    print(
        f"[{mode}] {args.pipeline} -> schema {CANONICAL_SCHEMA_VERSION} "
        f"({phase_count} populated phases, {batch_runs} batch runs)"
    )


if __name__ == "__main__":  # pragma: no cover - CLI convenience
    _cli()
