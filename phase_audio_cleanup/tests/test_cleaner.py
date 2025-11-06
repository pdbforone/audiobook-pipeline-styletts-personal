"""
Unit tests for Audio Cleanup module.

Run with: poetry run pytest tests/
"""

import pytest
from pathlib import Path
from audio_cleanup.cleaner import AudiobookCleaner


def test_cleaner_initialization():
    """Test basic cleaner initialization."""
    cleaner = AudiobookCleaner(
        target_phrases=["test phrase"],
        model_size="tiny"  # Use tiny for fast testing
    )
    
    assert len(cleaner.target_phrases) == 1
    assert cleaner.target_phrases[0] == "test phrase"
    assert cleaner.model_size == "tiny"


def test_config_loading():
    """Test loading config from YAML."""
    config_path = Path(__file__).parent.parent / "config" / "phrases.yaml"
    
    if config_path.exists():
        cleaner = AudiobookCleaner.from_config(config_path)
        assert len(cleaner.target_phrases) > 0
        assert cleaner.model_size in ["tiny", "base", "small", "medium", "large"]


# TODO: Add more tests
# - Test transcription with sample audio
# - Test phrase detection in mock segments
# - Test audio segment removal
# - Test batch processing
