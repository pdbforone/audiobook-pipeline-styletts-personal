from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_collect_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.evidence_ingestion import collect_evidence

    state = {
        "phase1": {"status": "success", "errors": [], "files": {"f": {"chunk_paths": []}}},
        "phase4": {"status": "success", "errors": ["tts"], "files": {"f": {"chunk_paths": ["a"]}}},
    }
    ev = collect_evidence(state, [])
    assert ev["phases"]["phase1"]["status"] == "success"
    out_files = list((Path(".pipeline") / "research" / "evidence").glob("*.json"))
    assert out_files
    data = json.loads(out_files[0].read_text(encoding="utf-8"))
    assert "errors" in data
