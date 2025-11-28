"""
Audio Feedback System for UI

Generates R2D2-style beeps and boops for pipeline events.
"""

from __future__ import annotations

import base64
import io
import logging
import threading
from typing import Literal, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Try to import audio libraries
try:
    from scipy.io import wavfile
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available - audio feedback will be disabled")


SoundType = Literal[
    "chunk_complete",
    "chunk_failed",
    "chunk_retry",
    "phase_complete",
    "phase_failed",
    "pipeline_complete",
    "pipeline_failed",
    "warning",
    "info",
]


class AudioFeedback:
    """Generate R2D2-style audio feedback for UI events"""

    def __init__(self, sample_rate: int = 22050, enabled: bool = True, volume: float = 0.5):
        self.sample_rate = sample_rate
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self._lock = threading.Lock()

    def _generate_tone(
        self,
        frequency: float,
        duration: float,
        envelope: str = "linear"
    ) -> np.ndarray:
        """Generate a pure tone with envelope"""
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        tone = np.sin(2 * np.pi * frequency * t)

        # Apply envelope
        if envelope == "linear":
            # Quick attack, slow release
            attack = int(len(t) * 0.1)
            release = int(len(t) * 0.3)
            envelope_curve = np.ones_like(t)
            envelope_curve[:attack] = np.linspace(0, 1, attack)
            envelope_curve[-release:] = np.linspace(1, 0, release)
            tone *= envelope_curve
        elif envelope == "exponential":
            # Exponential decay
            envelope_curve = np.exp(-3 * t / duration)
            tone *= envelope_curve

        return tone * self.volume

    def _generate_chirp(
        self,
        start_freq: float,
        end_freq: float,
        duration: float
    ) -> np.ndarray:
        """Generate a frequency sweep (chirp)"""
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        # Linear frequency sweep
        freq = np.linspace(start_freq, end_freq, len(t))
        phase = 2 * np.pi * np.cumsum(freq) / self.sample_rate
        chirp = np.sin(phase)

        # Apply envelope
        attack = int(len(t) * 0.1)
        release = int(len(t) * 0.2)
        envelope = np.ones_like(t)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[-release:] = np.linspace(1, 0, release)

        return chirp * envelope * self.volume

    def _combine_sounds(self, *sounds: np.ndarray) -> np.ndarray:
        """Combine multiple sound arrays with silence between them"""
        silence_duration = 0.05  # 50ms silence
        silence = np.zeros(int(self.sample_rate * silence_duration))

        combined = []
        for i, sound in enumerate(sounds):
            combined.append(sound)
            if i < len(sounds) - 1:
                combined.append(silence)

        return np.concatenate(combined)

    def generate_sound(self, sound_type: SoundType) -> Optional[str]:
        """
        Generate audio for the given event type.

        Returns base64-encoded WAV data for embedding in HTML audio element,
        or None if audio is disabled or generation fails.
        """
        if not self.enabled or not SCIPY_AVAILABLE:
            return None

        with self._lock:
            try:
                # Generate sound based on type
                if sound_type == "chunk_complete":
                    # Happy ascending chirp
                    sound = self._generate_chirp(400, 800, 0.15)

                elif sound_type == "chunk_failed":
                    # Sad descending tone
                    sound = self._combine_sounds(
                        self._generate_tone(600, 0.1, "exponential"),
                        self._generate_tone(400, 0.15, "exponential"),
                    )

                elif sound_type == "chunk_retry":
                    # Quick double beep
                    sound = self._combine_sounds(
                        self._generate_tone(500, 0.08),
                        self._generate_tone(500, 0.08),
                    )

                elif sound_type == "phase_complete":
                    # Triumphant rising sequence
                    sound = self._combine_sounds(
                        self._generate_tone(500, 0.1),
                        self._generate_tone(650, 0.1),
                        self._generate_tone(800, 0.15),
                    )

                elif sound_type == "phase_failed":
                    # Warning descending sequence
                    sound = self._combine_sounds(
                        self._generate_tone(700, 0.12, "exponential"),
                        self._generate_tone(500, 0.12, "exponential"),
                        self._generate_tone(300, 0.15, "exponential"),
                    )

                elif sound_type == "pipeline_complete":
                    # Victory fanfare
                    sound = self._combine_sounds(
                        self._generate_chirp(400, 600, 0.12),
                        self._generate_chirp(500, 800, 0.12),
                        self._generate_tone(1000, 0.25),
                    )

                elif sound_type == "pipeline_failed":
                    # Sad trombone effect
                    sound = self._generate_chirp(500, 200, 0.4)

                elif sound_type == "warning":
                    # Alert double-tone
                    sound = self._combine_sounds(
                        self._generate_tone(800, 0.1),
                        self._generate_tone(600, 0.1),
                    )

                elif sound_type == "info":
                    # Gentle single beep
                    sound = self._generate_tone(550, 0.12)

                else:
                    logger.warning(f"Unknown sound type: {sound_type}")
                    return None

                # Normalize to int16 range
                sound_int16 = (sound * 32767).astype(np.int16)

                # Convert to WAV format in memory
                buffer = io.BytesIO()
                wavfile.write(buffer, self.sample_rate, sound_int16)
                wav_data = buffer.getvalue()

                # Encode as base64 for HTML
                b64_data = base64.b64encode(wav_data).decode('utf-8')
                return f"data:audio/wav;base64,{b64_data}"

            except Exception as e:
                logger.error(f"Failed to generate sound for {sound_type}: {e}")
                return None

    def set_volume(self, volume: float) -> None:
        """Update volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable audio feedback"""
        self.enabled = enabled
