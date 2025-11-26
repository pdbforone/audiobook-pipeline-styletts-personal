from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_record_phase_observation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.observation_hooks import record_phase_observation
    from phaseP_research.research_config import ResearchConfig

    cfg = ResearchConfig(enable_research=True)
    path = record_phase_observation(
        "phase1",
        {"input_size": 1, "output_size": 1, "metadata": {"status": "success"}},
        cfg,
    )
    assert path is not None
    p = Path(path)
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["phase"] == "phase1"
