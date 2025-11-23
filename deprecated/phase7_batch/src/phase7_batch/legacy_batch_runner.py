# Deprecated: Superseded by Phase 7 (Trio + Phase 6 orchestrator).
import argparse
import json
import logging
import time
from pathlib import Path
import subprocess
import threading
import sys
import os
import toml
import trio
from tqdm import tqdm
import psutil
import yaml
from typing import List, Optional, Dict, Any, Tuple
from packaging import version
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)


class BatchConfig:
    def __init__(self, **data):
        self.log_level = data.get("log_level", "INFO")
        self.log_file = data.get("log_file", "batch.log")
        self.input_dir = data.get("input_dir", "input")
        self.pipeline_json = data.get("pipeline_json", "../pipeline.json")
        self.max_workers = data.get(
            "max_workers", max(1, psutil.cpu_count(logical=False) - 1)
        )
        self.phase_timeout = data.get("phase_timeout", 600)  # 10 min
        self.resume_enabled = data.get("resume_enabled", True)
        self.phases_to_run = data.get("phases_to_run", [1, 2, 3, 4, 5])
        self.batch_size = data.get("batch_size", None)
        self.cpu_threshold = data.get("cpu_threshold", 95.0)
        self.throttle_delay = data.get("throttle_delay", 0.5)
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


def get_project_root() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent.parent
    )  # Adjust based on structure


def find_phase_directory(
    phase: int, project_root: Optional[Path] = None
) -> Optional[Path]:
    try:
        if project_root is None:
            project_root = get_project_root()
        logger.debug(f"Using project_root: {project_root} for phase {phase}")

        phase_dir_mapping = {
            1: "phase1-validation",
            2: "phase2-extraction",
            3: "phase3-chunking",
            4: "phase4_tts",
            5: "phase5_enhancement",
        }
        mapped_name = phase_dir_mapping.get(phase)
        if mapped_name:
            exact_dir = project_root / mapped_name
            if exact_dir.exists() and exact_dir.is_dir():
                logger.debug(
                    f"Found exact match for phase {phase}: {exact_dir}"
                )
                return exact_dir

        # Broad glob fallback for variations
        matches = list(project_root.glob(f"phase{phase}*"))
        logger.debug(
            f"Searching for phase {phase} in {project_root}; found: {[str(m) for m in matches]}"
        )
        if matches:
            if len(matches) > 1:
                logger.warning(
                    f"Multiple matches for phase {phase}: {matches}; using {matches[0]}"
                )
            return matches[0]
        else:
            logger.warning(
                f"Phase {phase}: Directory not found in {project_root}"
            )
            return None
    except Exception as e:
        logger.error(f"Directory discovery failed for phase {phase}: {e}")
        return None


def find_phase_main(phase_dir: Path, phase: int) -> Optional[Path]:
    sub_dir_mapping = {
        1: "phase1_validation",
        2: "phase2_extraction",
        3: "phase3_chunking",
        4: "phase4_tts",
        5: "phase5_enhancement",
    }
    sub_dir = sub_dir_mapping.get(phase, f"phase{phase}")
    main_files = {
        1: ["validation.py", "main.py"],
        2: ["extraction.py", "main.py"],
        3: ["chunking.py", "main.py"],
        4: ["tts.py", "main.py"],
        5: ["enhancement.py", "main.py"],
    }.get(phase, ["main.py"])
    search_roots = [phase_dir / "src" / sub_dir, phase_dir / "src", phase_dir]
    for mf in main_files:
        for root in search_roots:
            main_path = root / mf
            if main_path.exists():
                return main_path
    logger.warning(f"No main script found in {phase_dir}")
    return None


