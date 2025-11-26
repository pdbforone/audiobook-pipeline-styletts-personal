from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_research_runner_lifecycle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.research_runner import ResearchRunner

    cfg = {"enable": True}
    runner = ResearchRunner(cfg)
    run_dir = runner.begin_run()
    evidence = runner.ingest_evidence({}, [])
    patterns = runner.extract_patterns(evidence)
    report_path = runner.write_report({"patterns": patterns})

    assert run_dir.exists()
    assert (run_dir / "evidence.json").exists()
    assert (run_dir / "patterns.json").exists()
    rp = Path(report_path)
    assert rp.exists()
    data = json.loads(rp.read_text(encoding="utf-8"))
    assert "patterns" in data
