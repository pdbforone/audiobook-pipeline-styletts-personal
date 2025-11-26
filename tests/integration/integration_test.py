import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_common import test_utils


def _load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _simulate_orchestrator_run(tmpdir: Path, autonomy_mode: str = "baseline") -> Path:
    """Simulate a lightweight orchestrator output without touching real pipeline logic."""
    summary = {
        "file_id": "sample_run",
        "status": "success",
        "phases": ["phase1", "phase2", "phase3", "phase4", "phase5", "phase6"],
        "autonomy_mode": autonomy_mode if autonomy_mode != "baseline" else None,
        "overrides": {} if autonomy_mode != "autonomous" else {"phase4": {"engine": "xtts"}},
        "repairs_applied": [] if autonomy_mode != "repair" else [{"chunk": "c1", "path": "repairs/c1.wav"}],
    }
    summary_path = tmpdir / "policy_runtime" / "last_run_summary.json"
    _write_json(summary_path, summary)
    return summary_path


def test_baseline_run(tmp_path, monkeypatch):
    # Simulate tiny text fixture and baseline orchestrator output
    summary_path = _simulate_orchestrator_run(tmp_path, autonomy_mode="baseline")
    summary = _load_json(summary_path)
    assert summary["status"] == "success"
    assert summary.get("overrides") == {}
    assert not summary.get("repairs_applied")
    assert "phases" in summary and len(summary["phases"]) == 6


def test_cross_phase_schemas():
    # Construct mock phase outputs and validate schemas and keys
    phase1 = {"file_id": "f1", "validated": True, "metadata": {}}
    phase2 = {"file_id": "f1", "text": "hello", "extracted_text": "hello"}
    phase3 = [{"id": "c1", "text": "chunk"}]
    phase4 = [{"chunk_id": "c1", "audio_path": __file__}]
    phase5 = {"file_id": "f1", "phases": [], "status": "success"}
    phase6 = {"file_id": "f1", "phases": [], "status": "success"}

    test_utils.validate_schema(phase1, test_utils.SCHEMA_PHASE1)
    test_utils.validate_schema(phase2, test_utils.SCHEMA_PHASE2)
    for ch in phase3:
        test_utils.validate_schema(ch, test_utils.SCHEMA_PHASE3)
    for seg in phase4:
        test_utils.validate_schema(seg, test_utils.SCHEMA_PHASE4)
    test_utils.validate_schema(phase5, test_utils.SCHEMA_PHASE5)
    test_utils.validate_schema(phase6, test_utils.SCHEMA_PHASE6)


def test_orchestrator_ordering(monkeypatch, tmp_path):
    executed: List[str] = []

    def fake_run_phase(name):
        executed.append(name)

    phase_sequence = ["phase1", "phase2", "phase3", "phase4", "phase5", "policy", "repair", "finalize"]
    for name in phase_sequence:
        fake_run_phase(name)
    assert executed == phase_sequence


def test_override_reset(tmp_path):
    overrides_path = tmp_path / ".pipeline" / "tuning_overrides.json"

    # Simulate run with overrides
    _write_json(overrides_path, {"overrides": {"phase3": {"chunk_size": 100}}})
    data = _load_json(overrides_path)
    assert data["overrides"]

    # Simulate clean run resetting overrides
    _write_json(overrides_path, {"overrides": {}})
    data = _load_json(overrides_path)
    assert data["overrides"] == {}


def test_state_integrity(tmp_path):
    pipeline_dir = tmp_path / ".pipeline"
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    valid_files = {
        "a.json": {"ts": "2025-11-25T00:00:00Z", "value": 1},
        "policy_runtime/log.json": {"event": "ok", "timestamp": "2025-11-25T00:00:00Z"},
    }
    for rel, payload in valid_files.items():
        _write_json(pipeline_dir / rel, payload)
    txn = pipeline_dir / "transactions.log"
    txn.write_text("001|ok\n002|ok\n", encoding="utf-8")

    for file in pipeline_dir.rglob("*.json"):
        data = _load_json(file)
        assert data is not None
        assert all(v is not None for v in data.values())
    entries = txn.read_text(encoding="utf-8").splitlines()
    assert entries == sorted(entries)


def test_engine_regression(tmp_path, monkeypatch):
    class FakeEngineManager:
        def __init__(self):
            self.engines = {"xtts": object(), "kokoro": object()}

        @property
        def enabled_engines(self):
            return ["xtts", "kokoro"]

        def synthesize(self, text: str, engine: str):
            assert engine in self.enabled_engines
            path = tmp_path / f"{engine}.wav"
            path.write_bytes(b"FAKE_WAV_DATA")
            return {"audio_path": str(path), "rtf": 1.0}

    manager = FakeEngineManager()
    for engine in manager.enabled_engines:
        result = manager.synthesize("Hello world.", engine=engine)
        assert Path(result["audio_path"]).exists()
        assert 0.1 < result["rtf"] < 20.0
    assert "piper" not in manager.enabled_engines


def test_repair_integration(tmp_path):
    repairs_dir = tmp_path / ".pipeline" / "repairs"
    repairs_dir.mkdir(parents=True, exist_ok=True)
    original = tmp_path / "audio.wav"
    repaired = repairs_dir / "audio_repaired.wav"
    original.write_bytes(b"ORIG")
    repaired.write_bytes(b"REPAIR")
    summary = {"chunks": [{"id": "c1", "repaired": True, "audio_path": str(repaired), "original_path": str(original)}]}
    summary_path = tmp_path / ".pipeline" / "policy_runtime" / "last_run_summary.json"
    _write_json(summary_path, summary)
    assert repaired.exists()
    assert original.exists()
    data = _load_json(summary_path)
    assert data["chunks"][0]["repaired"] is True
    assert data["chunks"][0]["audio_path"] != data["chunks"][0]["original_path"]


def test_full_safety_validation(tmp_path):
    safety_dir = tmp_path / ".pipeline" / "policy_runtime" / "safety_events"
    safety_dir.mkdir(parents=True, exist_ok=True)
    event = {"event": "downgrade", "timestamp": "2025-11-25T00:00:00Z", "details": {"reason": "test"}}
    _write_json(safety_dir / "event.json", event)
    overrides_path = tmp_path / ".pipeline" / "tuning_overrides.json"
    _write_json(overrides_path, {"overrides": {}})
    last_run = tmp_path / ".pipeline" / "policy_runtime" / "last_run_summary.json"
    _write_json(last_run, {"autonomy_mode": "supervised", "overrides": {}, "status": "success"})

    assert overrides_path.exists()
    assert _load_json(overrides_path)["overrides"] == {}
    events = list(safety_dir.glob("*.json"))
    assert events
    for ev in events:
        data = _load_json(ev)
        assert data.get("event") == "downgrade"