def get_venv_python(phase_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    logger.info(f"=== DEBUG: Searching for Python in {phase_dir} ===")
    logger.info(f"Phase directory name: {phase_dir.name}")

    # Standard venv
    venv_paths = [
        phase_dir / ".venv" / "bin" / "python",
        phase_dir / ".venv" / "Scripts" / "python.exe",
    ]
    for p in venv_paths:
        logger.debug(f"Checking venv path: {p}")
        if p.exists():
            logger.info(f"Found venv Python: {p}")
            return str(p), None

    # Conda detection - use exact directory name
    conda_env_name = phase_dir.name  # "phase4_tts" not "phase4_env"
    logger.info(f"Looking for Conda env named: {conda_env_name}")

    # Check what's actually in the Conda env directory
    conda_env_path = Path.home() / "miniconda3" / "envs" / conda_env_name
    if conda_env_path.exists():
        logger.info(f"Conda env directory exists: {conda_env_path}")
        logger.info(
            f"Contents: {[str(item) for item in list(conda_env_path.iterdir())[:5]]}"
        )  # First 5 items

        # Check all possible Python locations
        possible_pythons = [
            conda_env_path / "Scripts" / "python.exe",
            conda_env_path / "python.exe",
            conda_env_path / "bin" / "python",
            conda_env_path / "python",
        ]

        for py_path in possible_pythons:
            logger.debug(f"Checking: {py_path} - Exists: {py_path.exists()}")
            if py_path.exists():
                logger.info(f"✓ Found Conda Python: {py_path}")
                return str(py_path), conda_env_name

    # Check multiple locations
    conda_bases = [
        Path.home() / "miniconda3",
        Path.home() / "anaconda3",
    ]

    for base in conda_bases:
        logger.debug(f"Checking Conda base: {base}")
        # Windows
        env_path = base / "envs" / conda_env_name / "Scripts" / "python.exe"
        logger.debug(f"  Trying: {env_path}")
        if env_path.exists():
            logger.info(f"✓ Found Conda Python: {env_path}")
            return str(env_path), conda_env_name

        # Unix
        env_path = base / "envs" / conda_env_name / "bin" / "python"
        logger.debug(f"  Trying: {env_path}")
        if env_path.exists():
            logger.info(f"✓ Found Conda Python: {env_path}")
            return str(env_path), conda_env_name

    # Check CONDA_PREFIX as fallback
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        env_python = Path(conda_prefix) / "Scripts" / "python.exe"
        if not env_python.exists():
            env_python = Path(conda_prefix) / "bin" / "python"
        if env_python.exists():
            env_name = os.environ.get("CONDA_DEFAULT_ENV", conda_env_name)
            logger.info(
                f"Found Conda Python from CONDA_PREFIX: {env_python} (env: {env_name})"
            )
            return str(env_python), env_name

    logger.warning(f"No venv/Conda in {phase_dir}; fallback to system Python")
    return sys.executable, None


def monitor_resources(stop_event: threading.Event):
    while not stop_event.is_set():
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            logger.warning(f"CPU >80% ({cpu_percent}%); throttling")
            time.sleep(1)  # Simple throttle


def _run_subprocess(
    venv_python: str,
    env_identifier: Optional[str],
    main_script: Path,
    args: List[str],
    config: BatchConfig,
    metadata: BatchMetadata,
    phase: int,
) -> bool:
    start = time.perf_counter()

    # Set cwd to phase directory - FIXED
    phase_dir = (
        main_script.parent.parent.parent
    )  # src/phaseX_xxx -> phaseX_xxx

    # Prepare environment variables for subprocess
    env = os.environ.copy()

    # Set batch mode flag for Phase 4 (prevents parallel processing conflicts)
    if phase == 4:
        env["AUDIOBOOK_BATCH_MODE"] = "1"
        logger.debug(
            "Set AUDIOBOOK_BATCH_MODE=1 for Phase 4 (serial chunk processing)"
        )

    # If we have a conda env name, use conda run
    if env_identifier:
        cmd = [
            "conda",
            "run",
            "-n",
            env_identifier,
            "--no-capture-output",
            "python",
            str(main_script),
        ] + args
    else:
        # Direct execution for venv or system python
        cmd = [venv_python, str(main_script)] + args

    logger.debug(
        f"Executing Phase {phase}: {' '.join(cmd)} from cwd {phase_dir}"
    )
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.phase_timeout,
            cwd=str(phase_dir),  # FIXED: Set working directory
            env=env,  # ADDED: Pass environment variables
        )
        if result.returncode != 0:
            err_msg = f"Phase {phase} failed (code {result.returncode}): {result.stderr.strip()}"
            logger.error(err_msg)
            metadata.errors.append(err_msg)
            return False
        logger.info(f"Phase {phase} output: {result.stdout.strip()}")
        duration = time.perf_counter() - start
        metadata.add_phase_metric(phase, duration)
        return True
    except subprocess.TimeoutExpired:
        err_msg = f"Phase {phase} timed out after {config.phase_timeout}s"
        logger.error(err_msg)
        metadata.errors.append(err_msg)
        return False
    except Exception as e:
        err_msg = f"Subprocess error in Phase {phase}: {str(e)}"
        logger.error(err_msg)
        metadata.errors.append(err_msg)
        return False


