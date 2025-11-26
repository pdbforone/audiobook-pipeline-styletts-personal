from __future__ import annotations

from pathlib import Path

import pytest


def test_initialize_research_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.init import initialize_research_state

    base = Path(".pipeline") / "research"
    initialize_research_state(base)
    assert base.exists()
    assert (base / "observations").exists()
    assert (base / "evidence").exists()
    assert (base / "patterns").exists()
    assert (base / "runs").exists()
    assert (base / "registry.json").exists()
    assert (base / "research_version").exists()
