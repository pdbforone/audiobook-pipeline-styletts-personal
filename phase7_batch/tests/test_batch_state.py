from pathlib import Path


from pipeline_common import PipelineState
from phase7_batch.main import persist_batch_state
from phase7_batch.models import BatchMetadata, BatchSummary, Phase6Result


def _build_summary(
    *,
    status: str = "success",
    total: int = 1,
    successful: int = 1,
    failed: int = 0,
    skipped: int = 0,
    duration: float = 1.0,
    start: str = "2024-01-01T00:00:00+00:00",
    end: str = "2024-01-01T00:00:01+00:00",
    errors: list[str] | None = None,
    artifacts: list[str] | None = None,
) -> BatchSummary:
    return BatchSummary(
        status=status,
        total_files=total,
        successful_files=successful,
        failed_files=failed,
        skipped_files=skipped,
        duration_sec=duration,
        avg_cpu_usage=42.0,
        errors=errors or [],
        artifacts=artifacts or [],
        started_at=start,
        completed_at=end,
    )


def _build_metadata(
    file_id: str,
    *,
    status: str = "success",
    started: str = "2024-01-01T00:00:00+00:00",
    completed: str = "2024-01-01T00:00:05+00:00",
    duration: float = 5.0,
    error_message: str | None = None,
    errors: list[str] | None = None,
    cpu_avg: float | None = None,
    was_skipped: bool = False,
) -> BatchMetadata:
    return BatchMetadata(
        file_id=file_id,
        status=status,
        started_at=started,
        completed_at=completed,
        duration_sec=duration,
        was_skipped=was_skipped,
        error_message=error_message,
        errors=errors or [],
        source_path=f"/tmp/{file_id}.txt",
        phase6=Phase6Result(
            exit_code=0, metrics={}, stdout_tail=None, stderr_tail=None
        ),
        cpu_avg=cpu_avg,
    )


def _read_pipeline(path: Path) -> dict:
    state = PipelineState(path, validate_on_read=False)
    return state.read(validate=False)


def _assert_envelope(entry: dict) -> None:
    assert "status" in entry and isinstance(entry["status"], str)
    assert isinstance(entry.get("timestamps"), dict)
    assert isinstance(entry.get("artifacts"), dict)
    assert isinstance(entry.get("metrics"), dict)
    assert isinstance(entry.get("errors"), list)
    assert isinstance(entry.get("chunks"), list)


def test_persist_batch_success_path(tmp_path: Path) -> None:
    pipeline = tmp_path / "pipeline.json"
    summary = _build_summary(
        status="success", total=2, successful=2, failed=0, skipped=0
    )
    metadata = [
        _build_metadata("file_a", status="success", cpu_avg=12.5),
        _build_metadata("file_b", status="running", cpu_avg=10.0),
    ]

    persist_batch_state(pipeline, summary, metadata)

    data = _read_pipeline(pipeline)
    runs = data.get("batch_runs")
    assert isinstance(runs, list) and len(runs) == 1
    run = runs[0]
    assert run["status"] == "success"
    assert set(run["timestamps"]).issuperset({"start", "end", "duration"})
    assert isinstance(run["metrics"], dict)
    assert isinstance(run["errors"], list)

    for file_entry in run["files"].values():
        _assert_envelope(file_entry)


def test_failed_and_skipped_entries_record_errors(tmp_path: Path) -> None:
    pipeline = tmp_path / "pipeline.json"
    summary = _build_summary(
        status="partial", total=2, successful=0, failed=1, skipped=1
    )
    metadata = [
        _build_metadata(
            "failed_book",
            status="failed",
            error_message="boom",
            errors=["trace"],
        ),
        _build_metadata("skipped_book", status="skipped", was_skipped=True),
    ]

    persist_batch_state(pipeline, summary, metadata)

    run = _read_pipeline(pipeline)["batch_runs"][0]
    assert run["status"] == "partial"
    failed_entry = run["files"]["failed_book"]
    skipped_entry = run["files"]["skipped_book"]
    assert failed_entry["status"] == "failed"
    assert "boom" in failed_entry["errors"][0]
    assert skipped_entry["status"] == "skipped"
    assert skipped_entry["errors"] == []
    _assert_envelope(failed_entry)
    _assert_envelope(skipped_entry)


def test_partial_batch_metrics_present(tmp_path: Path) -> None:
    pipeline = tmp_path / "pipeline.json"
    summary = _build_summary(
        status="partial", total=3, successful=1, failed=1, skipped=1
    )
    metadata = [
        _build_metadata("ok", status="success"),
        _build_metadata("bad", status="failed", error_message="oops"),
        _build_metadata("later", status="skipped", was_skipped=True),
    ]

    persist_batch_state(pipeline, summary, metadata)

    run = _read_pipeline(pipeline)["batch_runs"][0]
    metrics = run["metrics"]
    assert metrics["total_files"] == 3
    assert metrics["successful_files"] == 1
    assert metrics["failed_files"] == 1
    assert metrics["skipped_files"] == 1
    for entry in run["files"].values():
        _assert_envelope(entry)


def test_multiple_runs_append_without_corruption(tmp_path: Path) -> None:
    pipeline = tmp_path / "pipeline.json"
    first_summary = _build_summary(
        status="success",
        total=1,
        successful=1,
        failed=0,
        skipped=0,
        start="2024-01-01T00:00:00+00:00",
        end="2024-01-01T00:05:00+00:00",
    )
    second_summary = _build_summary(
        status="success",
        total=1,
        successful=1,
        failed=0,
        skipped=0,
        start="2024-01-01T01:00:00+00:00",
        end="2024-01-01T01:05:00+00:00",
    )

    persist_batch_state(pipeline, first_summary, [_build_metadata("book1")])
    persist_batch_state(pipeline, second_summary, [_build_metadata("book2")])

    runs = _read_pipeline(pipeline)["batch_runs"]
    assert len(runs) == 2
    assert runs[0]["files"]["book1"]["status"] == "success"
    assert runs[1]["files"]["book2"]["status"] == "success"


def test_envelope_invariants_hold_for_all_files(tmp_path: Path) -> None:
    pipeline = tmp_path / "pipeline.json"
    summary = _build_summary(
        status="partial", total=2, successful=1, failed=1, skipped=0
    )
    metadata = [
        _build_metadata("good", status="success"),
        _build_metadata("bad", status="failed", error_message="bad things"),
    ]

    persist_batch_state(pipeline, summary, metadata)

    state = PipelineState(pipeline, validate_on_read=False).read(
        validate=False
    )
    files = state["batch_runs"][0]["files"]
    for entry in files.values():
        _assert_envelope(entry)
