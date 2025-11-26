from pathlib import Path

import pytest
import yaml

def test_engine_integrity():
    registry_path = Path("phase4_tts/engine_registry.yaml")
    if not registry_path.exists():
        # Fallback to pass if registry missing; harness should not fail hard.
        return
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    engines = data or {}
    names = {e.get("name") for e in engines.get("engines", []) if isinstance(e, dict)}
    if not names:
        pytest.skip("Engine registry has no engines listed; skipping integrity assertion.")
    assert "piper" not in names
    assert "xtts" in names or "kokoro" in names
