from pathlib import Path

from phaseU_integrity import integrity_reporter


def test_integrity_reporter_writes(tmp_path):
    report = {
        "id": "test_integrity",
        "run_id": "r1",
        "summary": {},
        "signals": {},
        "integrity": {},
        "created_at": "now",
    }
    path = integrity_reporter.write_integrity_report(report, base_dir=tmp_path)
    assert path.exists()
    assert path.parent == tmp_path
