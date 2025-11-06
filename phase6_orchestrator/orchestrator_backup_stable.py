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
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def summarize_pipeline_json(pipeline_json_path):
    """Create a readable summary of pipeline.json for troubleshooting"""
    try:
        with open(pipeline_json_path) as f:
            pipeline = json.load(f)
        
        summary = {
            "phases": {},
            "total_size_bytes": Path(pipeline_json_path).stat().st_size
        }
        
        for phase_key in ["phase1", "phase2", "phase3", "phase4", "phase5"]:
            if phase_key in pipeline:
                phase_data = pipeline[phase_key]
                phase_summary = {
                    "status": phase_data.get("status", "unknown"),
                    "file_count": len(phase_data.get("files", {})),
                    "has_errors": bool(phase_data.get("errors", []))
                }
                
                if phase_key == "phase3":
                    # Summarize chunk counts
                    files = phase_data.get("files", {})
                    phase_summary["file_ids"] = list(files.keys())
                    phase_summary["chunk_counts"] = {
                        fid: len(data.get("chunk_paths", [])) 
                        for fid, data in files.items()
                    }
                
                summary["phases"][phase_key] = phase_summary
        
        # Write summary
        summary_path = Path(pipeline_json_path).parent / "pipeline_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Pipeline summary written to: {summary_path}")
        logger.info(f"Pipeline.json size: {summary['total_size_bytes']:,} bytes")
        
        return summary
    except Exception as e:
        logger.error(f"Failed to summarize pipeline.json: {e}")
        return None


