"""
Unit tests for Phase 5.5 subtitle generation.
"""

import pytest
from pathlib import Path
import json

from src.phase5_enhancement.subtitle_aligner import detect_drift, align_timestamps
from src.phase5_enhancement.subtitle_validator import calculate_wer, format_srt, format_vtt


@pytest.fixture
def sample_segments():
    """Sample subtitle segments for testing."""
    return [
        {'start': 0.0, 'end': 5.0, 'text': 'First segment of text.'},
        {'start': 5.5, 'end': 10.0, 'text': 'Second segment continues.'},
        {'start': 10.5, 'end': 15.0, 'text': 'Final segment here.'}
    ]


def test_detect_drift_no_drift(sample_segments):
    """Test drift detection with matching durations."""
    audio_duration = 15.0
    drift = detect_drift(sample_segments, audio_duration)
    assert drift == 0.0


def test_detect_drift_positive(sample_segments):
    """Test drift detection when audio is longer."""
    audio_duration = 20.0
    drift = detect_drift(sample_segments, audio_duration)
    assert drift == 5.0  # 20 - 15


def test_detect_drift_negative(sample_segments):
    """Test drift detection when audio is shorter."""
    audio_duration = 10.0
    drift = detect_drift(sample_segments, audio_duration)
    assert drift == -5.0  # 10 - 15


def test_align_timestamps(sample_segments):
    """Test timestamp alignment/scaling."""
    audio_duration = 30.0  # 2x longer
    aligned = align_timestamps(sample_segments, audio_duration)

    # All timestamps should be scaled by 2x
    assert aligned[0]['end'] == 10.0  # Was 5.0
    assert aligned[1]['end'] == 20.0  # Was 10.0
    assert aligned[2]['end'] == 30.0  # Was 15.0


def test_calculate_wer_perfect():
    """Test WER with identical text."""
    reference = "This is a test sentence"
    hypothesis = "This is a test sentence"
    wer_score = calculate_wer(reference, hypothesis)
    assert wer_score == 0.0


def test_calculate_wer_partial():
    """Test WER with some errors."""
    reference = "This is a test sentence"
    hypothesis = "This is test sentence"  # Missing 'a'
    wer_score = calculate_wer(reference, hypothesis)
    assert 0.0 < wer_score < 1.0  # Should have some error


def test_format_srt(sample_segments):
    """Test SRT formatting."""
    srt = format_srt(sample_segments)

    # Check structure
    assert "1\n" in srt  # First subtitle number
    assert "00:00:00,000 --> 00:00:05,000" in srt  # Timestamp
    assert "First segment of text." in srt
    assert "2\n" in srt  # Second subtitle number


def test_format_vtt(sample_segments):
    """Test VTT formatting."""
    vtt = format_vtt(sample_segments)

    # Check structure
    assert vtt.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:05.000" in vtt  # Timestamp (note: . not ,)
    assert "First segment of text." in vtt


def test_empty_segments():
    """Test handling of empty segments."""
    empty = []
    drift = detect_drift(empty, 10.0)
    assert drift == 0.0

    srt = format_srt(empty)
    assert srt == ""

    vtt = format_vtt(empty)
    assert vtt.startswith("WEBVTT")
