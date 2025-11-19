#!/usr/bin/env python3
"""
Phase 7: Batch orchestrator CLI.
Delegates all batch work to the Trio-based runner that calls Phase 6 per file.
"""

from __future__ import annotations

import argparse
import sys

import trio

from .main import load_config, main_async, setup_logging
from .models import BatchConfig


def _positive_int(value: str) -> int:
    ivalue = int(value)
    if ivalue < 1:
        raise argparse.ArgumentTypeError("Value must be >= 1")
    return ivalue


def _cpu_percent(value: str) -> float:
    fvalue = float(value)
    if not 0 <= fvalue <= 100:
        raise argparse.ArgumentTypeError("CPU threshold must be between 0 and 100")
    return fvalue


def _non_negative_float(value: str) -> float:
    fvalue = float(value)
    if fvalue < 0:
        raise argparse.ArgumentTypeError("Value must be >= 0")
    return fvalue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 7 batch driver (Phase 6 orchestrator wrapper)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--input-dir", help="Input directory of files to process")
    parser.add_argument("--pipeline-json", help="Path to pipeline.json")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--log-file", help="Log file location")
    parser.add_argument("--max-workers", type=_positive_int, help="Max concurrent files")
    parser.add_argument("--cpu-threshold", type=_cpu_percent, help="CPU percent before throttling")
    parser.add_argument("--throttle-delay", type=_non_negative_float, help="Seconds to sleep when throttled")
    resume_group = parser.add_mutually_exclusive_group()
    resume_group.add_argument("--resume", dest="resume", action="store_true", help="Enable resume (skip completed)")
    resume_group.add_argument("--no-resume", dest="resume", action="store_false", help="Disable resume")
    parser.add_argument("--dry-run", action="store_true", help="List work without invoking Phase 6")
    parser.add_argument("--batch-size", type=_positive_int, help="Limit number of files processed")
    parser.add_argument("--phases", nargs="+", type=int, help="Phases to run (passed to Phase 6)")
    parser.add_argument("--phase-timeout", type=_positive_int, help="Per-phase timeout (forwarded downstream)")
    parser.set_defaults(resume=None)
    return parser


def apply_overrides(config: BatchConfig, args: argparse.Namespace) -> BatchConfig:
    updates = {}
    if args.input_dir:
        updates["input_dir"] = args.input_dir
    if args.pipeline_json:
        updates["pipeline_json"] = args.pipeline_json
    if args.log_level:
        updates["log_level"] = args.log_level
    if args.log_file:
        updates["log_file"] = args.log_file
    if args.max_workers is not None:
        updates["max_workers"] = args.max_workers
    if args.cpu_threshold is not None:
        updates["cpu_threshold"] = args.cpu_threshold
    if args.throttle_delay is not None:
        updates["throttle_delay"] = args.throttle_delay
    if args.resume is not None:
        updates["resume"] = args.resume
    if args.dry_run:
        updates["dry_run"] = True
    if args.batch_size is not None:
        updates["batch_size"] = args.batch_size
    if args.phases:
        updates["phases"] = args.phases
    if args.phase_timeout is not None:
        updates["phase_timeout"] = args.phase_timeout

    return config.model_copy(update=updates)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    config = apply_overrides(config, args)

    setup_logging(config)

    try:
        return trio.run(main_async, config)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