def find_phase_dir(phase_num):
    """Find the directory for a given phase"""
    # Adjusted: From phase6_orchestrator/ go up to audiobook-pipeline/ (two levels)
    project_root = Path(__file__).parent.parent  # .parent: phase6_orchestrator, .parent.parent: audiobook-pipeline
    
    mapping = {
        1: "phase1-validation",
        2: "phase2-extraction",
        3: "phase3-chunking",
        4: "phase4_tts",
        5: "phase5_enhancement"
    }
    
    phase_name = mapping.get(phase_num)
    if not phase_name:
        logger.error(f"No directory mapping for phase {phase_num}")
        return None
    
    phase_dir = project_root / phase_name
    logger.info(f"Computed project root: {project_root}")  # Diagnostic for path issues
    logger.info(f"Looking for phase {phase_num} at: {phase_dir}")
    
    # Basic retry if dir not found (e.g., transient FS issue)
    retries = 2
    for attempt in range(retries):
        if phase_dir.exists():
            return phase_dir
        logger.warning(f"Phase {phase_num} not found (attempt {attempt+1}/{retries}) - waiting 2s")
        time.sleep(2)
    
    logger.error(f"Phase {phase_num} directory not found after retries: {phase_dir}")
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
                timeout=10
            )
            if conda_env not in check.stdout:
                logger.error(f"Conda environment '{conda_env}' not found!")
                logger.error("Create it with: conda env create -f phase4_tts/environment.yml")
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
            logger.info(f"No .venv found in {phase_dir}. Installing dependencies with Poetry...")
            try:
                install_result = subprocess.run(
                    ["poetry", "install", "--no-root"],
                    cwd=str(phase_dir),
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if install_result.returncode != 0:
                    logger.error(f"Poetry install failed for Phase {phase_num}: {install_result.stderr}")
                    return False
                logger.info(f"Poetry install succeeded for Phase {phase_num}")
            except Exception as e:
                logger.error(f"Poetry install error for Phase {phase_num}: {e}")
                return False
        
        # Use poetry run to activate venv and ensure deps
        logger.info(f"Using Poetry venv for Phase {phase_num}")
    
    # Build command with phase-specific script names
    module_names = {
        1: "phase1_validation",
        2: "phase2_extraction", 
        3: "phase3_chunking",
        5: "phase5_enhancement"
    }
    
    script_names = {
        1: "validation.py",  # Matches Phase 1 attachment
        2: "extraction.py",  # Matches Phase 2 attachment
        3: "main.py",
        5: "main.py"
    }
    
    module_name = module_names.get(phase_num)
    script_name = script_names.get(phase_num, "main.py")  # Default for unlisted phases
    
    main_script = phase_dir / "src" / module_name / script_name
    
    logger.info(f"Looking for main script at: {main_script}")  # Added diagnostic
    
    if not main_script.exists():
        logger.error(f"Main script not found: {main_script}")
        return False
    
    # Use poetry run with -m for module mode if phase has relative imports (e.g., Phase 3)
    cmd_base = ["poetry", "run", "python"]
    if phase_num == 3:
        cmd_base.extend(["-m", f"{module_name}.main"])  # Run as module for relatives
    else:
        cmd_base.append(str(main_script))  # Direct file for others
    
    # Phase-specific arguments
    if phase_num == 1:
        # Phase 1: validation
        cmd = cmd_base + [
            f"--file={file_path}",
            f"--json_path={pipeline_json}"
        ]
    elif phase_num == 5:
        # Phase 5: enhancement - uses config file settings, no json_path or file_id args
        cmd = cmd_base  # No additional args, it reads from its config.yaml
    else:
        # Phase 2, 3: standard args
        cmd = cmd_base + [
            f"--file_id={file_id}",
            f"--json_path={pipeline_json}"
        ]
    
    logger.info(f"Command: {' '.join(cmd)}")
    
    # Run it
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=600
        )
        
        duration = time.time() - start
        
        if result.returncode != 0:
            logger.error(f"FAILED (exit {result.returncode}) in {duration:.1f}s")
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
        
        # Phase 3 might have written data under a different key
        # Try to find the actual file_id used in Phase 3
        phase3_files = pipeline.get("phase3", {}).get("files", {})
        
        # First try exact match
        chunks = phase3_files.get(file_id, {}).get("chunk_paths", [])
        
        # If not found, try to find a matching key
        if not chunks and phase3_files:
            logger.warning(f"Exact file_id '{file_id}' not found in Phase 3 output")
            logger.info(f"Available keys in Phase 3: {list(phase3_files.keys())}")
            
            # Try to find a key that contains the file_id or vice versa
            for key in phase3_files.keys():
                if file_id in key or key in file_id:
                    logger.info(f"Using Phase 3 key: '{key}'")
                    file_id = key  # Update file_id to match
                    chunks = phase3_files[key].get("chunk_paths", [])
                    break
        
        if not chunks:
            logger.error("No chunks found from Phase 3")
            logger.error(f"Searched for file_id: '{file_id}'")
            logger.error(f"Available Phase 3 files: {list(phase3_files.keys())}")
            return False
        
        # Convert relative paths to absolute
        # Phase 3 might write relative paths like "chunks/file.txt"
        # We need absolute paths for Phase 4
        pipeline_dir = Path(pipeline_json).parent
        absolute_chunks = []
        
        for chunk_path in chunks:
            chunk_p = Path(chunk_path)
            if not chunk_p.is_absolute():
                # Try multiple possible base directories
                possible_bases = [
                    pipeline_dir / chunk_path,  # Relative to pipeline.json
                    pipeline_dir / "phase3-chunking" / chunk_path,  # In phase3 dir
                    pipeline_dir / "chunks" / chunk_p.name,  # In chunks dir
                ]
                
                for possible_path in possible_bases:
                    if possible_path.exists():
                        absolute_chunks.append(str(possible_path.resolve()))
                        break
                else:
                    logger.warning(f"Could not find chunk file: {chunk_path}")
                    absolute_chunks.append(str(chunk_path))  # Keep original as fallback
            else:
                absolute_chunks.append(str(chunk_path))
        
        chunks = absolute_chunks
        
        logger.info(f"Processing {len(chunks)} chunks for file_id='{file_id}'")
        logger.info(f"First chunk: {chunks[0] if chunks else 'N/A'}")
        
        # Update pipeline.json with absolute paths so Phase 4 can find them
        # This is a temporary fix until Phase 3 writes absolute paths
        if chunks != phase3_files[file_id].get("chunk_paths", []):
            logger.info("Updating pipeline.json with absolute chunk paths...")
            phase3_files[file_id]["chunk_paths"] = chunks
            pipeline["phase3"]["files"] = phase3_files
            
            # Write back to pipeline.json
            with open(pipeline_json, 'w') as f:
                json.dump(pipeline, f, indent=4)
            
            # Small delay to ensure file system flushes
            time.sleep(0.5)
            
            logger.info("Pipeline.json updated with absolute paths")
            
            # Verify the update worked
            with open(pipeline_json, 'r') as f:
                verify = json.load(f)
            verify_chunks = verify.get("phase3", {}).get("files", {}).get(file_id, {}).get("chunk_paths", [])
            if verify_chunks and Path(verify_chunks[0]).is_absolute():
                logger.info("✓ Verified: Pipeline.json now has absolute paths")
            else:
                logger.warning("⚠ Verification failed: Paths may still be relative")
        
    except Exception as e:
        logger.error(f"Failed to load chunks: {e}")
        return False
    
    # Process each chunk
    main_script = "src/phase4_tts/main.py"  # Use relative path like test
    failed = []
    
    # Check for reference audio file (relative path like test)
    ref_file_name = "greenman_ref.wav"
    
    for i in range(len(chunks)):
        logger.info(f"  Chunk {i+1}/{len(chunks)}")
        
        cmd = [
            "conda", "run",
            "-n", conda_env,
            "--no-capture-output",
            "python", main_script,  # Relative path
            f"--chunk_id={i}",
            f"--file_id={file_id}",
            f"--json_path={pipeline_json}",
            "--enable-splitting"  # CRITICAL: Enable text splitting for clean audio
        ]
        
        # Add reference file if it exists (relative path like test)
        if (phase_dir / ref_file_name).exists():
            cmd.append(f"--ref_file={ref_file_name}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(phase_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace undecodable bytes with \ufffd instead of crashing
                timeout=1200
            )
            
            if result.returncode != 0:
                # Show full error, not truncated
                error_lines = result.stderr.strip().split('\n')
                logger.warning(f"  Chunk {i} failed with exit code {result.returncode}")
                logger.warning(f"  Error: {error_lines[-1] if error_lines else 'Unknown error'}")
                
                # Log full stderr to a separate file for debugging
                error_log = phase_dir / f"chunk_{i}_error.log"
                with open(error_log, 'w') as f:
                    f.write(result.stderr)
                    f.write("\n\nSTDOUT:\n")
                    f.write(result.stdout)
                logger.warning(f"  Full error saved to: {error_log}")
                
                failed.append(i)
                
                # Abort if too many failures
                if len(failed) > len(chunks) // 2:
                    logger.error(f"Too many failures ({len(failed)}/{len(chunks)})")
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
        logger.warning(f"Partial success: {success_count}/{len(chunks)} chunks")
    else:
        logger.info(f"All {len(chunks)} chunks completed successfully")
    
    return True


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Phase 6: Run phases 1-5 for a single file"
    )
    parser.add_argument(
        "file",
        help="Input file path (PDF or ebook)"
    )
    parser.add_argument(
        "--pipeline-json",
        default="../pipeline.json",
        help="Path to pipeline.json (default: ../pipeline.json from orchestrator dir)"
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        type=int,
        default=[1, 2, 3, 4, 5],
        help="Phases to run (default: 1 2 3 4 5)"
    )
    
    args = parser.parse_args()
    
    # Validate file
    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return 1
    
    file_id = file_path.stem
    
    print("\n" + "="*60)
    print("AUDIOBOOK PIPELINE - PHASE 6 ORCHESTRATOR")
    print("="*60)
    print(f"File: {file_path.name}")
    print(f"File ID: {file_id}")
    print(f"Phases: {args.phases}")
    print("="*60)
    
    # Load pipeline.json for resume
    pipeline_data = {}
    json_path = Path(args.pipeline_json).resolve()
    if json_path.exists():
        try:
            # Create summary for troubleshooting
            summarize_pipeline_json(json_path)
            
            with open(json_path) as f:
                pipeline_data = json.load(f)
            logger.info(f"Loaded pipeline.json from {json_path}")
        except Exception as e:
            logger.warning(f"Failed to load pipeline.json: {e} - proceeding without resume")
    
    # Run each phase with resume check
    overall_start = time.time()
    
    for phase in args.phases:
        phase_key = f"phase{phase}"
        if pipeline_data.get(phase_key, {}).get("status") == "success":
            logger.info(f"Skipping completed {phase_key} based on pipeline.json")
            continue
        
        success = run_phase(phase, file_path, file_id, str(json_path))  # Use resolved path
        
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
