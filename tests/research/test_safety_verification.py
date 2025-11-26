from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_safety_verification_flags_disallowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.safety_verification import verify_research_outputs

    signals = {
        "raw": {},
        "analysis": {},
        "engine_suggestion": {"preferred": "piper"},
    }
    result = verify_research_outputs(signals)
    assert result["valid"] is False
    assert result["issues"]
    log_files = list((Path(".pipeline") / "research").glob("safety_log_*.json"))
    assert log_files, "Safety log should be written"
    data = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert "blocked_actions" in data
