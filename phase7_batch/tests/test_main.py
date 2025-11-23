from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from phase7_batch.main import (
    discover_input_files,
    latest_batch_records,
    load_config,
    metadata_from_existing,
)
from phase7_batch.models import (
    BatchConfig,
    BatchMetadata,
    BatchSummary,
    Phase6Result,
)


class TestBatchConfig:
    def test_default_config_uses_cpu_minus_one(self, monkeypatch):
        monkeypatch.setattr("phase7_batch.models.os.cpu_count", lambda: 5)

        config = BatchConfig()

        assert config.max_workers == 4
        assert config.cpu_threshold == 85.0
        assert config.phases == []
        assert config.log_level == "INFO"
        assert config.resume is True

    def test_path_normalization_and_phase_parsing(self, tmp_path):
        config = BatchConfig(
            input_dir=tmp_path / "inputs",
            pipeline_json=tmp_path / "pipeline.json",
            log_file=tmp_path / "batch.log",
            log_level="debug",
            phases=["1", 3, "5"],
            batch_size=2,
        )

        assert config.input_dir.endswith("inputs")
        assert config.pipeline_json.endswith("pipeline.json")
        assert config.log_file.endswith("batch.log")
        assert config.log_level == "DEBUG"
        assert config.phases == [1, 3, 5]
        assert config.batch_size == 2


class TestBatchMetadata:
    def test_defaults_and_phase6_container(self):
        metadata = BatchMetadata(file_id="chapter1")

        assert metadata.status == "pending"
        assert metadata.phase6 == Phase6Result()
        assert metadata.was_skipped is False
        assert metadata.to_pipeline_dict()["status"] == "pending"

    def test_to_pipeline_dict_excludes_file_id(self):
        metadata = BatchMetadata(
            file_id="chapter2",
            status="failed",
            duration_sec=12.5,
            error_message="boom",
            errors=["trace"],
            cpu_avg=50.0,
        )

        payload = metadata.to_pipeline_dict()
        assert "file_id" not in payload
        assert payload["status"] == "failed"
        assert payload["duration_sec"] == 12.5
        assert payload["errors"][0] == "trace"


class TestBatchSummary:
    def test_summary_status_and_duration(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(seconds=90)
        metadata_list = [
            BatchMetadata(file_id="good", status="success"),
            BatchMetadata(
                file_id="bad", status="failed", error_message="boom"
            ),
            BatchMetadata(file_id="skip", status="skipped"),
        ]

        summary = BatchSummary.from_metadata_list(
            metadata_list, start, end, avg_cpu=70.0
        )

        assert summary.total_files == 3
        assert summary.status == "partial"
        assert summary.duration_sec == pytest.approx(90.0)
        assert "boom" in summary.errors
        assert summary.avg_cpu_usage == 70.0

    def test_summary_with_status_override(self):
        start = datetime.now(timezone.utc)
        end = start + timedelta(seconds=5)
        metadata_list = [BatchMetadata(file_id="only", status="skipped")]

        summary = BatchSummary.from_metadata_list(
            metadata_list, start, end, status_override="dry_run"
        )

        assert summary.status == "dry_run"
        assert summary.failed_files == 0
        assert summary.skipped_files == 1


class TestConfigLoading:
    def test_load_valid_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "\n".join(
                [
                    "log_level: warning",
                    "max_workers: 3",
                    "phases: [1, 4]",
                    "batch_size: 1",
                ]
            )
        )

        config = load_config(str(config_file))

        assert config.log_level == "WARNING"
        assert config.max_workers == 3
        assert config.phases == [1, 4]
        assert config.batch_size == 1

    def test_load_missing_config_returns_defaults(self):
        config = load_config("does-not-exist.yaml")

        assert isinstance(config, BatchConfig)
        assert config.phases == [1, 2, 3, 4, 5]
        assert config.log_level == "INFO"

    def test_load_invalid_yaml_falls_back(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("log_level: [not: valid")

        config = load_config(str(config_file))

        assert isinstance(config, BatchConfig)
        assert config.phases == [1, 2, 3, 4, 5]


class TestFilesystemHelpers:
    def test_discover_input_files_sorted_and_limited(self, tmp_path):
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        files = []
        for name in ["b.txt", "a.txt", "c.txt"]:
            path = input_dir / name
            path.write_text("data")
            files.append(path)

        config = BatchConfig(
            input_dir=str(input_dir),
            pipeline_json=str(tmp_path / "pipeline.json"),
            batch_size=2,
        )

        discovered = discover_input_files(config)

        assert [p.name for p in discovered] == ["a.txt", "b.txt"]

    def test_discover_input_files_missing_directory(self, tmp_path, caplog):
        caplog.set_level("ERROR")
        config = BatchConfig(
            input_dir=str(tmp_path / "missing"),
            pipeline_json=str(tmp_path / "pipeline.json"),
        )

        files = discover_input_files(config)

        assert files == []
        assert "Input directory not found" in caplog.text


class TestPipelineHelpers:
    def test_metadata_from_existing_merges_fields(self):
        file_path = Path("/tmp/book.pdf")
        record = {
            "status": "success",
            "timestamps": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-01T00:01:00Z",
            },
            "metrics": {"duration": 60.0, "cpu_avg": 40.0},
            "artifacts": {"source_path": "/tmp/book.pdf"},
            "errors": ["minor"],
            "phase6": {"exit_code": 0},
        }

        metadata = metadata_from_existing(file_path, record)

        assert metadata.file_id == "book"
        assert metadata.was_skipped is True
        assert metadata.phase6.exit_code == 0
        assert metadata.cpu_avg == 40.0
        assert metadata.errors[0] == "minor"

    def test_latest_batch_records_returns_latest(self):
        pipeline = {
            "batch_runs": [
                {"files": {"a": {"status": "success"}}},
                {"files": {"b": {"status": "failed"}}},
            ]
        }

        latest = latest_batch_records(pipeline)

        assert "b" in latest
        assert latest["b"]["status"] == "failed"

    def test_latest_batch_records_handles_missing(self):
        assert latest_batch_records({}) == {}
        assert latest_batch_records({"batch_runs": []}) == {}


class TestRealWorldSummaries:
    def test_large_batch_summary_counts(self):
        now = datetime.now(timezone.utc)
        metadata_list = []
        for i in range(10):
            status = "success" if i < 6 else "failed" if i < 8 else "skipped"
            metadata_list.append(
                BatchMetadata(file_id=f"doc{i}", status=status)
            )

        summary = BatchSummary.from_metadata_list(
            metadata_list, now, now + timedelta(seconds=10)
        )

        assert summary.successful_files == 6
        assert summary.failed_files == 2
        assert summary.skipped_files == 2
        assert summary.status == "partial"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