def run_phase_for_file(
    phase: int,
    file_path: Path,
    file_id: str,
    config: BatchConfig,
    metadata: BatchMetadata,
) -> bool:
    phase_dir = find_phase_directory(phase)
    if not phase_dir:
        err_msg = f"Phase {phase} directory not found"
        logger.error(err_msg)
        metadata.errors.append(err_msg)
        return False

    venv_python, env_identifier = get_venv_python(phase_dir)
    if not venv_python:
        err_msg = f"No Python found for Phase {phase}"
        logger.error(err_msg)
        metadata.errors.append(err_msg)
        return False

    main_script = find_phase_main(phase_dir, phase)
    if not main_script:
        err_msg = f"No main script for Phase {phase}"
        logger.error(err_msg)
        metadata.errors.append(err_msg)
        return False

    args = [f"--file_id={file_id}"]
    # FIXED: Only add --json_path for phases that support it (not Phase 4)
    if phase in [1, 2, 3, 5]:
        args.append(f"--json_path={config.pipeline_json}")

    # Phase-specific args - FIXED for Phase 1
    if phase == 1:
        args.append(f"--file={str(file_path)}")

    if phase in [1, 2, 3, 5]:
        if not _run_subprocess(
            venv_python,
            env_identifier,
            main_script,
            args,
            config,
            metadata,
            phase,
        ):
            return False
        metadata.phases_completed.append(phase)
        return True

    elif phase == 4:
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
            err_msg = f"Failed to load Phase 3 chunks: {e}"
            logger.error(err_msg)
            metadata.errors.append(err_msg)
            return False

        if not chunk_paths:
            err_msg = "No chunks for Phase 4"
            logger.error(err_msg)
            metadata.errors.append(err_msg)
            return False

        failed_chunks = []
        for idx, chunk_path in enumerate(chunk_paths):
            chunk_args = args + [f"--chunk_id={idx}"]
            if not _run_subprocess(
                venv_python,
                env_identifier,
                main_script,
                chunk_args,
                config,
                metadata,
                phase,
            ):
                failed_chunks.append(idx)
                logger.error(f"Phase 4 failed on chunk {idx} for {file_id}")
                if len(failed_chunks) > len(chunk_paths) // 2:
                    logger.warning(
                        f"Aborting Phase 4: {len(failed_chunks)}/{len(chunk_paths)} chunks failed"
                    )
                    break

        if len(chunk_paths) - len(failed_chunks) > 0:
            metadata.chunk_ids = [
                i for i in range(len(chunk_paths)) if i not in failed_chunks
            ]
            metadata.phases_completed.append(phase)
            if failed_chunks:
                metadata.errors.append(
                    f"Phase 4 partial: {len(failed_chunks)} chunks failed: {failed_chunks}"
                )
            return True
        return False


async def process_file(
    file_path: Path,
    config: BatchConfig,
) -> BatchMetadata:
    file_id = file_path.stem
    metadata = BatchMetadata(file_id)
    metadata.mark_started()

    # Check resume - FIXED JSON path
    if config.resume_enabled:
        try:
            with open(config.pipeline_json, "r") as f:
                pipeline = json.load(f)
            existing = (
                pipeline.get("batch", {}).get("files", {}).get(file_id, {})
            )
            metadata.phases_completed = existing.get("phases_completed", [])
        except Exception as e:
            logger.warning(f"Resume load failed: {e}; starting fresh")

    for phase in config.phases_to_run:
        if phase in metadata.phases_completed:
            logger.info(f"Skipping completed Phase {phase} for {file_id}")
            continue
        success = run_phase_for_file(
            phase, file_path, file_id, config, metadata
        )
        if not success:
            metadata.error_message = f"Phase {phase} failed"
            continue

    metadata.mark_completed()
    return metadata


