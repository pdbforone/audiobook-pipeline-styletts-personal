import pytest
from unittest.mock import patch
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent / "src" / "phase5_enhancement")
)

from main import reduce_noise, normalize_volume
import numpy as np


@pytest.fixture
def mock_audio():
    """Create 1 second of random audio at 22050 Hz"""
    return (
        np.random.rand(22050).astype(np.float32) * 2 - 1,
        22050,
    )  # Range [-1, 1]


def test_normalize_volume_basic(mock_audio):
    """Test basic volume normalization functionality"""
    audio, sr = mock_audio

    # Normalize volume
    normalized, pre_rms, post_rms = normalize_volume(audio, sr, headroom=0.1)

    # Check that function returns valid values
    assert isinstance(normalized, np.ndarray)
    assert len(normalized) == len(audio)
    assert isinstance(pre_rms, float)
    assert isinstance(post_rms, float)
    assert pre_rms > 0
    assert post_rms > 0

    # Check that normalization had some effect (post RMS should be different)
    # For random audio in [-1, 1], normalization should typically increase RMS
    assert post_rms != pre_rms


def test_normalize_volume_silent_audio():
    """Test volume normalization on silent audio"""
    silent_audio = np.zeros(22050, dtype=np.float32)
    sr = 22050

    normalized, pre_rms, post_rms = normalize_volume(silent_audio, sr)

    # Silent audio should remain silent
    assert np.allclose(pre_rms, 0.0, atol=1e-6)
    assert np.allclose(post_rms, 0.0, atol=1e-6)
    assert len(normalized) == len(silent_audio)


def test_normalize_volume_low_level_audio():
    """Test volume normalization on low-level audio"""
    # Create very quiet audio (RMS around 0.01)
    low_audio = (np.random.rand(22050).astype(np.float32) - 0.5) * 0.02
    sr = 22050

    normalized, pre_rms, post_rms = normalize_volume(low_audio, sr)

    # Post-RMS should be significantly higher than pre-RMS
    assert post_rms > pre_rms
    # Normalized audio should have higher RMS (volume increased)
    assert post_rms > 0.1  # Should be noticeably louder


def test_normalize_volume_with_different_headroom():
    """Test volume normalization with different headroom values"""
    audio = (np.random.rand(22050).astype(np.float32) - 0.5) * 0.5
    sr = 22050

    # Test with minimal headroom
    norm1, _, post_rms1 = normalize_volume(audio, sr, headroom=0.0)

    # Test with significant headroom
    norm2, _, post_rms2 = normalize_volume(audio, sr, headroom=0.5)

    # With more headroom, the output should be slightly quieter
    # (though both should normalize the audio)
    assert post_rms1 > 0
    assert post_rms2 > 0


def test_normalize_volume_no_clipping():
    """Test that volume normalization doesn't cause clipping"""
    audio = (np.random.rand(22050).astype(np.float32) - 0.5) * 0.3
    sr = 22050

    normalized, _, _ = normalize_volume(audio, sr, headroom=0.1)

    # Check that normalized audio doesn't exceed [-1, 1] range
    assert np.max(np.abs(normalized)) <= 1.0
    # Check that it's using the available headroom (shouldn't be at max)
    assert np.max(np.abs(normalized)) <= 0.95  # With 0.1 headroom


def test_reduce_noise(mock_audio):
    audio, sr = mock_audio
    with patch("noisereduce.reduce_noise") as mock_nr:
        mock_nr.return_value = audio
        result = reduce_noise(audio, sr)
        assert np.array_equal(result, audio)


# Additional tests for other functions can be added here as needed
