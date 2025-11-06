#!/usr/bin/env python3
"""
Phase 7: Batch Processing for Audiobook Pipeline

This phase processes multiple files by calling Phase 6 (orchestrator) for each file.
Uses Trio for async concurrency and monitors CPU usage to prevent overload.

Key Features:
- Calls Phase 6 orchestrator subprocess for each file
- Parallel processing with configurable worker limit
- CPU monitoring and throttling
- Resume from checkpoints
- Comprehensive error tracking
- Rich progress reporting
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import trio
import psutil
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

from .models import BatchConfig, BatchMetadata, BatchSummary

logger = logging.getLogger(__name__)
console = Console()


def setup_logging(config: BatchConfig):
    """Configure logging to both console and file"""
    numeric_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Clear existing handlers
    logging.getLogger().handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    
    # File handler
    file_handler = logging.FileHandler(config.log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    
    # Configure root logger
    logging.getLogger().setLevel(numeric_level)
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().addHandler(file_handler)
    
    logger.info("="*60)
    logger.info("Batch Processing Started")
    logger.info("="*60)


def load_config(config_path: str) -> BatchConfig:
    """
    Load configuration from YAML file with validation.
    Falls back to defaults if file not found or invalid.
    """
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"Config file {config_path} not found, using defaults")
            return BatchConfig()
        
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        
        logger.info(f"Loaded config from {config_path}")
        return BatchConfig(**data)
    
    except yaml.YAMLError as e:
        logger.warning(f"Invalid YAML in {config_path}: {e}; using defaults")
        return BatchConfig()
    except Exception as e:
        logger.warning(f"Config load failed: {e}; using defaults")
        return BatchConfig()


def get_project_root() -> Path:
    """Get the project root directory (parent of phase7_batch)"""
    return Path(__file__).resolve().parent.parent.parent.parent


def find_orchestrator() -> Optional[Path]:
    """
    Find the Phase 6 orchestrator script.
    
    Returns:
        Path to orchestrator.py or None if not found
    """
    project_root = get_project_root()
    phase6_dir = project_root / "phase6_orchestrator"
    
    orchestrator = phase6_dir / "orchestrator.py"
    if orchestrator.exists():
        logger.info(f"Found orchestrator: {orchestrator}")
        return orchestrator
    
    logger.error(f"Orchestrator not found at {orchestrator}")
    return None


async def process_single_file(
    file_path: Path,
    config: BatchConfig,
    semaphore: trio.Semaphore
) -> BatchMetadata:
    """
    Process a single file by calling Phase 6 orchestrator.
    
    Args:
        file_path: Path to input file
        config: Batch configuration
        semaphore: Semaphore to limit parallel workers
    
    Returns:
        BatchMetadata with processing results
    """
    file_id = file_path.stem
    metadata = BatchMetadata(file_id=file_id)
    metadata.mark_started()
    
    # Check resume
    if config.resume_enabled:
        existing = load_existing_metadata(config, file_id)
        if existing and existing.status == "success":
            logger.info(f"[SKIP] {file_id} already completed successfully")
            metadata = existing
            return metadata
    
    # Find orchestrator
    orchestrator = find_orchestrator()
    if not orchestrator:
        metadata.error_message = "Phase 6 orchestrator not found"
        metadata.mark_completed()
        return metadata
    
    # Acquire semaphore (limits parallel processes)
    async with semaphore:
        # Build command - call Phase 6 orchestrator
        cmd = [
            sys.executable,  # Use current Python
            str(orchestrator),
            str(file_path),
            f"--pipeline-json={config.pipeline_json}",
            f"--phases",
        ] + [str(p) for p in config.phases_to_run]
        
        if not config.resume_enabled:
            cmd.append("--no-resume")
        
        logger.info(f"[START] {file_id}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        # Run orchestrator
        start_time = time.perf_counter()
        
        try:
            # Run subprocess async
            process = await trio.run_process(
                cmd,
                capture_stdout=True,
                capture_stderr=True,
                check=False,
                stdin=subprocess.DEVNULL
            )
            
            duration = time.perf_counter() - start_time
            
            if process.returncode != 0:
                stderr = process.stderr.decode('utf-8', errors='replace')
                error_msg = f"Orchestrator failed with exit code {process.returncode}"
                logger.error(f"[FAIL] {file_id}: {error_msg}")
                logger.error(f"stderr: {stderr[-500:]}")
                
                metadata.error_message = error_msg
                metadata.errors.append(stderr[-500:])
            else:
                logger.info(f"[SUCCESS] {file_id} in {duration:.1f}s")
                metadata.phases_completed = config.phases_to_run
            
            metadata.add_phase_metric(0, duration, metadata.error_message)
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            error_msg = f"Subprocess error: {str(e)}"
            logger.error(f"[ERROR] {file_id}: {error_msg}")
            metadata.error_message = error_msg
            metadata.errors.append(str(e))
            metadata.add_phase_metric(0, duration, error_msg)
        
        metadata.mark_completed()
        return metadata


def load_existing_metadata(config: BatchConfig, file_id: str) -> Optional[BatchMetadata]:
    """
    Load existing metadata from pipeline.json for resume functionality.
    
    Args:
        config: Batch configuration
        file_id: File identifier
    
    Returns:
        BatchMetadata if found, None otherwise
    """
    try:
        pipeline_path = Path(config.pipeline_json)
        if not pipeline_path.exists():
            return None
        
        with open(pipeline_path, 'r') as f:
            pipeline = json.load(f)
        
        # Check if all required phases completed successfully
        all_phases_ok = True
        for phase in config.phases_to_run:
            phase_key = f"phase{phase}"
            phase_data = pipeline.get(phase_key, {})
            
            if phase_data.get("status") != "success":
                all_phases_ok = False
                break
            
            # Check file-specific status
            files = phase_data.get("files", {})
            if file_id not in files:
                all_phases_ok = False
                break
        
        if all_phases_ok:
            metadata = BatchMetadata(file_id=file_id)
            metadata.status = "success"
            metadata.phases_completed = config.phases_to_run
            return metadata
        
        return None
        
    except Exception as e:
        logger.warning(f"Could not load existing metadata for {file_id}: {e}")
        return None


def update_pipeline_json(
    config: BatchConfig,
    summary: BatchSummary,
    metadata_list: List[BatchMetadata]
):
    """
    Update pipeline.json with batch summary and metadata.
    
    Args:
        config: Batch configuration
        summary: Batch processing summary
        metadata_list: List of file metadata
    """
    try:
        json_path = Path(config.pipeline_json)
        
        # Load existing
        if json_path.exists():
            with open(json_path, 'r') as f:
                pipeline = json.load(f)
        else:
            pipeline = {
                "pipeline_version": "1.0",
                "created_at": time.time()
            }
        
        # Update batch section
        pipeline["batch"] = {
            "status": summary.status,
            "summary": summary.dict(),
            "files": {m.file_id: m.dict() for m in metadata_list}
        }
        
        pipeline["last_updated"] = time.time()
        
        # Write back
        with open(json_path, 'w') as f:
            json.dump(pipeline, f, indent=4)
        
        logger.info(f"Updated {json_path} with batch summary")
        
    except Exception as e:
        logger.error(f"Failed to update pipeline.json: {e}")


def render_summary_table(summary: BatchSummary, metadata_list: List[BatchMetadata]):
    """
    Display batch processing summary using Rich tables.
    
    Args:
        summary: Batch processing summary
        metadata_list: List of file metadata
    """
    # Overall summary table
    summary_table = Table(title="Batch Processing Summary", show_header=True)
    summary_table.add_column("Metric", style="cyan", no_wrap=True)
    summary_table.add_column("Value", style="magenta")
    
    summary_table.add_row("Total Files", str(summary.total_files))
    summary_table.add_row("Successful", f"[green]{summary.successful_files}[/green]")
    summary_table.add_row("Partial", f"[yellow]{summary.partial_files}[/yellow]" if summary.partial_files > 0 else "0")
    summary_table.add_row("Failed", f"[red]{summary.failed_files}[/red]" if summary.failed_files > 0 else "0")
    summary_table.add_row("Duration", f"{summary.total_duration:.1f}s ({summary.total_duration/60:.1f}min)")
    
    if summary.avg_cpu_usage:
        cpu_color = "green" if summary.avg_cpu_usage < 70 else "yellow" if summary.avg_cpu_usage < 90 else "red"
        summary_table.add_row("Avg CPU", f"[{cpu_color}]{summary.avg_cpu_usage:.1f}%[/{cpu_color}]")
    
    # Status with color
    status_color = "green" if summary.status == "success" else "yellow" if summary.status == "partial" else "red"
    summary_table.add_row("Status", f"[{status_color}]{summary.status.upper()}[/{status_color}]")
    
    console.print("\n")
    console.print(summary_table)
    
    # Per-file details table
    if metadata_list:
        file_table = Table(title="File Processing Details", show_header=True)
        file_table.add_column("File ID", style="cyan")
        file_table.add_column("Status", style="magenta")
        file_table.add_column("Duration", justify="right")
        file_table.add_column("Error", style="red")
        
        for m in metadata_list:
            status_display = m.status
            if m.status == "success":
                status_display = f"[green]{m.status}[/green]"
            elif m.status == "failed":
                status_display = f"[red]{m.status}[/red]"
            elif m.status == "partial":
                status_display = f"[yellow]{m.status}[/yellow]"
            
            duration_str = f"{m.duration:.1f}s" if m.duration else "N/A"
            error_str = m.error_message[:50] + "..." if m.error_message and len(m.error_message) > 50 else m.error_message or ""
            
            file_table.add_row(
                m.file_id,
                status_display,
                duration_str,
                error_str
            )
        
        console.print("\n")
        console.print(file_table)
    
    # Error summary
    if summary.errors:
        console.print("\n")
        error_panel = Panel(
            "\n".join(f"• {e}" for e in summary.errors[:10]),
            title=f"Errors ({len(summary.errors)} total)",
            style="red"
        )
        console.print(error_panel)


async def monitor_cpu_usage(
    config: BatchConfig,
    cpu_readings: List[float],
    stop_event: trio.Event
):
    """
    Monitor CPU usage and add throttling if threshold exceeded.
    
    Args:
        config: Batch configuration
        cpu_readings: List to append CPU readings to
        stop_event: Event to signal monitoring stop
    """
    while not stop_event.is_set():
        await trio.sleep(1)
        
        cpu = psutil.cpu_percent(interval=0.1)
        cpu_readings.append(cpu)
        
        if cpu > config.cpu_threshold:
            logger.warning(
                f"CPU {cpu:.1f}% > {config.cpu_threshold}%; "
                f"throttling for {config.throttle_delay}s"
            )
            await trio.sleep(config.throttle_delay)


async def main_async(config: BatchConfig) -> int:
    """
    Main async processing logic.
    
    Args:
        config: Batch configuration
    
    Returns:
        Exit code (0=success, 1=failed, 2=partial)
    """
    # Find input files
    input_dir = Path(config.input_dir)
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1
    
    # Glob for PDFs and ebooks
    input_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.epub"))
    
    if config.batch_size:
        input_files = input_files[:config.batch_size]
    
    if not input_files:
        logger.error(f"No input files found in {input_dir}")
        return 1
    
    logger.info(f"Found {len(input_files)} files to process")
    
    # Display header (use -> instead of → for Windows compatibility)
    phase_display = ' -> '.join(map(str, config.phases_to_run))
    header = f"""
