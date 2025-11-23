"""Unit tests for helper functions inside main_multi_engine.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from phase4_tts.src import main_multi_engine as multi


def test_normalize_pipeline_path_handles_relative(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Relative paths should be resolved against PROJECT_ROOT."""
    repo_root = tmp_path / "repo"
    chunk_dir = repo_root / "phase3-chunking" / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_file = chunk_dir / "chunk_0001.txt"
    chunk_file.write_text("demo", encoding="utf-8")

    monkeypatch.setattr(multi, "PROJECT_ROOT", repo_root)

    resolved = multi.normalize_pipeline_path(
        "phase3-chunking/chunks/chunk_0001.txt"
    )
    assert resolved == chunk_file


def test_collect_chunks_sanitizes_and_derives_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """collect_chunks should sanitize text and derive consistent chunk IDs."""
    repo_root = tmp_path / "repo"
    chunk_dir = repo_root / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_file = chunk_dir / "MyBook_chunk_0005.txt"
    chunk_file.write_text("Hello “world” -- said he.", encoding="utf-8")

    pipeline_data = {
        "phase3": {
            "files": {
                "MyBook": {
                    "chunk_paths": [str(chunk_file)],
                }
            }
        }
    }

    monkeypatch.setattr(multi, "PROJECT_ROOT", repo_root)
    resolved_id, chunks = multi.collect_chunks(pipeline_data, "MyBook")

    assert resolved_id == "MyBook"
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "chunk_0005"
    assert '"' in chunks[0].text  # smart quotes normalized


def test_update_phase4_summary_records_results(tmp_path: Path) -> None:
    """update_phase4_summary should create the phase4 section with per-chunk data."""
    pipeline_path = tmp_path / "pipeline.json"
    pipeline_path.write_text(json.dumps({"phase3": {}}), encoding="utf-8")

    audio_path = tmp_path / "chunk_0000.wav"
    audio_path.write_text("fake", encoding="utf-8")

    results = [
        multi.ChunkResult("chunk_0000", True, audio_path, "xtts"),
        multi.ChunkResult("chunk_0001", False, None, None, "boom"),
    ]

    multi.update_phase4_summary(
        pipeline_path=pipeline_path,
        file_id="MyBook",
        voice_id="voice_a",
        requested_engine="f5",
        selected_engine="xtts",
        slow_rt_threshold=2.5,
        results=results,
        output_dir=tmp_path,
        duration_sec=12.5,
    )

    data = json.loads(pipeline_path.read_text(encoding="utf-8"))
    book_entry = data["phase4"]["files"]["MyBook"]

    metrics = book_entry["metrics"]
    assert metrics["chunks_failed"] == 1
    chunk_map = {chunk["chunk_id"]: chunk for chunk in book_entry["chunks"]}
    assert chunk_map["chunk_0001"]["status"] == "failed"
    assert chunk_map["chunk_0001"]["errors"] == ["boom"]
    assert data["phase4"]["status"] == "partial"
