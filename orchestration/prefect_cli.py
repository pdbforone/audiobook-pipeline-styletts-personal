from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

try:
    from orchestration.prefect_flows import (
        tts_pipeline_batch_flow,
        tts_pipeline_flow,
    )
except Exception as exc:  # pragma: no cover - CLI guard
    print(f"Error importing Prefect flows: {exc}", file=sys.stderr)
    print("Ensure Prefect and orchestration.prefect_flows are installed.", file=sys.stderr)
    sys.exit(2)


def _validate_paths(paths: List[str]) -> List[str]:
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        for path in missing:
            print(f"Missing pipeline file: {path}", file=sys.stderr)
        sys.exit(1)
    return paths


def cmd_run(args: argparse.Namespace) -> int:
    pipeline = _validate_paths([args.pipeline])[0]
    try:
        result = tts_pipeline_flow(
            pipeline_path=pipeline,
            use_policy_engine=not args.no_policy,
        )
    except Exception as exc:
        print(f"Flow execution failed: {exc}", file=sys.stderr)
        return 1

    print("Prefect flow result:")
    print(result)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    pipelines = _validate_paths(args.pipelines)
    try:
        result = tts_pipeline_batch_flow(
            pipeline_paths=pipelines,
            use_policy_engine=not args.no_policy,
        )
    except Exception as exc:
        print(f"Batch flow failed: {exc}", file=sys.stderr)
        return 1

    print("Batch results:")
    print(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prefect CLI wrapper for the audiobook pipeline (local only)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run a single pipeline.json/book file")
    run_cmd.add_argument(
        "--pipeline",
        required=True,
        help="Path to the pipeline input (e.g., input/book.pdf)",
    )
    run_cmd.add_argument(
        "--no-policy",
        action="store_true",
        help="Disable PolicyEngine integration for this run",
    )
    run_cmd.set_defaults(func=cmd_run)

    batch_cmd = sub.add_parser("batch", help="Run multiple pipelines sequentially")
    batch_cmd.add_argument(
        "--pipelines",
        nargs="+",
        required=True,
        help="List of pipeline inputs (e.g., input/book1.pdf input/book2.pdf)",
    )
    batch_cmd.add_argument(
        "--no-policy",
        action="store_true",
        help="Disable PolicyEngine integration for this batch",
    )
    batch_cmd.set_defaults(func=cmd_batch)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
