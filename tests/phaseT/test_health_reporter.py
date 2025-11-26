from pathlib import Path

from phaseT_consistency import health_reporter


def test_health_reporter_writes(tmp_path):
    path = health_reporter.write_consistency_report(
        run_id="test_run",
        consistency={},
        drift={},
        base_dir=tmp_path,
    )
    assert path.exists()
    assert path.parent == tmp_path
