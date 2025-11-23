import argparse
import logging
import json
import time
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import psutil
import yaml
import sys
from typing import List, Optional, Dict
import os
import toml
import threading


# Assume models.py defines these; stubbed for completeness
class BatchConfig:
    def __init__(self, **data):
        self.log_level = data.get("log_level", "INFO")
        self.log_file = data.get("log_file", "batch.log")
        self.input_dir = data.get("input_dir", "input")
        self.pipeline_json = data.get("pipeline_json", "../pipeline.json")
        self.max_workers = data.get("max_workers", 4)
        self.phase_timeout = data.get("phase_timeout", 300)
        self.resume_enabled = data.get("resume_enabled", True)
        self.phases_to_run = data.get("phases_to_run", [1, 2, 3, 4, 5])
        self.batch_size = data.get("batch_size", None)
        self.cpu_threshold = data.get("cpu_threshold", 80)
        self.throttle_delay = data.get("throttle_delay", 2.0)

    def model_dump(self):
        return vars(self)


class BatchMetadata:
    def __init__(self, file_id=None):
        self.file_id = file_id
        self.status = "pending"
        self.phases_completed = []
        self.chunk_ids = []
        self.phase_metrics = {}
        self.error_message = None
        self.timestamps = {}
        self.duration = None

    def mark_started(self):
        self.status = "running"
        self.timestamps["start"] = time.time()

    def mark_completed(self):
        self.timestamps["end"] = time.time()
        self.duration = self.timestamps["end"] - self.timestamps["start"]
        self.status = "success" if not self.error_message else "failed"

    def add_phase_metric(self, phase, duration, error=None):
        self.phase_metrics[phase] = {"duration": duration, "error": error}

    def model_dump(self):
        return vars(self)


class BatchSummary:
    status = "pending"
    total_files = 0
    successful_files = 0
    partial_files = 0
    failed_files = 0
    total_duration = 0.0
    avg_cpu_usage = None
    errors = []
    artifacts = []
    timestamps = {}

    @classmethod
    def from_metadata_list(cls, metadata_list, total_duration, avg_cpu):
        obj = cls()
        obj.total_files = len(metadata_list)
        obj.successful_files = sum(
            1 for m in metadata_list if m.status == "success"
        )
        obj.partial_files = sum(
            1 for m in metadata_list if m.status == "partial"
        )
        obj.failed_files = sum(
            1 for m in metadata_list if m.status == "failed"
        )
        obj.total_duration = total_duration
        obj.avg_cpu_usage = avg_cpu
        obj.errors = [
            m.error_message for m in metadata_list if m.error_message
        ]
        obj.status = (
            "success"
            if obj.failed_files == 0
            else "partial" if obj.partial_files > 0 else "failed"
        )
        obj.timestamps = {
            "start": min(
                m.timestamps.get("start", float("inf")) for m in metadata_list
            ),
            "end": max(m.timestamps.get("end", 0) for m in metadata_list),
        }
        return obj


logger = logging.getLogger(__name__)


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


def setup_logging(config: BatchConfig):
    numeric_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.getLogger().handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    file_handler = logging.FileHandler(config.log_file)
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def monitor_cpu(config: BatchConfig, stop_event: threading.Event):
    while not stop_event.is_set():
        cpu = psutil.cpu_percent(interval=1)
        if cpu > config.cpu_threshold:
            logger.warning(
                f"CPU {cpu:.1f}% > {config.cpu_threshold}%; throttling for {config.throttle_delay}s"
            )
            time.sleep(config.throttle_delay)


def find_phase_directory(phase: int) -> Optional[Path]:
    parent_dir = Path("..").resolve()
    logger.debug(f"Looking for phase {phase} directories in: {parent_dir}")
    phase_dir_mapping = {
        1: "phase1_validation",
        2: "phase2_extraction",
        3: "phase3_chunking",
        4: "phase4_tts",
        5: "phase5_enhancement",
    }
    if phase in phase_dir_mapping:
        exact_dir = parent_dir / phase_dir_mapping[phase]
        if exact_dir.exists():
            logger.info(f"Found phase {phase} directory: {exact_dir}")
            return exact_dir
    patterns = [
        f"phase{phase}_*",
        f"phase{phase}-*",
        f"phase_{phase}*",
        f"phase-{phase}*",
    ]
    for pattern in patterns:
        matches = list(parent_dir.glob(pattern))
        logger.debug(f"Pattern '{pattern}' found: {[str(m) for m in matches]}")
        if matches:
            phase_dir = matches[0]
            logger.info(f"Found phase {phase} directory: {phase_dir}")
            return phase_dir
    available_dirs = [
        d
        for d in parent_dir.iterdir()
        if d.is_dir() and "phase" in d.name.lower()
    ]
    logger.error(
        f"No directory found for phase {phase}. Available phase directories: {[d.name for d in available_dirs]}"
    )
    return None


