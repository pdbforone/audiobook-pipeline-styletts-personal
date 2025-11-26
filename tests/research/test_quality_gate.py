from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_quality_gate_returns_expected_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.quality_gate import evaluate_quality_gate, write_quality_gate

    research_signals = {
        "analysis": {
            "phase_summary": {"phase1": {"status": "success"}},
            "failure_patterns": {"counts": {"tts_failure": 2}},
            "engine_usage": {"frequency": {"xtts": 3}},
            "chunk_distribution": {"min": 1, "max": 10},
            "memory_notes": {},
            "policy_notes": {},
        },
        "raw": {},
    }
    run_summary = {"status": "success"}

    result = evaluate_quality_gate(research_signals, run_summary)
    assert set(result.keys()) >= {"passed", "signals_considered", "issues", "notes", "summary_status"}
    path = write_quality_gate(result)
    path_obj = Path(path)
    assert path_obj.exists()
    data = json.loads(path_obj.read_text(encoding="utf-8"))
    assert data["passed"] in (True, False)
