"""Phase O: Self-repair integration smoke test (opt-in)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from self_repair.repair_loop import DeadChunkRepair, ErrorRegistry, RepairAttempt


RUN_PHASE_O = os.environ.get("RUN_PHASE_O_FULL") == "1"


def _require_env():
    if not RUN_PHASE_O:
        pytest.skip("Set RUN_PHASE_O_FULL=1 to run repair flow tests")


def test_repair_registry_updates(tmp_path):
    _require_env()
    pipeline_dir = tmp_path / ".pipeline"
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    registry_path = pipeline_dir / "error_registry.json"
    repairs_dir = pipeline_dir / "repairs"
    repairs_dir.mkdir(parents=True, exist_ok=True)
    registry = ErrorRegistry(path=registry_path)

    chunk_id = "chunk_test"
    file_id = "baseline_snippet"
    registry.add_failure(
        chunk_id=chunk_id,
        file_id=file_id,
        category="tts_failure",
        message="synthetic failure",
    )
    attempt = RepairAttempt(strategy="simplify_text", success=False, chunk_id=chunk_id)
    registry.add_attempt(chunk_id, attempt)

    data = registry_path.read_text(encoding="utf-8")
    assert '"chunk_id": "chunk_test"' in data

    chunk_path = tmp_path / "chunk_0001.txt"
    chunk_path.write_text("bad chunk", encoding="utf-8")
    original_size = chunk_path.stat().st_size

    repair = DeadChunkRepair(error_registry=registry)
    # Avoid real strategies; patch to no-op to ensure registry write only
    repair._try_smaller_splits = lambda **_: None
    repair._try_different_engine = lambda **_: None
    repair._try_text_rewrite = lambda **_: None
    repair._try_simplify_text = lambda **_: None

    repair.repair(
        chunk_id=chunk_id,
        file_id=file_id,
        text="bad chunk",
        original_engine="xtts",
        reference_audio=None,
        max_attempts=1,
        auto_repair=False,
    )

    assert registry_path.exists()
    content = registry_path.read_text(encoding="utf-8")
    assert '"chunk_id": "chunk_test"' in content
    assert chunk_path.stat().st_size == original_size
