#!/usr/bin/env python3
"""
Simple smoke test for Phase 4 TTS.

This mirrors the legacy command used throughout the orchestration diagnostics
so tooling such as ``trace_execution.py`` can still introspect a concrete
example.  By default the script only prints the command it would execute;
pass ``--run`` to actually synthesize ``chunk_0.wav`` using the Phase 4
environment.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PHASE4_ROOT = Path(__file__).resolve().parent
DEFAULT_PIPELINE = (PHASE4_ROOT.parent / "pipeline.json").resolve()


def build_command(
    file_id: str = "TEST_SIMPLE",
    chunk_id: int = 0,
    pipeline_json: Path = DEFAULT_PIPELINE,
    engine: str = "kokoro",
) -> list[str]:
    """Construct the legacy Phase 4 test command."""
    cmd = [
        "conda",
        "run",
        "-n",
        "phase4_tts",
        "--no-capture-output",
        "python",
        "src/main_multi_engine.py",
        f"--chunk_id={chunk_id}",
        f"--file_id={file_id}",
        f"--json_path={pipeline_json}",
        f"--engine={engine}",
    ]
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4 quick sanity check.")
    parser.add_argument("--file-id", default="TEST_SIMPLE", help="Pipeline file identifier.")
    parser.add_argument("--chunk-id", type=int, default=0, help="Chunk index to synthesize.")
    parser.add_argument(
        "--pipeline-json",
        type=Path,
        default=DEFAULT_PIPELINE,
        help="Path to pipeline.json (defaults to repo root).",
    )
    parser.add_argument(
        "--engine",
        default="kokoro",
        choices=["f5", "xtts", "kokoro"],
        help="Engine to request (multi-engine CLI will auto-fallback).",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the command instead of printing it.",
    )
    args = parser.parse_args()

    cmd = build_command(
        file_id=args.file_id,
        chunk_id=args.chunk_id,
        pipeline_json=args.pipeline_json.resolve(),
        engine=args.engine,
    )

    print("Phase 4 test command:\n")
    print(" \\\n".join(f"  {part}" for part in cmd))
    print()

    if not args.run:
        print("Dry run only. Pass --run to execute.")
        return 0

    print("Running test command...\n")
    try:
        subprocess.run(cmd, cwd=PHASE4_ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"❌ Command failed with exit code {exc.returncode}")
        return exc.returncode

    print("✅ Test command completed. Check audio_chunks/chunk_0.wav for output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
