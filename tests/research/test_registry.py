from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_research_registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from phaseP_research.research_registry import ResearchRegistry

    registry_path = Path(".pipeline/research/registry.json")
    registry = ResearchRegistry(registry_path)

    registry.add_entry("research_topics", {"topic": "voice"})
    entry = registry.resolve("research_topics")
    assert entry is not None
    assert entry["payload"]["topic"] == "voice"

    registry.update_entry("research_topics", {"topic": "audio"})
    entry2 = registry.resolve("research_topics")
    assert entry2["payload"]["topic"] == "audio"

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "keys" in data
