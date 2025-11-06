"""Pytest suite for Phase 4 TTS main module covering config, retries, and CLI flow."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from phase4_tts.src import main as main_module
from phase4_tts.src.models import TTSConfig
from phase4_tts.src.validation import ValidationResult


def test_get_chunk_file_path_returns_all_chunks(phase4_assets: SimpleNamespace) -> None:
    """Verify chunk discovery returns the complete list when no chunk_id is provided."""
    chunks, error = main_module.get_chunk_file_path(
        str(phase4_assets.pipeline_path), phase4_assets.file_id
    )

    assert error == ""
    assert isinstance(chunks, list)
    assert chunks == [str(phase4_assets.chunk_file)]


def test_get_chunk_file_path_specific_index(phase4_assets: SimpleNamespace) -> None:
    """Ensure requesting a specific chunk index resolves to the correct path."""
    chunk_path, error = main_module.get_chunk_file_path(
        str(phase4_assets.pipeline_path), phase4_assets.file_id, "0"
    )

    assert error == ""
    assert chunk_path == str(phase4_assets.chunk_file)


def test_get_chunk_file_path_reports_invalid_index(phase4_assets: SimpleNamespace) -> None:
    """Confirm an out-of-range chunk index surfaces an informative error."""
    chunk_path, error = main_module.get_chunk_file_path(
        str(phase4_assets.pipeline_path), phase4_assets.file_id, "99"
    )

    assert chunk_path == []
    assert "out of range" in error


def test_load_config_reads_yaml(phase4_assets: SimpleNamespace) -> None:
    """Validate YAML config parsing produces a populated TTSConfig object."""
    config = main_module.load_config(str(phase4_assets.config_path))

    assert isinstance(config, TTSConfig)
    assert config.sample_rate == 22050
    assert config.ref_url == "https://example.com/reference.wav"
    assert Path(config.output_dir).resolve() == phase4_assets.output_dir.resolve()


def test_load_validation_config_parses_yaml(phase4_assets: SimpleNamespace) -> None:
    """Check validation config loader maps nested YAML settings to ValidationConfig."""
    validation_config = main_module.load_validation_config(
        str(phase4_assets.validation_path)
    )

    assert validation_config.enable_tier1 is True
    assert validation_config.duration_tolerance_sec == pytest.approx(4.0)
    assert validation_config.enable_tier2 is True
    assert validation_config.whisper_sample_rate == pytest.approx(0.5)
    assert "error phrase" in validation_config.error_phrases


def test_retry_chunk_synthesis_succeeds_after_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify retry logic retries once, sleeps with backoff, and returns success on second attempt."""
    attempt_outcomes = [False, True]
    sleep_calls: list[float] = []

    def fake_synthesize(*args, **kwargs):
        result = attempt_outcomes.pop(0)
        return result, {"attempt": len(attempt_outcomes)}

    monkeypatch.setattr(main_module, "synthesize_chunk", fake_synthesize)
    monkeypatch.setattr(main_module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    config = TTSConfig(ref_url="https://example.com/ref.wav")
    success, metadata = main_module.retry_chunk_synthesis(
        model=Mock(),
        text="Retry me",
        ref_path="ref.wav",
        output_path=tmp_path / "chunk.wav",
        config=config,
        chunk_id="chunk_001",
        max_attempts=3,
        delay_sec=2.0,
    )

    assert success is True
    assert metadata["attempt"] == 0
    assert sleep_calls == [2.0]


def test_retry_chunk_synthesis_fails_after_max_attempts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure retry logic exhausts attempts, performs exponential backoff, and reports failure."""
    monkeypatch.setattr(
        main_module,
        "synthesize_chunk",
        lambda *args, **kwargs: (False, {"failed": True}),
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(main_module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    config = TTSConfig(ref_url="https://example.com/ref.wav")
    success, metadata = main_module.retry_chunk_synthesis(
        model=Mock(),
        text="Always fail",
        ref_path="ref.wav",
        output_path=tmp_path / "chunk.wav",
        config=config,
        chunk_id="chunk_002",
        max_attempts=3,
        delay_sec=1.0,
    )

    assert success is False
    assert metadata == {}
    assert sleep_calls == [1.0, 2.0]


def test_main_succeeds_with_validation(monkeypatch: pytest.MonkeyPatch, phase4_assets: SimpleNamespace) -> None:
    """Run the CLI flow and assert successful synthesis, validation, and merge metadata."""
    mock_model = Mock()
    mock_tts = Mock()
    mock_tts.from_pretrained.return_value = mock_model
    monkeypatch.setattr(main_module, "ChatterboxTTS", mock_tts)

    monkeypatch.setattr(
        main_module,
        "prepare_voice_references",
        lambda *args, **kwargs: {
            "phase3_voice": str(phase4_assets.voice_ref),
            "override_voice": str(phase4_assets.voice_ref),
        },
    )
    monkeypatch.setattr(
        main_module,
        "get_selected_voice_from_phase3",
        lambda *_: "phase3_voice",
    )
    monkeypatch.setattr(
        main_module,
        "synthesize_chunk",
        lambda *args, **kwargs: (True, {"split_applied": False, "num_sub_chunks": 1}),
    )
    monkeypatch.setattr(main_module, "evaluate_mos_proxy", lambda *args, **kwargs: 4.2)

    tier1 = ValidationResult(True, 1, "ok", {"duration": 1.0}, 0.4)
    tier2 = ValidationResult(True, 2, "ok", {"wer": 0.03}, 0.9)
    validation_calls: list[tuple] = []

    def fake_validate(*args, **kwargs):
        validation_calls.append(args)
        return tier1, tier2

    monkeypatch.setattr(main_module, "validate_audio_chunk", fake_validate)
    monkeypatch.setattr(main_module.torch, "load", lambda *a, **k: Mock())
    monkeypatch.setattr(main_module.torch, "manual_seed", lambda *a, **k: None)
    monkeypatch.setattr(main_module.time, "sleep", lambda *a, **k: None)

    merge_calls = []

    def fake_merge(*args, **kwargs):
        merge_calls.append((args, kwargs))

    monkeypatch.setattr(main_module, "merge_to_pipeline_json", fake_merge)

    argv = [
        "phase4",
        "--file_id",
        phase4_assets.file_id,
        "--json_path",
        str(phase4_assets.pipeline_path),
        "--config",
        str(phase4_assets.config_path),
        "--validation_config",
        str(phase4_assets.validation_path),
    ]
    monkeypatch.setattr(main_module.sys, "argv", argv)

    exit_code = main_module.main()

    assert exit_code == 0
    mock_tts.from_pretrained.assert_called_once_with(device="cpu")
    assert len(validation_calls) == 1
    assert merge_calls, "merge_to_pipeline_json should be called once for the chunk"

    merge_args, merge_kwargs = merge_calls[0]
    metrics = merge_args[6]
    assert metrics["selected_voice"] == "phase3_voice"
    assert metrics["validation"]["validation_passed"] is True
    assert metrics["validation"]["tier2"]["details"]["wer"] == pytest.approx(0.03)
    assert merge_kwargs["split_metadata"]["num_sub_chunks"] == 1


def test_main_handles_validation_failure(monkeypatch: pytest.MonkeyPatch, phase4_assets: SimpleNamespace) -> None:
    """Confirm tier 1 validation failure marks the chunk as unsuccessful and surfaces errors."""
    mock_model = Mock()
    mock_tts = Mock()
    mock_tts.from_pretrained.return_value = mock_model
    monkeypatch.setattr(main_module, "ChatterboxTTS", mock_tts)

    monkeypatch.setattr(
        main_module,
        "prepare_voice_references",
        lambda *args, **kwargs: {"phase3_voice": str(phase4_assets.voice_ref)},
    )
    monkeypatch.setattr(
        main_module,
        "get_selected_voice_from_phase3",
        lambda *_: "phase3_voice",
    )
    monkeypatch.setattr(
        main_module,
        "synthesize_chunk",
        lambda *args, **kwargs: (True, {"split_applied": False}),
    )
    monkeypatch.setattr(main_module, "evaluate_mos_proxy", lambda *args, **kwargs: 3.5)

    tier1_fail = ValidationResult(False, 1, "duration_mismatch", {"delta": 10.0}, 0.5)
    monkeypatch.setattr(
        main_module,
        "validate_audio_chunk",
        lambda *args, **kwargs: (tier1_fail, None),
    )
    monkeypatch.setattr(main_module.torch, "load", lambda *a, **k: Mock())
    monkeypatch.setattr(main_module.torch, "manual_seed", lambda *a, **k: None)
    monkeypatch.setattr(main_module.time, "sleep", lambda *a, **k: None)

    merge_calls = []
    monkeypatch.setattr(
        main_module,
        "merge_to_pipeline_json",
        lambda *args, **kwargs: merge_calls.append((args, kwargs)),
    )

    argv = [
        "phase4",
        "--file_id",
        phase4_assets.file_id,
        "--json_path",
        str(phase4_assets.pipeline_path),
        "--config",
        str(phase4_assets.config_path),
        "--validation_config",
        str(phase4_assets.validation_path),
    ]
    monkeypatch.setattr(main_module.sys, "argv", argv)

    exit_code = main_module.main()

    assert exit_code == 1
    merge_args, _ = merge_calls[0]
    errors = merge_args[7]
    assert any("validation_tier1_duration_mismatch" in err for err in errors)


def test_main_returns_error_when_chunk_missing(
    monkeypatch: pytest.MonkeyPatch, phase4_assets: SimpleNamespace
) -> None:
    """Ensure missing chunk files do not trigger synthesis and yield a non-zero exit code."""
    missing_chunk = phase4_assets.chunk_file.parent / "chunk_9999.txt"
    pipeline_payload = {
        "phase3": {"files": {"test_file_001": {"chunk_paths": [str(missing_chunk)]}}}
    }
    phase4_assets.pipeline_path.write_text(
        json.dumps(pipeline_payload), encoding="utf-8"
    )

    mock_model = Mock()
    mock_tts = Mock()
    mock_tts.from_pretrained.return_value = mock_model
    monkeypatch.setattr(main_module, "ChatterboxTTS", mock_tts)

    monkeypatch.setattr(
        main_module,
        "prepare_voice_references",
        lambda *args, **kwargs: {"phase3_voice": str(phase4_assets.voice_ref)},
    )
    monkeypatch.setattr(
        main_module,
        "get_selected_voice_from_phase3",
        lambda *_: "phase3_voice",
    )

    def synthesize_guard(*args, **kwargs):
        raise AssertionError("synthesize_chunk should not run when chunk is missing")

    monkeypatch.setattr(main_module, "synthesize_chunk", synthesize_guard)

    def fail_validate(*args, **kwargs):
        raise AssertionError("validate_audio_chunk should not be called for missing files")

    monkeypatch.setattr(main_module, "validate_audio_chunk", fail_validate)
    monkeypatch.setattr(main_module.torch, "load", lambda *a, **k: Mock())
    monkeypatch.setattr(main_module.torch, "manual_seed", lambda *a, **k: None)
    monkeypatch.setattr(main_module.time, "sleep", lambda *a, **k: None)

    merge_calls = []
    monkeypatch.setattr(main_module, "merge_to_pipeline_json", lambda *a, **k: merge_calls.append((a, k)))

    argv = [
        "phase4",
        "--file_id",
        phase4_assets.file_id,
        "--json_path",
        str(phase4_assets.pipeline_path),
        "--config",
        str(phase4_assets.config_path),
        "--validation_config",
        str(phase4_assets.validation_path),
    ]
    monkeypatch.setattr(main_module.sys, "argv", argv)

    exit_code = main_module.main()

    assert exit_code == 1
    assert merge_calls == []
