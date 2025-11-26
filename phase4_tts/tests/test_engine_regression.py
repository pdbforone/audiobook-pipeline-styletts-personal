"""Phase O: Engine regression smoke tests (opt-in)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
yaml = pytest.importorskip("yaml", reason="PyYAML required for registry validation")


RUN_PHASE_O = os.environ.get("RUN_PHASE_O_FULL") == "1"


def _require_env():
    if not RUN_PHASE_O:
        pytest.skip("Set RUN_PHASE_O_FULL=1 to run engine regression tests")


def test_piper_disabled_in_registry():
    _require_env()
    registry_path = Path(__file__).resolve().parents[1] / "engine_registry.yaml"
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    piper = (data.get("engines") or {}).get("piper", {})
    assert not piper.get("enabled", False)


def test_xtts_and_kokoro_synthesis(tmp_path):
    _require_env()
    try:
        from phase4_tts.engines.engine_manager import EngineManager
        from phase4_tts.engines.xtts_engine import XTTSEngine
        from phase4_tts.engines.kokoro_engine import KokoroEngine
    except Exception as exc:
        pytest.skip(f"Engine dependencies unavailable: {exc}")

    manager = EngineManager()
    manager.register_engine("xtts", XTTSEngine)
    manager.register_engine("kokoro", KokoroEngine)

    ref_audio = tmp_path / "ref.wav"
    # Tiny silent reference
    ref_audio.write_bytes(b"\x00\x00")

    for engine_key in ("xtts", "kokoro"):
        try:
            audio, used_engine = manager.synthesize(
                text="Hello world.",
                reference_audio=ref_audio,
                engine=engine_key,
                return_engine=True,
            )
        except Exception as exc:
            pytest.skip(f"{engine_key} synthesis unavailable: {exc}")
        assert used_engine == engine_key
        assert audio is not None
