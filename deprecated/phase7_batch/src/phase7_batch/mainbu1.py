import argparse
import json
import logging
import time
from pathlib import Path
import subprocess
import threading
import sys
import tomllib  # Stdlib for TOML
from typing import List, Optional, Dict, Any
from packaging import version
from rich.console import Console
from rich.table import Table

import trio
from tqdm import tqdm
import psutil
import yaml

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / "pipeline.json").exists():
            return current
        current = current.parent
    raise ValueError(
        "Project root not found; ensure pipeline.json exists at root."
    )


class BatchConfig:
    def __init__(self, **data):
        self.log_level = data.get("log_level", "INFO")
        self.log_file = data.get("log_file", "batch.log")
        self.input_dir = data.get("input_dir", "input")
        self.pipeline_json = data.get("pipeline_json", "pipeline.json")
        self.max_workers = data.get(
            "max_workers", max(1, psutil.cpu_count(logical=False) - 1)
        )
        self.phase_timeout = data.get("phase_timeout", 600)  # 10 min
        self.resume_enabled = data.get("resume_enabled", True)
        self.phases_to_run = data.get("phases_to_run", [1, 2, 3, 4, 5])
        self.batch_size = data.get("batch_size", None)
        self.cpu_threshold = data.get("cpu_threshold", 95.0)
        self.throttle_delay = data.get("throttle_delay", 0.5)
        self.cleanup_days = data.get("cleanup_days", 7)  # For artifacts
        if self.max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        valid_phases = set(range(1, 6))
        if not all(p in valid_phases for p in self.phases_to_run):
            raise ValueError(f"Phases must be in {valid_phases}")

    def dict(self):
        return vars(self)


class BatchMetadata:
    def __init__(self, file_id: str):
        self.file_id = file_id
        self.status = "pending"
        self.phases_completed: List[int] = []
        self.chunk_ids: List[int] = []
        self.phase_metrics: Dict[str, Dict[str, Any]] = {}
        self.error_message: Optional[str] = None
        self.timestamps: Dict[str, float] = {}
        self.duration: Optional[float] = None
        self.errors: List[str] = []

    def mark_started(self):
        self.status = "running"
        self.timestamps["start"] = time.time()

    def mark_completed(self):
        self.timestamps["end"] = time.time()
        self.duration = self.timestamps["end"] - self.timestamps["start"]
        self.status = (
            "success"
            if not self.error_message and not self.errors
            else "failed" if not self.phases_completed else "partial"
        )

    def add_phase_metric(
        self, phase: int, duration: float, error: Optional[str] = None
    ):
        self.phase_metrics[f"phase{phase}"] = {
            "duration": duration,
            "error": error,
        }

    def dict(self):
        return vars(self)


class BatchSummary:
    def __init__(
        self,
        total_files: int,
        successful_files: int,
        partial_files: int,
        failed_files: int,
        total_duration: float,
        avg_cpu_usage: Optional[float],
        errors: List[str],
        timestamps: Dict[str, float],
    ):
        self.total_files = total_files
        self.successful_files = successful_files
        self.partial_files = partial_files
        self.failed_files = failed_files
        self.total_duration = total_duration
        self.avg_cpu_usage = avg_cpu_usage
        self.status = (
            "success"
            if failed_files == 0 and partial_files == 0
            else (
                "partial"
                if successful_files > 0 or partial_files > 0
                else "failed"
            )
        )
        self.errors = errors
        self.timestamps = timestamps
        self.artifacts: List[str] = []

    def dict(self):
        return {
            "total_files": self.total_files,
            "successful_files": self.successful_files,
            "partial_files": self.partial_files,
            "failed_files": self.failed_files,
            "total_duration": self.total_duration,
            "avg_cpu_usage": self.avg_cpu_usage,
            "status": self.status,
            "errors": self.errors,
            "timestamps": self.timestamps,
            "artifacts": self.artifacts,
        }


