import os
from pathlib import Path


def test_capabilities_config_flags():
    text = Path("phase6_orchestrator/config.yaml").read_text(encoding="utf-8")
    assert "capabilities:" in text
    for flag in [
        "enable_safe_modes",
        "enable_phaseI",
        "enable_phaseJ",
        "enable_phaseK_safe",
        "enable_phaseP",
        "enable_phaseQ",
        "enable_phaseR",
        "enable_phaseS",
        "enable_phaseT",
        "enable_phaseU",
        "enable_phaseV",
        "enable_phaseW",
        "enable_phaseX",
        "enable_phaseY",
        "enable_phaseZ",
    ]:
        assert f"{flag}: true" in text.lower()


def test_no_engine_modifications():
    registry_path = Path("phase4_tts/engine_registry.yaml")
    if registry_path.exists():
        content = registry_path.read_text(encoding="utf-8").lower()
        assert "piper" not in content or "enabled: false" in content


def test_no_autonomy_overrides():
    base = Path(".pipeline")
    assert not (base / "overrides").exists()
    assert not (base / "autonomy_runtime").exists()
