from pathlib import Path

from tests.master_harness import orchestration_runner


def test_phase_sequence():
    tmp_dir = Path(".pipeline_harness_tmp_seq")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    res = orchestration_runner.run_full_pipeline(Path("input.txt"), tmp_dir)
    phases = [p.get("phase") for p in res["output_json"].get("phases", [])]
    assert phases == [1, 2, 3, 4, 5, 6]
