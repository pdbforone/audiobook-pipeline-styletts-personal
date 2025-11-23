from __future__ import annotations

import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil
import trio
import yaml
from pipeline_common import PipelineState
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import BatchConfig, BatchMetadata, BatchSummary, Phase6Result

logger = logging.getLogger(__name__)
console = Console()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def posix(path: Path) -> str:
    return path.as_posix()


def setup_logging(config: BatchConfig) -> None:
    numeric_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.getLogger().handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    file_handler = logging.FileHandler(config.log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    logging.getLogger().setLevel(numeric_level)
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().addHandler(file_handler)


def load_config(config_path: str) -> BatchConfig:
    try:
        with open(config_path, "r") as fh:
            data = yaml.safe_load(fh) or {}
        config = BatchConfig(**data)
        if not config.phases:
            config.phases = [1, 2, 3, 4, 5]
        return config
    except FileNotFoundError:
        logger.warning("Config file %s not found, using defaults", config_path)
    except Exception as exc:
        logger.warning("Config load failed (%s); using defaults", exc)
    # Fall back to defaults if anything went wrong
    return BatchConfig(phases=[1, 2, 3, 4, 5])


def get_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for ancestor in [current] + list(current.parents):
        if (ancestor / "pipeline.json").exists():
            return ancestor
    # Fallback to the repository root by climbing four levels up
    return Path(__file__).resolve().parents[3]


def find_orchestrator() -> Optional[Path]:
    project_root = get_project_root()
    orchestrator = project_root / "phase6_orchestrator" / "orchestrator.py"
    if orchestrator.exists():
        return orchestrator
    logger.error("Phase 6 orchestrator not found at %s", orchestrator)
    return None


def discover_input_files(config: BatchConfig) -> List[Path]:
    input_dir = Path(config.input_dir)
    if not input_dir.exists():
        logger.error("Input directory not found: %s", input_dir)
        return []
    files = sorted(p for p in input_dir.iterdir() if p.is_file())
    if config.batch_size:
        files = files[: config.batch_size]
    return files


def load_pipeline_state(pipeline_path: Path) -> Dict[str, Any]:
    state = PipelineState(pipeline_path, validate_on_read=False)
    try:
        return state.read(validate=False)
    except FileNotFoundError:
        return {}


def latest_batch_records(pipeline: Dict[str, Any]) -> Dict[str, Any]:
    runs = pipeline.get("batch_runs") or []
    if not runs:
        return {}
    return runs[-1].get("files", {}) or {}


def metadata_from_existing(
    file_path: Path, record: Dict[str, Any]
) -> BatchMetadata:
    phase6_data = record.get("phase6") or {}
    timestamps = record.get("timestamps") or {}
    metrics = record.get("metrics") or {}
    artifacts = record.get("artifacts") or {}
    errors = record.get("errors", [])
    if record.get("error_message"):
        errors = [record["error_message"], *errors]
    metadata = BatchMetadata(
        file_id=file_path.stem,
        status=record.get("status", "skipped"),
        started_at=timestamps.get("start"),
        completed_at=timestamps.get("end"),
        duration_sec=timestamps.get("duration"),
        was_skipped=True,
        error_message=record.get("error_message"),
        errors=errors,
        source_path=artifacts.get("source_path") or posix(file_path),
        phase6=Phase6Result(**phase6_data),
        cpu_avg=metrics.get("cpu_avg"),
    )
    if metadata.started_at is None:
        metadata.started_at = utcnow().isoformat()
    if metadata.completed_at is None:
        metadata.completed_at = metadata.started_at
    return metadata


def _timestamp_payload(
    start: Optional[str], end: Optional[str], duration: Optional[float]
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if start is not None:
        payload["start"] = start
    if end is not None:
        payload["end"] = end
    if duration is not None:
        payload["duration"] = duration
    return payload


def _file_entry_from_metadata(meta: BatchMetadata) -> Dict[str, Any]:
    errors = [*(meta.errors or [])]
    if meta.error_message:
        errors.insert(0, meta.error_message)

    artifacts: Dict[str, Any] = {}
    if meta.source_path:
        artifacts["source_path"] = meta.source_path

    metrics: Dict[str, Any] = {}
    if meta.duration_sec is not None:
        metrics["duration_sec"] = meta.duration_sec
    if meta.cpu_avg is not None:
        metrics["cpu_avg"] = meta.cpu_avg

    entry: Dict[str, Any] = {
        "file_id": meta.file_id,
        "status": meta.status or "pending",
        "timestamps": _timestamp_payload(
            meta.started_at, meta.completed_at, meta.duration_sec
        ),
        "artifacts": artifacts,
        "metrics": metrics,
        "errors": errors,
        "chunks": [],
    }

    phase6_payload = meta.phase6.model_dump(exclude_none=True)
    if phase6_payload:
        entry["phase6"] = phase6_payload
    if meta.was_skipped:
        entry["was_skipped"] = True

    return entry


async def process_single_file(
    file_path: Path,
    config: BatchConfig,
    orchestrator: Path,
    semaphore: trio.Semaphore,
    existing_records: Dict[str, Any],
) -> BatchMetadata:
    file_id = file_path.stem
    if config.resume and file_id in existing_records:
        existing = existing_records[file_id]
        if existing.get("status") == "success":
            logger.info("[SKIP] %s already completed in previous run", file_id)
            return metadata_from_existing(file_path, existing)

    metadata = BatchMetadata(
        file_id=file_id,
        status="running",
        started_at=utcnow().isoformat(),
        source_path=posix(file_path),
    )

    cmd = [
        sys.executable,
        str(orchestrator),
        str(file_path),
        f"--pipeline-json={config.pipeline_json}",
    ]
    if config.phases:
        cmd.append("--phases")
        cmd.extend(config.phases_argument)
    if not config.resume:
        cmd.append("--no-resume")

    logger.info("[START] %s", file_id)

    start_perf = time.perf_counter()
    async with semaphore:
        try:
            result = await trio.run_process(
                cmd,
                capture_stdout=True,
                capture_stderr=True,
                check=False,
                stdin=subprocess.DEVNULL,
            )
            duration = time.perf_counter() - start_perf
            stdout_text = (result.stdout or b"").decode(
                "utf-8", errors="replace"
            )
            stderr_text = (result.stderr or b"").decode(
                "utf-8", errors="replace"
            )
            stdout_tail = "\n".join(stdout_text.splitlines()[-20:])
            stderr_tail = "\n".join(stderr_text.splitlines()[-20:])

            metadata.completed_at = utcnow().isoformat()
            metadata.duration_sec = duration
            metadata.phase6 = Phase6Result(
                exit_code=result.returncode,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                metrics={},
            )

            if result.returncode == 0:
                metadata.status = "success"
                logger.info("[SUCCESS] %s in %.2fs", file_id, duration)
            else:
                metadata.status = "failed"
                metadata.error_message = (
                    f"Phase 6 exited with code {result.returncode}"
                )
                if stderr_tail:
                    metadata.errors.append(stderr_tail)
                logger.error("[FAIL] %s: %s", file_id, metadata.error_message)
        except Exception as exc:  # pragma: no cover - safety net
            duration = time.perf_counter() - start_perf
            metadata.completed_at = utcnow().isoformat()
            metadata.duration_sec = duration
            metadata.status = "failed"
            metadata.error_message = f"Subprocess error: {exc}"
            metadata.errors.append(str(exc))
            metadata.phase6 = Phase6Result(exit_code=None, metrics={})
            logger.error("[ERROR] %s: %s", file_id, exc)

    return metadata


async def monitor_cpu_usage(
    config: BatchConfig, cpu_readings: List[float], stop_event: trio.Event
) -> None:
    throttling = False
    while not stop_event.is_set():
        await trio.sleep(1)
        cpu = psutil.cpu_percent(interval=0.1)
        cpu_readings.append(cpu)

        if cpu > config.cpu_threshold:
            if not throttling:
                logger.warning(
                    "[CPU] High load detected (%.1f%%). Throttling for %ss...",
                    cpu,
                    config.throttle_delay,
                )
                throttling = True
            await trio.sleep(config.throttle_delay)
        elif throttling:
            logger.info("[CPU] Load normalized. Resuming full concurrency.")
            throttling = False


def render_reports(
    summary: BatchSummary, metadata_list: List[BatchMetadata]
) -> None:
    status_colors = {
        "success": "green",
        "partial": "yellow",
        "failed": "red",
        "skipped": "yellow",
        "dry_run": "blue",
    }

    summary_table = Table(title="Batch Summary", show_header=True)
    summary_table.add_column("Metric", style="cyan", no_wrap=True)
    summary_table.add_column("Value", style="magenta")

    summary_table.add_row("Total Files", str(summary.total_files))
    summary_table.add_row(
        "Successful", f"[green]{summary.successful_files}[/green]"
    )
    summary_table.add_row("Failed", f"[red]{summary.failed_files}[/red]")
    summary_table.add_row(
        "Skipped", f"[yellow]{summary.skipped_files}[/yellow]"
    )
    summary_table.add_row("Duration (s)", f"{summary.duration_sec:.2f}")
    if summary.avg_cpu_usage is not None:
        summary_table.add_row("Avg CPU (%)", f"{summary.avg_cpu_usage:.1f}")
    color = status_colors.get(summary.status, "white")
    summary_table.add_row("Status", f"[{color}]{summary.status}[/{color}]")

    file_table = Table(title="Per-File Summary", show_header=True)
    file_table.add_column("File ID", style="cyan")
    file_table.add_column("Status", style="magenta")
    file_table.add_column("Duration (s)", justify="right")
    file_table.add_column("CPU Avg", justify="right")
    file_table.add_column("Errors", style="red")

    for meta in metadata_list:
        f_color = status_colors.get(meta.status, "white")
        status_display = f"[{f_color}]{meta.status}[/{f_color}]"
        duration_str = (
            f"{meta.duration_sec:.2f}"
            if meta.duration_sec is not None
            else "-"
        )
        cpu_str = f"{meta.cpu_avg:.1f}%" if meta.cpu_avg is not None else "-"
        error_excerpt = ""
        if meta.error_message:
            error_excerpt = (
                (meta.error_message[:80] + "...")
                if len(meta.error_message) > 80
                else meta.error_message
            )
        elif meta.errors:
            error_excerpt = (
                (meta.errors[0][:80] + "...")
                if len(meta.errors[0]) > 80
                else meta.errors[0]
            )
        file_table.add_row(
            meta.file_id, status_display, duration_str, cpu_str, error_excerpt
        )

    console.print("\n")
    console.print(summary_table)
    console.print("\n")
    console.print(file_table)


def persist_batch_state(
    pipeline_path: Path,
    summary: BatchSummary,
    metadata_list: List[BatchMetadata],
) -> None:
    state = PipelineState(pipeline_path, validate_on_read=False)
    files_payload: Dict[str, Any] = {
        meta.file_id: _file_entry_from_metadata(meta)
        for meta in sorted(metadata_list, key=lambda m: m.file_id)
    }

    run_id = f"batch_{summary.completed_at}"
    run_entry = {
        "run_id": run_id,
        "status": summary.status,
        "timestamps": _timestamp_payload(
            summary.started_at, summary.completed_at, summary.duration_sec
        ),
        "metrics": {
            "total_files": summary.total_files,
            "successful_files": summary.successful_files,
            "failed_files": summary.failed_files,
            "skipped_files": summary.skipped_files,
            "avg_cpu_usage": summary.avg_cpu_usage,
            "duration_sec": summary.duration_sec,
        },
        "errors": list(summary.errors),
        "artifacts": [str(artifact) for artifact in summary.artifacts],
        "files": files_payload,
    }
    with state.transaction(operation="batch_run") as txn:
        runs = txn.data.setdefault("batch_runs", [])
        existing_index = next(
            (
                idx
                for idx, run in enumerate(runs)
                if run.get("run_id") == run_id
            ),
            None,
        )
        if existing_index is not None:
            runs[existing_index] = run_entry
        else:
            runs.append(run_entry)
    logger.info(
        "Updated pipeline.json with batch results at %s", pipeline_path
    )


async def run_batch(
    config: BatchConfig,
) -> Tuple[BatchSummary, List[BatchMetadata]]:
    orchestrator = find_orchestrator()
    pipeline_path = Path(config.pipeline_json)
    pipeline = load_pipeline_state(pipeline_path)
    input_files = discover_input_files(config)

    if config.dry_run:
        if orchestrator is None:
            raise FileNotFoundError("Phase 6 orchestrator is missing.")
        now = utcnow()
        metadata_list = [
            BatchMetadata(
                file_id=path.stem,
                status="skipped",
                was_skipped=True,
                started_at=now.isoformat(),
                completed_at=now.isoformat(),
                duration_sec=0.0,
                source_path=posix(path),
            )
            for path in input_files
        ]
        summary = BatchSummary.from_metadata_list(
            metadata_list,
            started_at=now,
            completed_at=now,
            avg_cpu=None,
            status_override="dry_run",
        )
        summary.artifacts.append(Path(config.log_file).as_posix())

        dry_run_panel = Panel(
            "\n".join([f"- {p.as_posix()}" for p in input_files])
            or "No input files found.",
            title="Dry Run: Files that would be processed",
            style="blue",
        )
        console.print(dry_run_panel)

        persist_batch_state(pipeline_path, summary, metadata_list)
        render_reports(summary, metadata_list)
        return summary, metadata_list

    if orchestrator is None:
        raise FileNotFoundError("Phase 6 orchestrator is missing.")
    if not input_files:
        logger.error("No input files found in %s", config.input_dir)
        raise FileNotFoundError("No input files found to process.")

    existing_records = latest_batch_records(pipeline)
    cpu_readings: List[float] = []
    metadata_list: List[BatchMetadata] = []
    semaphore = trio.Semaphore(config.max_workers)
    stop_event = trio.Event()
    started_at = utcnow()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(monitor_cpu_usage, config, cpu_readings, stop_event)

        async def run_and_record(file_path: Path) -> None:
            m = await process_single_file(
                file_path, config, orchestrator, semaphore, existing_records
            )
            metadata_list.append(m)

        async with trio.open_nursery() as work_nursery:
            for file_path in input_files:
                work_nursery.start_soon(run_and_record, file_path)

        stop_event.set()

    completed_at = utcnow()
    avg_cpu = sum(cpu_readings) / len(cpu_readings) if cpu_readings else None
    summary = BatchSummary.from_metadata_list(
        metadata_list,
        started_at=started_at,
        completed_at=completed_at,
        avg_cpu=avg_cpu,
    )
    summary.artifacts.append(Path(config.log_file).as_posix())

    persist_batch_state(pipeline_path, summary, metadata_list)
    render_reports(summary, metadata_list)
    return summary, metadata_list


async def main_async(config: BatchConfig) -> int:
    try:
        summary, metadata_list = await run_batch(config)
    except Exception as exc:
        logger.error("Batch failed: %s", exc, exc_info=True)
        return 1

    status = summary.status
    if status in {"success", "dry_run", "skipped"}:
        return 0
    if status == "partial":
        return 2
    return 1


def main() -> int:
    config = load_config("config.yaml")
    setup_logging(config)
    return trio.run(main_async, config)


if __name__ == "__main__":
    sys.exit(main())
