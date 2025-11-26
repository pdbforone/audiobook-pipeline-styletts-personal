from pathlib import Path

from tests.master_harness.harness_runner import run_master_harness


def test_master_harness_runs(tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text("dummy input", encoding="utf-8")
    report = run_master_harness(input_path)
    assert report["overall_status"] == "pass"
    assert report["comparison"]["schema_valid"] is True
