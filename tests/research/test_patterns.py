from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_extract_patterns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.patterns import extract_patterns

    evidence = {
        "phases": {"phase1": {"status": "success"}},
        "errors": ["e1", "e1", "e2"],
        "chunks": ["c1", "c2"],
    }
    patterns = extract_patterns(evidence)
    assert "patterns" in patterns
    out_files = list((Path(".pipeline") / "research" / "patterns").glob("*.json"))
    assert out_files
    data = json.loads(out_files[0].read_text(encoding="utf-8"))
    assert "errors" in data["patterns"]
