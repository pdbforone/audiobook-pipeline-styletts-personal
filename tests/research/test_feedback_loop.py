from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_feedback_loop_append_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.feedback_loop import update_research_feedback

    signals1 = {"analysis": {"engine_usage": {"frequency": {"xtts": 1}}}, "raw": {}}
    signals2 = {"analysis": {"engine_usage": {"frequency": {"kokoro": 2}}}, "raw": {}}

    agg1 = update_research_feedback({}, signals1)
    agg2 = update_research_feedback({}, signals2)

    history = Path(".pipeline/research/history.jsonl")
    assert history.exists()
    lines = history.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    aggregates = Path(".pipeline/research/aggregates.json")
    assert aggregates.exists()
    data = json.loads(aggregates.read_text(encoding="utf-8"))
    assert data["total_runs"] == 2
    assert "xtts" in data.get("engine_preference_signals", {})