Batch Audiobook Processing

Input Dir:     {input_dir}
Files:         {len(input_files)}
Pipeline JSON: {config.pipeline_json}
Max Workers:   {config.max_workers}
CPU Threshold: {config.cpu_threshold}%
Resume:        {'Enabled' if config.resume_enabled else 'Disabled'}
Phases:        {phase_display}
"""
    console.print(Panel(header.strip(), title="Configuration", style="cyan"))
    
    # Setup CPU monitoring
    cpu_readings = []
    stop_event = trio.Event()
    
    # Setup semaphore for worker limit
    semaphore = trio.Semaphore(config.max_workers)
    
    # Setup progress tracking
    metadata_list = []
    overall_start = time.perf_counter()
    
    async with trio.open_nursery() as nursery:
        # Start CPU monitor
        nursery.start_soon(monitor_cpu_usage, config, cpu_readings, stop_event)
        
        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Processing files...",
                total=len(input_files)
            )
            
            async def process_and_update(file_path):
                metadata = await process_single_file(file_path, config, semaphore)
                metadata_list.append(metadata)
                progress.update(task, advance=1)
            
            # Launch all file processing tasks
            async with trio.open_nursery() as process_nursery:
                for file_path in input_files:
                    process_nursery.start_soon(process_and_update, file_path)
        
        # Stop CPU monitoring
        stop_event.set()
    
    # Calculate summary
    total_duration = time.perf_counter() - overall_start
    avg_cpu = sum(cpu_readings) / len(cpu_readings) if cpu_readings else None
    
    summary = BatchSummary.from_metadata_list(
        metadata_list,
        total_duration,
        avg_cpu
    )
    
    # Update pipeline.json
    update_pipeline_json(config, summary, metadata_list)
    
    # Display summary
    render_summary_table(summary, metadata_list)
    
    # Determine exit code
    if summary.status == "success":
        return 0
    elif summary.status == "partial":
        return 2
    else:
        return 1


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 7: Batch processing for audiobook pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all PDFs in input directory
  batch-audiobook --config config.yaml

  # Process with custom settings
  batch-audiobook --input-dir ./books --max-workers 8 --phases 3 4 5
        """
    )
    
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config YAML (default: config.yaml)"
    )
    parser.add_argument(
        "--input-dir",
        help="Override input directory from config"
    )
    parser.add_argument(
        "--pipeline-json",
        help="Override pipeline.json path from config"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Override max parallel workers"
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        type=int,
        help="Override phases to run"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume (process all files fresh)"
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Apply CLI overrides
    if args.input_dir:
        config.input_dir = args.input_dir
    if args.pipeline_json:
        config.pipeline_json = args.pipeline_json
    if args.max_workers:
        config.max_workers = args.max_workers
    if args.phases:
        config.phases_to_run = args.phases
    if args.no_resume:
        config.resume_enabled = False
    
    # Setup logging
    setup_logging(config)
    
    # Run async main
    try:
        exit_code = trio.run(main_async, config)
        return exit_code
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
