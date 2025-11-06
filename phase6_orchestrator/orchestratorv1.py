#!/usr/bin/env python3
"""
Phase 6: Single-File Orchestrator (Enhanced)
Production-ready orchestrator - runs phases 1-5 sequentially with:
- Rich progress reporting
- Robust Conda environment handling
- Resume from checkpoints
- Error handling with retries
- Actionable error messages
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich not available. Install with: pip install rich")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console() if RICH_AVAILABLE else None


def print_status(message: str, style: str = "bold"):
    """Print status message with Rich or fallback to print"""
    if console:
        console.print(message, style=style)
    else:
        print(message)


def print_panel(content: str, title: str = "", style: str = ""):
    """Print panel with Rich or fallback"""
    if console:
        console.print(Panel(content, title=title, style=style))
    else:
        print(f"\n{'='*60}")
        if title:
            print(f"{title}")
            print("="*60)
        print(content)
        print("="*60 + "\n")


def check_conda_environment(env_name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if Conda environment exists and is accessible.
    
    Returns:
        (exists: bool, error_message: Optional[str])
    """
    try:
        # Check if conda is available
        result = subprocess.run(
            ["conda", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "Conda not found. Install Miniconda or Anaconda first."
        
        # Check if environment exists
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if env_name not in result.stdout:
            error_msg = (
                f"Conda environment '{env_name}' not found.\n\n"
                f"Create it with:\n"
                f"  cd phase4_tts\n"
                f"  conda env create -f environment.yml\n"
                f"  conda activate {env_name}\n"
                f"  pip install git+https://github.com/resemble-ai/chatterbox.git\n"
                f"  pip install piper-tts librosa requests torchaudio"
            )
            return False, error_msg
        
        # Verify environment can be activated
        test_cmd = ["conda", "run", "-n", env_name, "python", "--version"]
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, f"Cannot activate '{env_name}': {result.stderr}"
        
        logger.info(f"✓ Conda environment '{env_name}' is ready")
        return True, None
        
    except FileNotFoundError:
        error_msg = (
            "Conda not found in PATH.\n\n"
            "Install Miniconda from: https://docs.conda.io/en/latest/miniconda.html\n"
            "Or add Conda to PATH if already installed."
        )
        return False, error_msg
    except subprocess.TimeoutExpired:
        return False, "Conda command timed out. Check your Conda installation."
    except Exception as e:
        return False, f"Conda check failed: {str(e)}"


def load_pipeline_json(json_path: Path) -> Dict:
    """
    Load pipeline.json with error handling.
    
    Returns:
        Dictionary with pipeline data, or empty dict on error
    """
    if not json_path.exists():
        logger.info(f"Pipeline JSON not found: {json_path} (will create on first run)")
        return {}
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        if not isinstance(data, dict):
            logger.warning(f"Invalid pipeline.json structure, starting fresh")
            return {}
        
        logger.info(f"Loaded pipeline.json: {len(data)} phase(s) recorded")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Corrupt pipeline.json: {e}")
        backup_path = json_path.with_suffix('.json.corrupt')
        json_path.rename(backup_path)
        logger.info(f"Moved corrupt file to: {backup_path}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load pipeline.json: {e}")
        return {}


def check_phase_status(pipeline_data: Dict, phase_num: int, file_id: str) -> str:
    """
    Check status of a phase for a specific file.
    
    Returns:
        "success", "failed", "partial", or "pending"
    """
    phase_key = f"phase{phase_num}"
    phase_data = pipeline_data.get(phase_key, {})
    
    # Check overall phase status first
    overall_status = phase_data.get("status")
    if overall_status == "success":
        return "success"
    
    # Check file-specific status
    files = phase_data.get("files", {})
    
    # Try exact match first
    if file_id in files:
        return files[file_id].get("status", "pending")
    
    # Try fuzzy match
    for key in files.keys():
        if file_id in key or key in file_id:
            logger.info(f"Phase {phase_num}: Using key '{key}' for file_id '{file_id}'")
            return files[key].get("status", "pending")
    
    return "pending"


def find_phase_dir(phase_num: int) -> Optional[Path]:
    """Find directory for a phase number."""
    project_root = Path(__file__).parent.parent
    
    mapping = {
        1: "phase1-validation",
        2: "phase2-extraction",
        3: "phase3-chunking",
        4: "phase4_tts",
        5: "phase5_enhancement"
    }
    
    phase_name = mapping.get(phase_num)
    if not phase_name:
        return None
    
    phase_dir = project_root / phase_name
    if phase_dir.exists():
        return phase_dir
    
    logger.error(f"Phase {phase_num} directory not found: {phase_dir}")
    return None


def run_phase_with_retry(
    phase_num: int,
    file_path: Path,
    file_id: str,
    pipeline_json: Path,
    max_retries: int = 2
) -> bool:
    """
    Run a phase with retry logic.
    
    Args:
        phase_num: Phase number (1-5)
        file_path: Input file path
        file_id: File identifier
        pipeline_json: Path to pipeline.json
        max_retries: Maximum retry attempts (default 2)
    
    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt}/{max_retries} for Phase {phase_num}")
            time.sleep(2)  # Brief pause before retry
        
        success = run_phase(phase_num, file_path, file_id, pipeline_json)
        
        if success:
            return True
    
    logger.error(f"Phase {phase_num} failed after {max_retries + 1} attempts")
    return False


def run_phase(
    phase_num: int,
    file_path: Path,
    file_id: str,
    pipeline_json: Path
) -> bool:
    """
    Run a single phase.
    
    Args:
        phase_num: Phase number (1-5)
        file_path: Input file path
        file_id: File identifier
        pipeline_json: Path to pipeline.json
    
    Returns:
        True if successful, False otherwise
    """
    phase_dir = find_phase_dir(phase_num)
    if not phase_dir:
        return False
    
    logger.info(f"Phase {phase_num} directory: {phase_dir}")
    
    # Special handling for Phase 4 (Conda environment)
    if phase_num == 4:
        return run_phase4_with_conda(phase_dir, file_id, pipeline_json)
    
    # Standard phases (1, 2, 3, 5) use Poetry
    return run_phase_standard(phase_num, phase_dir, file_path, file_id, pipeline_json)


def run_phase_standard(
    phase_num: int,
    phase_dir: Path,
    file_path: Path,
    file_id: str,
    pipeline_json: Path
) -> bool:
    """Run a standard phase using Poetry."""
    # Check for venv
    venv_dir = phase_dir / ".venv"
    if not venv_dir.exists():
        logger.info(f"Installing dependencies for Phase {phase_num}...")
        try:
            result = subprocess.run(
                ["poetry", "install", "--no-root"],
                cwd=str(phase_dir),
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                logger.error(f"Poetry install failed: {result.stderr}")
                return False
            logger.info("Dependencies installed successfully")
        except Exception as e:
            logger.error(f"Poetry install error: {e}")
            return False
    
    # Build command
    module_names = {
        1: "phase1_validation",
        2: "phase2_extraction",
        3: "phase3_chunking",
        5: "phase5_enhancement"
    }
    
    module_name = module_names.get(phase_num)
    
    # Phase 3 requires module mode for relative imports
    if phase_num == 3:
        cmd = ["poetry", "run", "python", "-m", f"{module_name}.main"]
    else:
        script_names = {
            1: "validation.py",
            2: "extraction.py",
            5: "main.py"
        }
        script_name = script_names.get(phase_num, "main.py")
        main_script = phase_dir / "src" / module_name / script_name
        
        if not main_script.exists():
            logger.error(f"Script not found: {main_script}")
            return False
        
        cmd = ["poetry", "run", "python", str(main_script)]
    
    # Add phase-specific arguments
    if phase_num == 1:
        cmd.extend([f"--file={file_path}", f"--json_path={pipeline_json}"])
    elif phase_num == 5:
        # Phase 5 reads from config.yaml
        pass
    else:
        cmd.extend([f"--file_id={file_id}", f"--json_path={pipeline_json}"])
    
    logger.info(f"Command: {' '.join(cmd)}")
    
    # Execute
    start_time = time.perf_counter()
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
        
        duration = time.perf_counter() - start_time
        
        if result.returncode != 0:
            logger.error(f"Phase {phase_num} FAILED (exit {result.returncode}) in {duration:.1f}s")
            logger.error(f"Error: {result.stderr[-500:]}")  # Last 500 chars
            return False
        
        logger.info(f"Phase {phase_num} SUCCESS in {duration:.1f}s")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"Phase {phase_num} TIMEOUT (600s)")
        return False
    except Exception as e:
        logger.error(f"Phase {phase_num} ERROR: {e}")
        return False


def run_phase4_with_conda(phase_dir: Path, file_id: str, pipeline_json: Path) -> bool:
    """
    Run Phase 4 with Conda environment activation.
    
    Special handling for TTS synthesis with Chatterbox.
    """
    conda_env = "phase4_tts"
    
    # Check Conda environment
    env_ok, error_msg = check_conda_environment(conda_env)
    if not env_ok:
        logger.error("="*60)
        logger.error("CONDA ENVIRONMENT ERROR")
        logger.error("="*60)
        logger.error(error_msg)
        logger.error("="*60)
        return False
    
    # Load chunks from pipeline.json
    try:
        with open(pipeline_json, 'r') as f:
            pipeline = json.load(f)
        
        phase3_files = pipeline.get("phase3", {}).get("files", {})
        
        # Find matching file_id (exact or fuzzy match)
        chunks = []
        actual_file_id = file_id
        
        if file_id in phase3_files:
            chunks = phase3_files[file_id].get("chunk_paths", [])
        else:
            for key in phase3_files.keys():
                if file_id in key or key in file_id:
                    logger.info(f"Using Phase 3 file_id: '{key}'")
                    actual_file_id = key
                    chunks = phase3_files[key].get("chunk_paths", [])
                    break
        
        if not chunks:
            logger.error(f"No chunks found for file_id: '{file_id}'")
            logger.error(f"Available in Phase 3: {list(phase3_files.keys())}")
            return False
        
        logger.info(f"Processing {len(chunks)} chunks")
        
    except Exception as e:
        logger.error(f"Failed to load chunks: {e}")
        return False
    
    # Process chunks with progress bar
    main_script = "src/phase4_tts/main.py"
    ref_file = "greenman_ref.wav"
    failed_chunks = []
    
    if RICH_AVAILABLE and console:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"[cyan]Synthesizing {len(chunks)} chunks...", total=len(chunks))
            
            for i in range(len(chunks)):
                success = process_single_chunk(
                    phase_dir, conda_env, main_script, ref_file,
                    i, actual_file_id, pipeline_json
                )
                
                if not success:
                    failed_chunks.append(i)
                
                progress.update(task, advance=1)
    else:
        # Fallback without Rich
        for i in range(len(chunks)):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            success = process_single_chunk(
                phase_dir, conda_env, main_script, ref_file,
                i, actual_file_id, pipeline_json
            )
            
            if not success:
                failed_chunks.append(i)
    
    # Check results
    success_count = len(chunks) - len(failed_chunks)
    
    if success_count == 0:
        logger.error("All chunks failed")
        return False
    
    if failed_chunks:
        logger.warning(f"Partial success: {success_count}/{len(chunks)} chunks completed")
        logger.warning(f"Failed chunks: {failed_chunks[:10]}")
        # Accept partial success (Phase 4 has silence insertion fallback)
        return True
    
    logger.info(f"All {len(chunks)} chunks completed successfully")
    return True


def process_single_chunk(
    phase_dir: Path,
    conda_env: str,
    main_script: str,
    ref_file: str,
    chunk_id: int,
    file_id: str,
    pipeline_json: Path
) -> bool:
    """Process a single TTS chunk."""
    cmd = [
        "conda", "run",
        "-n", conda_env,
        "--no-capture-output",
        "python", main_script,
        f"--chunk_id={chunk_id}",
        f"--file_id={file_id}",
        f"--json_path={pipeline_json}",
        "--enable-splitting"
    ]
    
    # Add reference file if exists
    if (phase_dir / ref_file).exists():
        cmd.append(f"--ref_file={ref_file}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=1200  # 20 minutes per chunk
        )
        
        if result.returncode != 0:
            error_log = phase_dir / f"chunk_{chunk_id}_error.log"
            with open(error_log, 'w') as f:
                f.write(result.stderr)
                f.write("\n\nSTDOUT:\n")
                f.write(result.stdout)
            logger.warning(f"Chunk {chunk_id} failed (logged to {error_log})")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Chunk {chunk_id} timeout (20min)")
        return False
    except Exception as e:
        logger.warning(f"Chunk {chunk_id} error: {e}")
        return False


def summarize_results(pipeline_json: Path):
    """Create summary table of pipeline results."""
    try:
        with open(pipeline_json, 'r') as f:
            data = json.load(f)
    except:
        return
    
    if not RICH_AVAILABLE:
        return
    
    table = Table(title="Pipeline Results")
    table.add_column("Phase", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    for i in range(1, 6):
        phase_key = f"phase{i}"
        phase_data = data.get(phase_key, {})
        status = phase_data.get("status", "pending")
        
        # Get details
        details = ""
        if phase_key == "phase3":
            files = phase_data.get("files", {})
            for fid, fdata in files.items():
                chunk_count = len(fdata.get("chunk_paths", []))
                details = f"{chunk_count} chunks"
                break
        elif phase_key == "phase4":
            files = phase_data.get("files", {})
            for fid, fdata in files.items():
                audio_count = len(fdata.get("chunk_audio_paths", []))
                avg_mos = fdata.get("metrics", {}).get("avg_mos", 0)
                details = f"{audio_count} audio chunks, MOS={avg_mos:.2f}"
                break
        
        # Color-code status
        if status == "success":
            status_display = f"[green]{status}[/green]"
        elif status == "failed":
            status_display = f"[red]{status}[/red]"
        else:
            status_display = f"[yellow]{status}[/yellow]"
        
        table.add_row(f"Phase {i}", status_display, details)
    
    console.print(table)


def main():
    """Main orchestrator entry point."""
    parser = argparse.ArgumentParser(
        description="Phase 6: Production Orchestrator for Audiobook Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline for a PDF
  python orchestrator.py input/The_Analects_of_Confucius_20240228.pdf

  # Resume from checkpoint
  python orchestrator.py input/book.pdf --pipeline-json=pipeline.json

  # Run specific phases only
  python orchestrator.py input/book.pdf --phases 3 4 5
        """
    )
    
    parser.add_argument(
        "file",
        type=Path,
        help="Input file path (PDF or ebook)"
    )
    parser.add_argument(
        "--pipeline-json",
        type=Path,
        default=Path("../pipeline.json"),
        help="Path to pipeline.json (default: ../pipeline.json)"
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        type=int,
        default=[1, 2, 3, 4, 5],
        help="Phases to run (default: 1 2 3 4 5)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume from checkpoint (run all phases)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum retry attempts per phase (default: 2)"
    )
    
    args = parser.parse_args()
    
    # Validate input file (resolve path first)
    file_path = args.file.resolve()
    if not file_path.exists():
        print_status(f"[red]ERROR: File not found: {file_path}[/red]")
        return 1
    file_id = file_path.stem
    
    # Resolve pipeline.json path
    pipeline_json = args.pipeline_json.resolve()
    
    # Display header
    header = f"""
Audiobook Pipeline - Phase 6 Orchestrator

Input File:    {file_path.name}
File ID:       {file_id}
Pipeline JSON: {pipeline_json}
Phases:        {' → '.join(map(str, args.phases))}
Resume:        {'Disabled' if args.no_resume else 'Enabled'}
Max Retries:   {args.max_retries}
"""
    print_panel(header.strip(), "Configuration", "bold cyan")
    
    # Load pipeline.json
    pipeline_data = load_pipeline_json(pipeline_json) if not args.no_resume else {}
    
    # Run phases
    overall_start = time.perf_counter()
    completed_phases = []
    
    for phase_num in args.phases:
        phase_name = f"Phase {phase_num}"
        
        # Check resume status
        if not args.no_resume:
            status = check_phase_status(pipeline_data, phase_num, file_id)
            if status == "success":
                print_status(f"[green]✓ Skipping {phase_name} (already completed)[/green]")
                completed_phases.append(phase_num)
                continue
            elif status in ["failed", "partial"]:
                print_status(f"[yellow]⟳ Retrying {phase_name} (previous status: {status})[/yellow]")
        
        # Run phase with retries
        print_status(f"\n[bold cyan]▶ Running {phase_name}...[/bold cyan]")
        
        success = run_phase_with_retry(
            phase_num,
            file_path,
            file_id,
            pipeline_json,
            max_retries=args.max_retries
        )
        
        if not success:
            print_panel(
                f"Pipeline aborted at {phase_name}\n\n"
                f"Check logs above for details.\n"
                f"Fix issues and re-run with same command to resume.",
                "PIPELINE FAILED",
                "bold red"
            )
            return 1
        
        print_status(f"[green]✓ {phase_name} completed successfully[/green]")
        completed_phases.append(phase_num)
    
    # Calculate duration
    duration = time.perf_counter() - overall_start
    
    # Display summary
    summary = f"""
Pipeline completed successfully!

Phases Completed: {' → '.join(map(str, completed_phases))}
Total Duration:   {duration:.1f}s ({duration/60:.1f} minutes)

Output Location:
- Chunks: phase3-chunking/chunks/
- Audio:  phase4_tts/audio_chunks/
- Final:  phase5_enhancement/output/

Next Steps:
1. Review pipeline.json for quality metrics
2. Listen to final audiobook in phase5_enhancement/output/
3. Check for any warnings in logs above
"""
    print_panel(summary.strip(), "SUCCESS", "bold green")
    
    # Show results table
    summarize_results(pipeline_json)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