def find_phase_main(phase_dir: Path, phase: int) -> Optional[Path]:
    src_patterns = [
        f"src/phase{phase}_*",
        f"src/phase{phase}-*",
        f"src/phase_{phase}*",
        f"src/phase-{phase}*",
    ]
    phase_main_files = {
        1: ["validation.py", "main.py"],
        2: ["extraction.py", "main.py"],
        3: ["main.py"],
        4: ["main.py"],
        5: ["main.py"],
    }
    main_files_to_try = phase_main_files.get(phase, ["main.py"])
    for pattern in src_patterns:
        matches = list(phase_dir.glob(pattern))
        if matches:
            src_dir = matches[0]
            logger.debug(f"Found src directory for phase {phase}: {src_dir}")
            for main_file in main_files_to_try:
                main_path = src_dir / main_file
                if main_path.exists():
                    logger.debug(
                        f"Found {main_file} for phase {phase}: {main_path}"
                    )
                    return main_path
    for main_file in main_files_to_try:
        main_path = phase_dir / main_file
        if main_path.exists():
            logger.debug(f"Found {main_file} in phase root: {main_path}")
            return main_path
    logger.error(f"No main file found for phase {phase} in {phase_dir}")
    logger.debug(f"Tried files: {main_files_to_try}")
    return None