def setup_logging(config: BatchConfig):
    numeric_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.getLogger().handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    file_handler = logging.FileHandler(config.log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().setLevel(numeric_level)
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().addHandler(file_handler)


def monitor_cpu(config: BatchConfig, stop_event: threading.Event):
    while not stop_event.is_set():
        cpu = psutil.cpu_percent(interval=1)
        if cpu > config.cpu_threshold:
            logger.warning(
                f"CPU {cpu:.1f}% > {config.cpu_threshold}%; throttling for {config.throttle_delay}s"
            )
            time.sleep(config.throttle_delay)


def find_phase_directory(phase: int, project_root: Path) -> Optional[Path]:
    phase_dir_mapping = {
        1: "phase1-validation",
        2: "phase2-extraction",
        3: "phase3-chunking",
        4: "phase4-tts",
        5: "phase5-enhancement",
    }
    phase_dir_name = phase_dir_mapping.get(phase, f"phase{phase}_*")
    matches = list(project_root.glob(phase_dir_name))
    logger.debug(
        f"Searching for phase {phase} directory in {project_root}; found: {[str(m) for m in matches]}"
    )
    return matches[0] if matches else None


def find_phase_main(phase_dir: Path, phase: int) -> Optional[Path]:
    sub_dir_mapping = {
        1: "phase1_validation",
        2: "phase2_extraction",
        3: "phase3_chunking",
        4: "phase4_tts",
        5: "phase5_enhancement",
    }
    sub_dir = sub_dir_mapping.get(phase, f"phase{phase}_chunking")
    main_files = {
        1: ["validation.py", "main.py"],
        2: ["extraction.py", "main.py"],
        3: ["chunking.py", "main.py"],
        4: ["tts.py", "main.py"],
        5: ["enhancement.py", "main.py"],
    }.get(phase, ["main.py"])
    for mf in main_files:
        main_path = (
            phase_dir / mf
            if mf != "main.py"
            else phase_dir / "src" / sub_dir / "main.py"
        )
        if main_path.exists():
            return main_path
    logger.warning(f"No main script found in {phase_dir}")
    return None


def get_venv_python(phase_dir: Path) -> Optional[str]:
    venv_paths = [
        phase_dir / ".venv" / "bin" / "python",  # Unix
        phase_dir / ".venv" / "Scripts" / "python.exe",  # Windows
    ]
    for p in venv_paths:
        if p.exists():
            logger.info(f"Found venv Python: {p}")
            return str(p)
    logger.warning(f"No venv found in {phase_dir}; using system Python")
    return sys.executable


def _run_subprocess(
    venv_python: str,
    main_script: Path,
    args: List[str],
    config: BatchConfig,
    metadata: BatchMetadata,
    phase: int,
) -> bool:
    # Run as module for relative imports (e.g., -m phase3_chunking.main)
    sub_dir = {
        1: "phase1_validation",
        2: "phase2_extraction",
        3: "phase3_chunking",
        4: "phase4_tts",
        5: "phase5_enhancement",
    }.get(phase, f"phase{phase}_chunking")
    cmd = [venv_python, "-m", f"{sub_dir}.main"] + args
    cmd_str = " ".join(cmd)
    logger.debug(f"Running Phase {phase} subprocess as module: {cmd_str}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.phase_timeout,
            check=True,
        )
        logger.info(f"Phase {phase} output: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"Phase {phase} stderr: {result.stderr.strip()}")
        return True
    except subprocess.TimeoutExpired:
        err_msg = f"Phase {phase} timed out after {config.phase_timeout}s"
        metadata.error_message = err_msg
        metadata.errors.append(err_msg)
        logger.error(err_msg)
    except subprocess.CalledProcessError as e:
        err_msg = (
            f"Phase {phase} failed (code {e.returncode}): {e.stderr.strip()}"
        )
        metadata.error_message = err_msg
        metadata.errors.append(err_msg)
        logger.error(err_msg)
    except Exception as e:
        err_msg = f"Phase {phase} subprocess error: {str(e)}"
        metadata.error_message = err_msg
        metadata.errors.append(err_msg)
        logger.error(err_msg)
    return False


def run_phase_for_file(
    phase: int,
    file_path: Path,
    file_id: str,
    config: BatchConfig,
    metadata: BatchMetadata,
) -> bool:
    phase_start = time.perf_counter()
    phase_dir = find_phase_directory(phase, get_project_root())
    if not phase_dir:
        metadata.error_message = f"Phase {phase} directory not found"
        return False
    main_script = find_phase_main(phase_dir, phase)
    if not main_script:
        metadata.error_message = f"Phase {phase} main script not found"
        return False
    venv_python = get_venv_python(phase_dir)
    if not venv_python:
        metadata.error_message = f"Phase {phase} no valid Python environment"
        return False
    # Base args for all phases
    args = [f"--file_id={file_id}", f"--json_path={config.pipeline_json}"]
    if phase == 1:
        # Phase 1: Validation - needs the original file
        args.append(f"--file={str(file_path)}")

    elif phase == 2:
        # Phase 2: Extraction - loads from JSON or needs file path
        # Assume it loads from Phase 1 via JSON; no extra args needed
        pass  # Explicit pass for empty block

    elif phase == 3:
        # Phase 3: Chunking - creates chunks from single text file
        # It will load text_path from Phase 2 via JSON automatically
        # Only add --strict if explicitly configured or Phase 2 failed
        if config.resume_enabled:
            try:
                with open(config.pipeline_json, "r") as f:
                    pipeline = json.load(f)
                phase2_data = (
                    pipeline.get("phase2", {})
                    .get("files", {})
                    .get(file_id, {})
                )
                # Only add strict if Phase 2 explicitly failed (not just missing)
                if phase2_data and phase2_data.get("status") == "failed":
                    args.append("--strict")
            except Exception as e:
                logger.warning(f"Could not check Phase 2 status: {e}")

        # Run Phase 3 once per file (it creates multiple chunks internally)
        success = _run_subprocess(
            venv_python, main_script, args, config, metadata, phase
        )
        phase_duration = time.perf_counter() - phase_start
        metadata.add_phase_metric(phase, phase_duration)
        if success:
            metadata.phases_completed.append(phase)
        return success

    elif phase == 4:
        # Phase 4: TTS - processes each chunk individually
        try:
            with open(config.pipeline_json, "r") as f:
                pipeline = json.load(f)
            chunk_paths = (
                pipeline.get("phase3", {})
                .get("files", {})
                .get(file_id, {})
                .get("chunk_paths", [])
            )
        except Exception as e:
            metadata.error_message = f"Failed to load chunks for Phase 4: {e}"
            return False

        if not chunk_paths:
            metadata.error_message = (
                f"No chunks found for Phase 4 (file_id: {file_id})"
            )
            return False

        # Process each chunk
        for idx, chunk_path in enumerate(chunk_paths):
            chunk_args = args + [
                f"--chunk_id={idx}",
                f"--text_path={chunk_path}",
            ]
            if not _run_subprocess(
                venv_python, main_script, chunk_args, config, metadata, phase
            ):
                # Record which chunk failed but continue with others
                logger.error(f"Phase 4 failed on chunk {idx} for {file_id}")
                metadata.errors.append(f"Chunk {idx} failed in Phase 4")
            else:
                metadata.chunk_ids.append(idx)

        phase_duration = time.perf_counter() - phase_start
        metadata.add_phase_metric(phase, phase_duration)

        # Consider phase successful if at least some chunks processed
        if metadata.chunk_ids:
            metadata.phases_completed.append(phase)
            return True
        return False

    elif phase == 5:
        # Phase 5: Enhancement - processes all audio from Phase 4
        try:
            with open(config.pipeline_json, "r") as f:
                pipeline = json.load(f)
            audio_paths = (
                pipeline.get("phase4", {})
                .get("files", {})
                .get(file_id, {})
                .get("chunk_audio_paths", [])
            )
        except Exception as e:
            metadata.error_message = (
                f"Failed to load audio paths for Phase 5: {e}"
            )
            return False

        if not audio_paths:
            metadata.error_message = (
                f"No audio files found for Phase 5 (file_id: {file_id})"
            )
            return False

        # Pass all audio paths to Phase 5
        args.append(f"--audio_paths={','.join(str(p) for p in audio_paths)}")

    else:
        metadata.error_message = f"Unsupported phase {phase}"
        return False
    # Run for phases 1, 2, 5 (single execution per file)
    success = _run_subprocess(
        venv_python, main_script, args, config, metadata, phase
    )
    phase_duration = time.perf_counter() - phase_start
    metadata.add_phase_metric(phase, phase_duration)

    if success:
        metadata.phases_completed.append(phase)

    return success


def verify_phase_environments(
    phases: List[int], project_root: Path
) -> Dict[int, bool]:
    results = {}
    for phase in phases:
        try:
            phase_dir = find_phase_directory(phase, project_root)
            if not phase_dir:
                results[phase] = False
                logger.warning(f"Phase {phase}: Directory not found")
                continue
            venv_python = get_venv_python(phase_dir)
            if not venv_python:
                results[phase] = False
                logger.warning(f"Phase {phase}: No valid Python venv")
                continue
            version_result = subprocess.run(
                [venv_python, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if version_result.returncode != 0:
                results[phase] = False
                logger.warning(f"Phase {phase}: Python version check failed")
                continue
            version_str = version_result.stdout.strip().split()[1]
            major_minor = ".".join(version_str.split(".")[:2])
            toml_path = phase_dir / "pyproject.toml"
            if toml_path.exists():
                try:
                    with open(toml_path, "rb") as f:
                        project_data = tomllib.load(f)
                    required_python = (
                        project_data.get("tool", {})
                        .get("poetry", {})
                        .get("dependencies", {})
                        .get("python", "")
                        or ">=" + major_minor
                    )
                    required = required_python.strip()
                    current = version.parse(major_minor)
                    if required.startswith("^"):
                        required_ver = version.parse(required[1:])
                        if (
                            current < required_ver
                            or current.major != required_ver.major
                        ):
                            results[phase] = False
                            logger.warning(
                                f"Phase {phase}: Python version mismatch (^ {required_ver})"
                            )
                            continue
                    elif required.startswith(">="):
                        required_ver = version.parse(required[2:])
                        if current < required_ver:
                            results[phase] = False
                            logger.warning(
                                f"Phase {phase}: Python version too low (>= {required_ver})"
                            )
                            continue
                    elif required.startswith("<"):
                        required_ver = version.parse(required[1:])
                        if current >= required_ver:
                            results[phase] = False
                            logger.warning(
                                f"Phase {phase}: Python version too high (< {required_ver})"
                            )
                            continue
                    # Add other operators as needed
                except Exception as e:
                    logger.warning(
                        f"Phase {phase}: pyproject.toml parse failed - {e}; assuming compatible"
                    )
            results[phase] = True
        except Exception as e:
            logger.warning(f"Phase {phase}: Environment check failed - {e}")
            results[phase] = False
    return results


async def process_file(
    file_path: Path, config: BatchConfig, nursery, project_root: Path
) -> BatchMetadata:
    file_id = file_path.stem
    metadata = BatchMetadata(file_id)
    metadata.mark_started()

    # Load existing pipeline for resume checks
    if config.resume_enabled:
        try:
            with open(config.pipeline_json, "r") as f:
                pipeline = json.load(f)
            existing_data = (
                pipeline.get("batch", {}).get("files", {}).get(file_id, {})
            )
            metadata.phases_completed = existing_data.get(
                "phases_completed", []
            )
        except Exception as e:
            logger.warning(f"Resume load failed for {file_id}: {e}")

    for phase in config.phases_to_run:
        if phase in metadata.phases_completed:
            logger.info(f"Skipping completed Phase {phase} for {file_id}")
            continue
        success = run_phase_for_file(
            phase, file_path, file_id, config, metadata
        )
        if not success:
            logger.error(
                f"Phase {phase} failed for {file_id}; continuing to next"
            )

    metadata.mark_completed()
    return metadata


def load_config(config_path: str, project_root: Path) -> BatchConfig:
    try:
        config_file = Path(config_path).resolve()
        if not config_file.exists():
            logger.warning(
                f"Config file {config_path} not found, using defaults"
            )
            return BatchConfig()
        with open(config_file, "r") as f:
            data = yaml.safe_load(f) or {}
        config = BatchConfig(**data)
        # Make paths absolute
        config.input_dir = str(project_root / config.input_dir)
        config.pipeline_json = str(project_root / config.pipeline_json)
        config.log_file = str(project_root / config.log_file)
        return config
    except Exception as e:
        logger.warning(f"Config load failed: {e}; using defaults")
        return BatchConfig()


def update_pipeline_json(
    config: BatchConfig,
    summary: BatchSummary,
    metadata_list: List[BatchMetadata],
):
    try:
        with open(config.pipeline_json, "r") as f:
            pipeline = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pipeline = {}
    # Merge batch data
    if "batch" not in pipeline:
        pipeline["batch"] = {"files": {}, "summary": summary.dict()}
    for m in metadata_list:
        pipeline["batch"]["files"][m.file_id] = m.dict()
    with open(config.pipeline_json, "w") as f:
        json.dump(pipeline, f, indent=4)
    logger.info("Updated pipeline.json with batch summary and metadata")


def cleanup_old_artifacts(pipeline_json: str, days: int = 7):
    try:
        with open(pipeline_json, "r") as f:
            pipeline = json.load(f)
        cleaned = []
        cutoff = time.time() - (days * 86400)  # seconds in days
        for section in pipeline.values():
            if isinstance(section, dict) and "artifacts" in section:
                for art in list(section["artifacts"]):
                    art_path = Path(art)
                    if art_path.exists() and art_path.stat().st_mtime < cutoff:
                        art_path.unlink()
                        cleaned.append(str(art_path))
        logger.info(f"Cleaned {len(cleaned)} old artifacts: {cleaned}")
        if "orchestration" not in pipeline:
            pipeline["orchestration"] = {}
        if "cleanup" not in pipeline["orchestration"]:
            pipeline["orchestration"]["cleanup"] = []
        pipeline["orchestration"]["cleanup"].extend(cleaned)
        with open(pipeline_json, "w") as f:
            json.dump(pipeline, f, indent=4)
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")


def render_rich_summary(
    summary: BatchSummary, metadata_list: List[BatchMetadata]
):
    console = Console()
    table = Table(title="Batch Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Total Files", str(summary.total_files))
    table.add_row("Successful", str(summary.successful_files))
    table.add_row("Partial", str(summary.partial_files))
    table.add_row("Failed", str(summary.failed_files))
    table.add_row("Duration", f"{summary.total_duration:.2f}s")
    table.add_row(
        "Avg CPU",
        f"{summary.avg_cpu_usage:.1f}%" if summary.avg_cpu_usage else "N/A",
    )
    table.add_row("Status", summary.status)

    console.print(table)

    # Per-file details
    for m in metadata_list:
        console.print(f"\nFile: {m.file_id} - Status: {m.status}")
        if m.error_message:
            console.print(f"Error: {m.error_message}", style="red")
        for err in m.errors:
            console.print(f" - {err}", style="red")


async def main_async():
    project_root = get_project_root()
    logger.info(f"Project root detected: {project_root}")

    parser = argparse.ArgumentParser(
        description="Batch Processing for Audiobook Pipeline"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config YAML"
    )
    args = parser.parse_args()

    config = load_config(args.config, project_root)
    setup_logging(config)

    env_results = verify_phase_environments(config.phases_to_run, project_root)
    if not all(env_results.values()):
        logger.warning(
            "Some phase environments invalid; proceeding with valid phases"
        )  # Changed to warning for resilience

    input_files = list(Path(config.input_dir).glob("*"))
    if not input_files:
        logger.warning(f"No input files found in {config.input_dir}")
        return 0

    stop_event = threading.Event()
    monitor_thread = threading.Thread(
        target=monitor_cpu, args=(config, stop_event)
    )
    monitor_thread.start()

    overall_start = time.perf_counter()
    cpu_readings = []
    metadata_list = []

    async with trio.open_nursery() as nursery:
        pbar = tqdm(total=len(input_files), desc="Processing files")
        for file_path in input_files:
            metadata = await process_file(
                file_path, config, nursery, project_root
            )
            metadata_list.append(metadata)
            pbar.update(1)

        while any(m.status == "running" for m in metadata_list):
            await trio.sleep(0.5)
            completed = sum(1 for m in metadata_list if m.status != "running")
            pbar.update(completed - pbar.n)
            cpu_readings.append(psutil.cpu_percent(interval=0.1))

    total_duration = time.perf_counter() - overall_start
    avg_cpu = sum(cpu_readings) / len(cpu_readings) if cpu_readings else None
    summary = BatchSummary(
        total_files=len(metadata_list),
        successful_files=sum(
            1 for m in metadata_list if m.status == "success"
        ),
        partial_files=sum(1 for m in metadata_list if m.status == "partial"),
        failed_files=sum(1 for m in metadata_list if m.status == "failed"),
        total_duration=total_duration,
        avg_cpu_usage=avg_cpu,
        errors=[m.error_message for m in metadata_list if m.error_message]
        + sum((m.errors for m in metadata_list), []),
        timestamps={
            "start": min(
                m.timestamps.get("start", float("inf")) for m in metadata_list
            ),
            "end": max(m.timestamps.get("end", 0) for m in metadata_list),
        },
    )
    summary.artifacts.append(config.log_file)
    update_pipeline_json(config, summary, metadata_list)
    cleanup_old_artifacts(config.pipeline_json, config.cleanup_days)
    render_rich_summary(summary, metadata_list)

    stop_event.set()
    monitor_thread.join()

    return (
        0
        if summary.status == "success"
        else 2 if summary.status == "partial" else 1
    )


def main():
    return trio.run(main_async)


if __name__ == "__main__":
    sys.exit(main())
