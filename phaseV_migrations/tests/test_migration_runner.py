from pathlib import Path

from phaseV_migrations import migration_runner


def test_plan_and_apply(tmp_path):
    cfg = {"targets": ["pipeline_state"], "lookback_runs": 5, "dry_run": True}
    plan = migration_runner.plan_migrations(cfg, base_dir=tmp_path)
    assert "plans" in plan
    result = migration_runner.apply_migrations(cfg, base_dir=tmp_path)
    assert "applied" in result
    # Ensure applied artifact is written
    assert Path(result["applied"][0]["output"]).exists()
