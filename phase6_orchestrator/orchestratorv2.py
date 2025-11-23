#!/usr/bin/env python3
"""
Phase 6: Single-File Orchestrator
Simplified version - runs phases 1-5 sequentially for ONE file
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

# Simple logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def find_phase_dir(phase_num):
    """Find the directory for a given phase"""
    # Adjusted: From phase6_orchestrator/ go up to audiobook-pipeline/ (two levels)
    project_root = Path(
        __file__
    ).parent.parent  # .parent: phase6_orchestrator, .parent.parent: audiobook-pipeline

    mapping = {
        1: "phase1-validation",
        2: "phase2-extraction",
        3: "phase3-chunking",
        4: "phase4_tts",
        5: "phase5_enhancement",
    }

    phase_name = mapping.get(phase_num)
    if not phase_name:
        logger.error(f"No directory mapping for phase {phase_num}")
        return None

    phase_dir = project_root / phase_name
    logger.info(
        f"Computed project root: {project_root}"
    )  # Diagnostic for path issues
    logger.info(f"Looking for phase {phase_num} at: {phase_dir}")

    # Basic retry if dir not found (e.g., transient FS issue)
    retries = 2
    for attempt in range(retries):
        if phase_dir.exists():
            return phase_dir
        logger.warning(
            f"Phase {phase_num} not found (attempt {attempt+1}/{retries}) - waiting 2s"
        )
        time.sleep(2)

    logger.error(
        f"Phase {phase_num} directory not found after retries: {phase_dir}"
    )
    return None


def run_phase(phase_num, file_path, file_id, pipeline_json):
    """Run a single phase"""

    print(f"\n{'='*60}")
    print(f"PHASE {phase_num}")
    print(f"{'='*60}")

    # Find phase directory
    phase_dir = find_phase_dir(phase_num)
    if not phase_dir:
        return False

    logger.info(f"Phase directory: {phase_dir}")

    # Find Python executable
    if phase_num == 4:
        # Phase 4 uses Conda
        conda_env = "phase4_tts"
        logger.info(f"Using Conda environment: {conda_env}")

        # Check if conda env exists
        try:
            check = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if conda_env not in check.stdout:
                logger.error(f"Conda environment '{conda_env}' not found!")
                logger.error(
                    "Create it with: conda env create -f phase4_tts/environment.yml"
                )
                return False
        except Exception as e:
            logger.error(f"Conda check failed: {e}")
            return False

        # For Phase 4, we need to process chunks
        return run_phase4_chunks(phase_dir, conda_env, file_id, pipeline_json)

    else:
        # Other phases use Poetry venv
        venv_dir = phase_dir / ".venv"
        if not venv_dir.exists():
            logger.info(
                f"No .venv found in {phase_dir}. Installing dependencies with Poetry..."
            )
            try:
                install_result = subprocess.run(
                    ["poetry", "install", "--no-root"],
                    cwd=str(phase_dir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if install_result.returncode != 0:
                    logger.error(
                        f"Poetry install failed for Phase {phase_num}: {install_result.stderr}"
                    )
                    return False
                logger.info(f"Poetry install succeeded for Phase {phase_num}")
            except Exception as e:
                logger.error(
                    f"Poetry install error for Phase {phase_num}: {e}"
                )
                return False

        # Use poetry run to activate venv and ensure deps
        logger.info(f"Using Poetry venv for Phase {phase_num}")

    # Build command with phase-specific script names
    module_names = {
        1: "phase1_validation",
        2: "phase2_extraction",
        3: "phase3_chunking",
        5: "phase5_enhancement",
    }

    script_names = {
        1: "validation.py",  # Matches Phase 1 attachment
        2: "extraction.py",  # Matches Phase 2 attachment
        3: "main.py",
        5: "main.py",
    }

    module_name = module_names.get(phase_num)
    script_name = script_names.get(
        phase_num, "main.py"
    )  # Default for unlisted phases

    main_script = phase_dir / "src" / module_name / script_name

    logger.info(
        f"Looking for main script at: {main_script}"
    )  # Added diagnostic

    if not main_script.exists():
        logger.error(f"Main script not found: {main_script}")
        return False

    # Use poetry run with -m for module mode if phase has relative imports (e.g., Phase 3)
    cmd_base = ["poetry", "run", "python"]
    if phase_num == 3:
        cmd_base.extend(
            ["-m", f"{module_name}.main"]
        )  # Run as module for relatives
    else:
        cmd_base.append(str(main_script))  # Direct file for others

    cmd = cmd_base + [f"--json_path={pipeline_json}"]

    # Phase-specific args
    if phase_num == 1:
        cmd.append(f"--file={file_path}")
    else:
        cmd.append(f"--file_id={file_id}")

    logger.info(f"Command: {' '.join(cmd)}")

    # Run it
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            capture_output=True,
            text=True,
            timeout=600,
        )

        duration = time.time() - start

        if result.returncode != 0:
            logger.error(
                f"FAILED (exit {result.returncode}) in {duration:.1f}s"
            )
            logger.error(f"STDERR: {result.stderr}")
            return False

        logger.info(f"SUCCESS in {duration:.1f}s")
        if result.stdout:
            logger.info(f"Output: {result.stdout.strip()}")

        return True

    except subprocess.TimeoutExpired:
        logger.error("TIMEOUT (600s)")
        return False
    except Exception as e:
        logger.error(f"ERROR: {e}")
        return False


def run_phase4_chunks(phase_dir, conda_env, file_id, pipeline_json):
    """Special handling for Phase 4 - process all chunks"""

    # Load chunks from pipeline.json
    try:
        with open(pipeline_json) as f:
            pipeline = json.load(f)

        chunks = (
            pipeline.get("phase3", {})
            .get("files", {})
            .get(file_id, {})
            .get("chunk_paths", [])
        )

        if not chunks:
            logger.error("No chunks found from Phase 3")
            return False

        logger.info(f"Processing {len(chunks)} chunks")

    except Exception as e:
        logger.error(f"Failed to load chunks: {e}")
        return False

    # Process each chunk
    main_script = phase_dir / "src" / "phase4_tts" / "main.py"
    failed = []

    for i in range(len(chunks)):
        logger.info(f"  Chunk {i+1}/{len(chunks)}")

        cmd = [
            "conda",
            "run",
            "-n",
            conda_env,
            "--no-capture-output",
            "python",
            str(main_script),
            f"--chunk_id={i}",
            f"--file_id={file_id}",
            f"--json_path={pipeline_json}",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(phase_dir),
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                logger.warning(f"  Chunk {i} failed: {result.stderr[:100]}")
                failed.append(i)

                # Abort if too many failures
                if len(failed) > len(chunks) // 2:
                    logger.error(
                        f"Too many failures ({len(failed)}/{len(chunks)})"
                    )
                    return False
            else:
                logger.info(f"  Chunk {i} OK")

        except subprocess.TimeoutExpired:
            logger.warning(f"  Chunk {i} timeout")
            failed.append(i)
        except Exception as e:
            logger.warning(f"  Chunk {i} error: {e}")
            failed.append(i)

    success_count = len(chunks) - len(failed)

    if success_count == 0:
        logger.error("All chunks failed")
        return False

    if failed:
        logger.warning(
            f"Partial success: {success_count}/{len(chunks)} chunks"
        )
    else:
        logger.info(f"All {len(chunks)} chunks completed successfully")

    return True


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="Phase 6: Run phases 1-5 for a single file"
    )
    parser.add_argument("file", help="Input file path (PDF or ebook)")
    parser.add_argument(
        "--pipeline-json",
        default="../pipeline.json",
        help="Path to pipeline.json",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        type=int,
        default=[1, 2, 3, 4, 5],
        help="Phases to run (default: 1 2 3 4 5)",
    )

    args = parser.parse_args()

    # Validate file
    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return 1

    file_id = file_path.stem

    print("\n" + "=" * 60)
    print("AUDIOBOOK PIPELINE - PHASE 6 ORCHESTRATOR")
    print("=" * 60)
    print(f"File: {file_path.name}")
    print(f"File ID: {file_id}")
    print(f"Phases: {args.phases}")
    print("=" * 60)

    # Load pipeline.json for resume
    pipeline_data = {}
    json_path = Path(args.pipeline_json).resolve()
    if json_path.exists():
        try:
            with open(json_path) as f:
                pipeline_data = json.load(f)
            logger.info(f"Loaded pipeline.json from {json_path}")
        except Exception as e:
            logger.warning(
                f"Failed to load pipeline.json: {e} - proceeding without resume"
            )

    # Run each phase with resume check
    overall_start = time.time()

    for phase in args.phases:
        phase_key = f"phase{phase}"
        if pipeline_data.get(phase_key, {}).get("status") == "success":
            logger.info(
                f"Skipping completed {phase_key} based on pipeline.json"
            )
            continue

        success = run_phase(
            phase, file_path, file_id, str(json_path)
        )  # Use resolved path

        if not success:
            print(f"\n{'='*60}")
            print(f"PIPELINE FAILED AT PHASE {phase}")
            print(f"{'='*60}")
            return 1

    duration = time.time() - overall_start

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Total time: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"{'='*60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