def update_pipeline_json(
    config: BatchConfig,
    summary: BatchSummary,
    metadata_list: List[BatchMetadata],
):
    try:
        json_path = Path(config.pipeline_json)
        if json_path.exists():
            with open(json_path, "r") as f:
                pipeline = json.load(f)
        else:
            pipeline = {}

        if "batch" not in pipeline:
            pipeline["batch"] = {}

        pipeline["batch"]["summary"] = summary.dict()
        pipeline["batch"]["files"] = {
            m.file_id: m.dict() for m in metadata_list
        }

        with open(json_path, "w") as f:
            json.dump(pipeline, f, indent=4)
        logger.info("Updated pipeline.json with batch summary and metadata")
    except Exception as e:
        logger.error(f"Failed to update pipeline.json: {e}")


def cleanup_old_artifacts(json_path: str):
    try:
        with open(json_path, "r") as f:
            pipeline = json.load(f)

        # Placeholder cleanup logic; e.g., remove >7 days old
        cleaned = []  # Simulate
        logger.info(f"Cleaned {len(cleaned)} old artifacts: {cleaned}")
        if "orchestration" not in pipeline:
            pipeline["orchestration"] = {}
        if "cleanup" not in pipeline["orchestration"]:
            pipeline["orchestration"]["cleanup"] = []
        pipeline["orchestration"]["cleanup"].extend(cleaned)
        with open(json_path, "w") as f:
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


def verify_phase_environments(phases: List[int]) -> Dict[int, bool]:
    results = {}
    for phase in phases:
        try:
            phase_dir = find_phase_directory(phase)
            if not phase_dir:
                results[phase] = False
                continue
            venv_python, env_identifier = get_venv_python(phase_dir)
            if not venv_python:
                results[phase] = False
                continue
            # For conda, test with conda run if needed, but simplify to version check
            version_result = subprocess.run(
                [venv_python, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if version_result.returncode != 0:
                results[phase] = False
                continue
            version_str = version_result.stdout.strip().split()[1]
            major_minor = ".".join(version_str.split(".")[:2])
            toml_path = phase_dir / "pyproject.toml"
            if toml_path.exists():
                project_data = toml.load(toml_path)
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
                        continue
            results[phase] = True
        except Exception as e:
            logger.warning(f"Phase {phase}: Environment check failed - {e}")
            results[phase] = False
    return results


def load_config(config_path: str) -> BatchConfig:
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(
                f"Config file {config_path} not found, using defaults"
            )
            return BatchConfig()
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        return BatchConfig(**data)
    except Exception as e:
        logger.warning(f"Config load failed: {e}; using defaults")
        return BatchConfig()


async def main_async():
    parser = argparse.ArgumentParser(
        description="Batch Processing for Audiobook Pipeline"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config YAML"
    )
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config)

    env_results = verify_phase_environments(config.phases_to_run)
    invalid_phases = [p for p, valid in env_results.items() if not valid]
    if invalid_phases:
        logger.warning(
            f"Some phase environments invalid: {invalid_phases}; proceeding with valid phases"
        )

    input_files = list(Path(config.input_dir).glob("*"))
    if not input_files:
        logger.warning("No input files found")
        return 0

    stop_event = threading.Event()
    monitor_thread = threading.Thread(
        target=monitor_resources, args=(stop_event,)
    )
    monitor_thread.start()

    overall_start = time.perf_counter()
    cpu_readings = []
    metadata_list = []

    pbar = tqdm(total=len(input_files), desc="Processing files")

    async def collect_result(file_path, pbar):
        result = await process_file(file_path, config)
        metadata_list.append(result)
        pbar.update(1)  # FIXED: Update progress

    async with trio.open_nursery() as nursery:
        for file_path in input_files:
            nursery.start_soon(collect_result, file_path, pbar)

        # FIXED: Monitor CPU during processing
        while len(metadata_list) < len(input_files):
            await trio.sleep(1)
            cpu_readings.append(psutil.cpu_percent(interval=0.1))

    pbar.close()

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
        errors=[err for m in metadata_list for err in m.errors],
        timestamps={
            "start": min(
                m.timestamps.get("start", float("inf")) for m in metadata_list
            ),
            "end": max(m.timestamps.get("end", 0) for m in metadata_list),
        },
    )
    summary.artifacts.append(config.log_file)
    update_pipeline_json(config, summary, metadata_list)
    cleanup_old_artifacts(config.pipeline_json)
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
