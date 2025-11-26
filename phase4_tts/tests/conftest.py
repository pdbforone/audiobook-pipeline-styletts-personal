"""Shared pytest fixtures for Phase 4 test suite."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

TESTS_DIR = Path(__file__).resolve().parent
PHASE_ROOT = TESTS_DIR.parent
SRC_DIR = PHASE_ROOT / "src"
REPO_ROOT = PHASE_ROOT.parent
for candidate in (REPO_ROOT, PHASE_ROOT, SRC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


@pytest.fixture
def phase4_assets(tmp_path: Path) -> SimpleNamespace:
    """Create temporary config, validation, pipeline, and chunk assets for Phase 4 tests."""
    if yaml is None:
        pytest.skip("PyYAML is required for Phase 4 test fixtures", allow_module_level=True)
    output_dir = tmp_path / "artifacts" / "audio"
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    config_data = {
        "sample_rate": 22050,
        "language": "en",
        "ref_url": "https://example.com/reference.wav",
        "exaggeration": 0.3,
        "cfg_weight": 1.5,
        "temperature": 0.65,
        "sub_chunk_retries": 2,
        "silence_duration": 0.4,
        "enable_splitting": True,
        "output_dir": str(output_dir),
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    validation_data = {
        "validation": {
            "tier1": {
                "enabled": True,
                "duration_tolerance_sec": 4.0,
                "silence_threshold_sec": 1.5,
                "min_amplitude_db": -35.0,
            },
            "tier2": {
                "enabled": True,
                "whisper_model": "base",
                "whisper_sample_rate": 0.5,
                "whisper_first_n": 1,
                "whisper_last_n": 1,
                "max_wer": 0.15,
            },
            "error_phrases": ["error phrase"],
        }
    }
    validation_path = tmp_path / "validation_config.yaml"
    validation_path.write_text(
        yaml.safe_dump(validation_data), encoding="utf-8"
    )

    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_file = chunk_dir / "chunk_0001.txt"
    chunk_file.write_text(
        "This is a synthetic chunk for testing.", encoding="utf-8"
    )

    pipeline_data = {
        "phase3": {
            "files": {
                "test_file_001": {
                    "chunk_paths": [str(chunk_file)],
                    "suggested_voice": "phase3_voice",
                }
            }
        }
    }
    pipeline_path = tmp_path / "pipeline.json"
    pipeline_path.write_text(json.dumps(pipeline_data), encoding="utf-8")

    voice_ref = tmp_path / "voice.wav"
    voice_ref.write_bytes(b"fake-audio")

    return SimpleNamespace(
        config_path=config_path,
        validation_path=validation_path,
        pipeline_path=pipeline_path,
        chunk_file=chunk_file,
        output_dir=output_dir,
        voice_ref=voice_ref,
        file_id="test_file_001",
    )
