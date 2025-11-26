"""Phase P: research state initializer (opt-in)."""

from __future__ import annotations

from pathlib import Path


def initialize_research_state(base_path: Path) -> None:
    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / "observations").mkdir(parents=True, exist_ok=True)
    (base_path / "evidence").mkdir(parents=True, exist_ok=True)
    (base_path / "patterns").mkdir(parents=True, exist_ok=True)
    (base_path / "runs").mkdir(parents=True, exist_ok=True)
    registry = base_path / "registry.json"
    if not registry.exists():
        registry.write_text('{"keys": {}}', encoding="utf-8")
    version_file = base_path / "research_version"
    if not version_file.exists():
        version_file.write_text("v1", encoding="utf-8")