def get_venv_python(phase_dir: Path) -> Optional[str]:
    result = subprocess.run(
        ["poetry", "env", "info", "--path"],
        cwd=str(phase_dir),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        logger.error(
            f"Failed to get venv path for {phase_dir}: {result.stderr}"
        )
        return None
    env_path = result.stdout.strip()
    if not env_path:
        logger.error(f"No venv found for {phase_dir}")
        return None
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    python_exe = "python.exe" if os.name == "nt" else "python"
    python_path = os.path.join(env_path, bin_dir, python_exe)
    if not os.path.exists(python_path):
        logger.error(f"Python executable not found in venv: {python_path}")
        return None
    logger.debug(f"Venv Python for {phase_dir}: {python_path}")
    return python_path


def get_absolute_file_path(file_path: str, phase_dir: Path) -> str:
    current_dir = Path.cwd()
    if not Path(file_path).is_absolute():
        abs_path = current_dir / file_path
    else:
        abs_path = Path(file_path)
    if not abs_path.exists():
        raise FileNotFoundError(f"Input file not found: {abs_path}")
    return str(abs_path.resolve())


def build_phase_command(
    phase: int,
    main_path: Path,
    file_path: str,
    venv_python: str,
    file_id: str,
    chunk_id: Optional[int] = None,
) -> List[str]:
    main_path_str = str(main_path)
    file_path_str = get_absolute_file_path(file_path, Path(main_path).parent)
    phase_args = {
        1: ["--file", file_path_str],
        2: ["--file_id", file_id],
        3: ["--file_id", file_id],
        4: (
            ["--file_id", file_id, "--chunk_id", str(chunk_id)]
            if chunk_id is not None
            else []
        ),
        5: (
            ["--chunk_id", str(chunk_id)]
            if chunk_id is not None
            else ["--input", file_path_str]
        ),  # Adjusted for chunk mode; assume Phase 5 supports --chunk_id or similar
    }
    args = phase_args.get(phase, [])
    return [venv_python, main_path_str] + args


def run_phase_for_file(
    file_path: str,
    phases: List[int],
    config: BatchConfig,
    metadata: BatchMetadata,
) -> BatchMetadata:
    file_id = Path(file_path).stem
    metadata.file_id = file_id
    metadata.mark_started()
    logger.info(f"Starting processing for {file_id}")

    try:
        for phase in phases:
            if phase in metadata.phases_completed:
                logger.debug(f"Skipping completed phase {phase} for {file_id}")
                continue

            retries = 0
            max_retries = 2
            while retries <= max_retries:
                phase_start = time.perf_counter()

                phase_dir = find_phase_directory(phase)
                if not phase_dir:
                    raise ValueError(f"Phase {phase} directory not found")

                main_path = find_phase_main(phase_dir, phase)
                if not main_path:
                    raise ValueError(f"Phase {phase} main script not found")

                venv_python = get_venv_python(phase_dir)
                if not venv_python:
                    raise RuntimeError(
                        f"No valid venv Python for phase {phase}"
                    )

                file_path_str = get_absolute_file_path(file_path, phase_dir)

                if phase > 3:  # Chunk-based phases
                    chunks = load_chunks_from_json(
                        config.pipeline_json, file_id
                    )
                    if not chunks:
                        raise ValueError(
                            f"No chunks found for {file_id} after Phase 3"
                        )
                    metadata.chunk_ids = []  # Reset for new phase
                    with ThreadPoolExecutor(
                        max_workers=config.max_workers
                    ) as chunk_exec:
                        chunk_futures = {
                            chunk_exec.submit(
                                run_chunk_phase,
                                phase,
                                main_path,
                                file_path_str,
                                venv_python,
                                file_id,
                                chunk_id,
                                config,
                            ): chunk_id
                            for chunk_id in range(len(chunks))
                        }
                        for future in as_completed(chunk_futures):
                            chunk_id = chunk_futures[future]
                            try:
                                result = future.result()
                                if result:
                                    metadata.chunk_ids.append(chunk_id)
                            except Exception as e:
                                logger.error(f"Chunk {chunk_id} failed: {e}")
                                metadata.error_message = (
                                    f"Chunk {chunk_id} error: {e}"
                                )
                                break
                    if metadata.error_message:
                        break

                else:  # File-based phases
                    cmd = build_phase_command(
                        phase, main_path, file_path_str, venv_python, file_id
                    )
                    logger.debug(
                        f"Executing phase {phase} in directory {phase_dir}"
                    )
                    logger.debug(f"Command: {' '.join(cmd)}")
                    result = subprocess.run(
                        cmd,
                        cwd=str(phase_dir),
                        capture_output=True,
                        text=True,
                        timeout=config.phase_timeout,
                    )
                    if result.returncode != 0:
                        retries += 1
                        if retries > max_retries:
                            error_msg = f"Phase {phase} failed after {retries} retries: {result.stderr.strip() or result.stdout.strip()}"
                            logger.error(error_msg)
                            metadata.add_phase_metric(
                                phase,
                                time.perf_counter() - phase_start,
                                error=error_msg,
                            )
                            metadata.error_message = error_msg
                            break
                        logger.warning(
                            f"Retry {retries}/{max_retries} for phase {phase}"
                        )
                        time.sleep(1)
                        continue

                phase_duration = time.perf_counter() - phase_start
                logger.info(f"Phase {phase} completed successfully")
                metadata.phases_completed.append(phase)
                metadata.add_phase_metric(phase, phase_duration)
                break

    except subprocess.TimeoutExpired:
        metadata.error_message = (
            f"Phase {phase} timed out after {config.phase_timeout}s"
        )
    except Exception as e:
        metadata.error_message = f"Unexpected error in phase {phase}: {str(e)}"

    metadata.mark_completed()
    return metadata


def run_chunk_phase(
    phase: int,
    main_path: Path,
    file_path: str,
    venv_python: str,
    file_id: str,
    chunk_id: int,
    config: BatchConfig,
) -> bool:
    start = time.perf_counter()
    cmd = build_phase_command(
        phase, main_path, file_path, venv_python, file_id, chunk_id
    )
    logger.debug(
        f"Executing chunk {chunk_id} for phase {phase}: {' '.join(cmd)}"
    )
    result = subprocess.run(
        cmd,
        cwd=str(Path(main_path).parent),
        capture_output=True,
        text=True,
        timeout=config.phase_timeout,
    )
    duration = time.perf_counter() - start
    logger.debug(f"Chunk {chunk_id} duration: {duration:.2f}s")
    return result.returncode == 0


def load_chunks_from_json(json_path: str, file_id: str) -> List[str]:
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        return (
            data.get("phase3", {})
            .get("files", {})
            .get(file_id, {})
            .get("chunk_paths", [])
        )
    except Exception as e:
        logger.error(f"Failed to load chunks from {json_path}: {e}")
        return []


def process_file_worker(args):
    file_path, phases, config = args
    file_id = Path(file_path).stem
    metadata = BatchMetadata(file_id=file_id)

    if config.resume_enabled:
        existing = load_existing_metadata(config.pipeline_json, file_id)
        if existing:
            metadata.phases_completed = existing.get("phases_completed", [])
            metadata.chunk_ids = existing.get("chunk_ids", [])

    return run_phase_for_file(file_path, phases, config, metadata)


def load_existing_metadata(json_path: str, file_id: str) -> Optional[Dict]:
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        return data.get("batch", {}).get("files", {}).get(file_id, {})
    except Exception as e:
        logger.debug(f"No existing metadata for {file_id}: {e}")
        return None


def update_pipeline_json(
    config: BatchConfig,
    summary: BatchSummary,
    metadata_list: List[BatchMetadata],
):
    pipeline_path = Path(config.pipeline_json)
    try:
        with open(pipeline_path, "r+") as f:
            data = json.load(f)
            data["phase6"] = (
                {  # Updated to "phase6" for consistency with guidelines
                    "status": summary.status,
                    "files": {
                        m.file_id: m.model_dump() for m in metadata_list
                    },
                    "metrics": vars(summary),  # Dump as dict
                    "timestamps": summary.timestamps,
                }
            )
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        logger.info(f"Updated {config.pipeline_json} with batch results")
    except Exception as e:
        logger.error(f"Failed to update pipeline.json: {e}")


def verify_phase_environments(phases: List[int]) -> Dict[int, bool]:
    results = {}
    for phase in phases:
        try:
            phase_dir = find_phase_directory(phase)
            if not phase_dir:
                logger.warning(f"Phase {phase}: Directory not found")
                results[phase] = False
                continue
            venv_python = get_venv_python(phase_dir)
            if not venv_python:
                results[phase] = False
                continue
            version_result = subprocess.run(
                [venv_python, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if version_result.returncode != 0:
                logger.warning(f"Phase {phase}: Failed to get Python version")
                results[phase] = False
                continue
            version_str = version_result.stdout.strip().split()[1]
            major_minor = ".".join(version_str.split(".")[:2])
            toml_path = phase_dir / "pyproject.toml"
            if not toml_path.exists():
                logger.warning(f"Phase {phase}: pyproject.toml not found")
                results[phase] = False
                continue
            project_data = toml.load(toml_path)
            required_python = (
                project_data.get("tool", {})
                .get("poetry", {})
                .get("dependencies", {})
                .get("python", "")
                or ">=" + major_minor
            )
            if not major_minor >= required_python.strip(">=").strip():
                logger.warning(
                    f"Phase {phase}: Python {major_minor} does not satisfy {required_python}"
                )
                results[phase] = False
                continue
            logger.debug(
                f"Phase {phase}: Python {major_minor} OK for {required_python}"
            )
            results[phase] = True
        except Exception as e:
            logger.warning(f"Phase {phase}: Environment check failed - {e}")
            results[phase] = False
    return results


def cleanup_old_artifacts(json_path: str, age_days: int = 7):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        current_time = time.time()
        for phase_key in data:
            artifacts = data[phase_key].get("artifacts", [])
            for art in artifacts[:]:
                art_path = Path(art)
                if (
                    art_path.exists()
                    and (current_time - art_path.stat().st_mtime)
                    > age_days * 86400
                ):
                    art_path.unlink()
                    artifacts.remove(art)
                    logger.info(f"Cleaned old artifact: {art}")
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 6: Batch Processing for Audiobook Pipeline"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--files",
        type=str,
        nargs="+",
        help="Specific files to process (overrides input_dir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without executing",
    )
    parser.add_argument(
        "--verify-envs",
        action="store_true",
        help="Verify phase environments are set up correctly",
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        help="Input directory for files (overrides config.input_dir)",
    )
    parser.add_argument(
        "--json_path",
        type=str,
        help="Path to pipeline.json (overrides config.pipeline_json)",
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        help="Max parallel workers (overrides config.max_workers)",
    )
    parser.add_argument(
        "--cpu_threshold",
        type=int,
        help="CPU throttle threshold % (overrides config.cpu_threshold)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Enable resume from JSON (overrides config.resume_enabled)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    # Override with CLI args
    if args.input_dir:
        config.input_dir = args.input_dir
    if args.json_path:
        config.pipeline_json = args.json_path
    if args.max_workers is not None:
        config.max_workers = args.max_workers
    if args.cpu_threshold is not None:
        config.cpu_threshold = args.cpu_threshold
    if args.resume:
        config.resume_enabled = True
    setup_logging(config)
    logger.info("Starting Phase 6 Batch Processing")
    logger.info(f"Configuration: {config.model_dump()}")

    if args.verify_envs:
        logger.info("Verifying phase environments...")
        env_status = verify_phase_environments(config.phases_to_run)
        print("\n" + "=" * 50)
        print("PHASE ENVIRONMENT VERIFICATION")
        print("=" * 50)
        for phase, status in env_status.items():
            status_str = "✓ OK" if status else "✗ FAILED"
            print(f"Phase {phase}: {status_str}")
        if not all(env_status.values()):
            print("\nTo fix failed environments:")
            for phase, status in env_status.items():
                if not status:
                    phase_dir_name = {
                        1: "phase1_validation",
                        2: "phase2_extraction",
                        3: "phase3_chunking",
                        4: "phase4_tts",
                        5: "phase5_enhancement",
                    }.get(phase, f"phase{phase}")
                    print(
                        f"  cd ../{phase_dir_name} && poetry env use <python_path> && poetry install"
                    )
        return 0 if all(env_status.values()) else 1

    if args.files:
        input_files = [Path(f) for f in args.files if Path(f).exists()]
        missing_files = [f for f in args.files if not Path(f).exists()]
        if missing_files:
            logger.warning(f"Missing files: {missing_files}")
    else:
        input_dir = Path(config.input_dir)
        if not input_dir.exists():
            logger.error(f"Input directory {input_dir} does not exist")
            return 1
        input_files = []
        for pattern in ["*.pdf", "*.txt", "*.doc", "*.docx"]:
            input_files.extend(input_dir.glob(pattern))

    if config.batch_size and len(input_files) > config.batch_size:
        logger.info(f"Limiting batch to {config.batch_size} files")
        input_files = input_files[: config.batch_size]

    if not input_files:
        logger.error("No input files found")
        return 1

    logger.info(f"Found {len(input_files)} files to process")

    if args.dry_run:
        print("DRY RUN - Files that would be processed:")
        for file_path in input_files:
            print(f"  - {file_path}")
        print(f"Phases to run: {config.phases_to_run}")
        return 0

    overall_start = time.perf_counter()
    cpu_readings = []
    processed_metadata = []
    stop_event = threading.Event()
    monitor_thread = threading.Thread(
        target=monitor_cpu, args=(config, stop_event)
    )
    monitor_thread.start()

    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        worker_args = [
            (str(file_path), config.phases_to_run, config)
            for file_path in input_files
        ]
        future_to_file = {
            executor.submit(process_file_worker, args): args[0]
            for args in worker_args
        }
        with tqdm(total=len(input_files), desc="Processing files") as pbar:
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    metadata = future.result()
                    processed_metadata.append(metadata)
                    pbar.set_postfix(
                        {
                            "file": Path(file_path).name[:20],
                            "status": metadata.status,
                        }
                    )
                except Exception as e:
                    logger.error(f"Worker failed for {file_path}: {e}")
                    failed_metadata = BatchMetadata(
                        file_id=Path(file_path).stem,
                        status="failed",
                        error_message=str(e),
                    )
                    processed_metadata.append(failed_metadata)
                cpu = psutil.cpu_percent(interval=0.1)
                cpu_readings.append(cpu)
                pbar.update(1)

    stop_event.set()
    monitor_thread.join()

    total_duration = time.perf_counter() - overall_start
    avg_cpu = sum(cpu_readings) / len(cpu_readings) if cpu_readings else None
    summary = BatchSummary.from_metadata_list(
        processed_metadata, total_duration, avg_cpu
    )
    summary.artifacts.append(config.log_file)
    update_pipeline_json(config, summary, processed_metadata)
    cleanup_old_artifacts(config.pipeline_json)

    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total Files: {summary.total_files}")
    print(f"Successful: {summary.successful_files}")
    print(f"Partial: {summary.partial_files}")
    print(f"Failed: {summary.failed_files}")
    print(f"Duration: {summary.total_duration:.2f}s")
    if summary.avg_cpu_usage:
        print(f"Avg CPU: {summary.avg_cpu_usage:.1f}%")
    print(f"Overall Status: {summary.status.upper()}")

    if summary.errors:
        print(f"\nErrors ({len(summary.errors)}):")
        for i, error in enumerate(summary.errors[:5]):
            print(f"  {i+1}. {error}")
        if len(summary.errors) > 5:
            print(f"  ... and {len(summary.errors) - 5} more")

    print("\nDetailed Results:")
    for metadata in processed_metadata:
        file_name = Path(metadata.file_id).name
        duration = f"{metadata.duration:.1f}s" if metadata.duration else "N/A"
        phases = ",".join(map(str, metadata.phases_completed)) or "none"
        print(
            f"  {file_name:<30} {metadata.status:<10} {duration:<8} phases: {phases}"
        )

    logger.info(f"Batch processing completed with status: {summary.status}")
    return (
        0
        if summary.status == "success"
        else 2 if summary.status == "partial" else 1
    )


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
