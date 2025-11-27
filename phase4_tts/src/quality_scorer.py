"""
Audio Quality Scorer for TTS Output Validation

Analyzes generated audio chunks for quality issues:
- Signal-to-noise ratio (SNR)
- Voice stability across chunk
- Silence detection
- Spectral clarity
- Duration variance from expected

Used by Phase 4 to detect bad audio before mastering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import librosa
except ImportError:
    librosa = None

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Quality assessment result for an audio chunk."""

    audio_path: str
    overall_score: float  # 0.0 - 1.0
    is_acceptable: bool
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Individual metrics
    snr_db: Optional[float] = None
    silence_ratio: float = 0.0
    clipping_ratio: float = 0.0
    spectral_clarity: float = 0.0
    duration_variance: float = 0.0  # Ratio of actual/expected
    amplitude_db: float = -100.0

    # Thresholds used
    thresholds: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio_path": self.audio_path,
            "overall_score": self.overall_score,
            "is_acceptable": self.is_acceptable,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "metrics": {
                "snr_db": self.snr_db,
                "silence_ratio": self.silence_ratio,
                "clipping_ratio": self.clipping_ratio,
                "spectral_clarity": self.spectral_clarity,
                "duration_variance": self.duration_variance,
                "amplitude_db": self.amplitude_db,
            },
            "thresholds": self.thresholds,
        }


@dataclass
class QualityConfig:
    """Configuration for quality scoring thresholds."""

    # Minimum acceptable values
    min_snr_db: float = 15.0  # Minimum signal-to-noise ratio
    min_amplitude_db: float = -40.0  # Minimum peak amplitude
    min_spectral_clarity: float = 0.3  # Minimum spectral clarity score

    # Maximum acceptable values
    max_silence_ratio: float = 0.3  # Max 30% silence
    max_clipping_ratio: float = 0.01  # Max 1% clipping
    max_duration_variance: float = 0.5  # Max 50% deviation from expected

    # Scoring weights
    snr_weight: float = 0.25
    silence_weight: float = 0.20
    clipping_weight: float = 0.15
    spectral_weight: float = 0.20
    duration_weight: float = 0.20

    # Overall threshold
    min_acceptable_score: float = 0.6

    # Speech rate estimation
    chars_per_minute: int = 1050  # Average speaking rate


class AudioQualityScorer:
    """
    Analyze audio quality for TTS-generated chunks.

    Usage:
        scorer = AudioQualityScorer()
        result = scorer.score("chunk_0001.wav", expected_chars=500)
        if not result.is_acceptable:
            print(f"Issues: {result.issues}")
            print(f"Recommendations: {result.recommendations}")
    """

    def __init__(self, config: Optional[QualityConfig] = None):
        self.config = config or QualityConfig()
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Verify required libraries are available."""
        if sf is None:
            logger.warning("soundfile not installed - some features disabled")
        if librosa is None:
            logger.warning("librosa not installed - spectral analysis disabled")

    def score(
        self,
        audio_path: str | Path,
        expected_chars: Optional[int] = None,
        expected_duration: Optional[float] = None,
    ) -> QualityScore:
        """
        Score audio quality for a TTS-generated chunk.

        Args:
            audio_path: Path to audio file (.wav)
            expected_chars: Number of characters in source text
            expected_duration: Expected duration in seconds (if known)

        Returns:
            QualityScore with metrics and recommendations
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            return QualityScore(
                audio_path=str(audio_path),
                overall_score=0.0,
                is_acceptable=False,
                issues=["Audio file not found"],
                recommendations=["Re-synthesize chunk"],
            )

        try:
            audio, sample_rate = self._load_audio(audio_path)
        except Exception as e:
            logger.error("Failed to load audio %s: %s", audio_path, e)
            return QualityScore(
                audio_path=str(audio_path),
                overall_score=0.0,
                is_acceptable=False,
                issues=[f"Failed to load audio: {e}"],
                recommendations=["Re-synthesize chunk"],
            )

        if len(audio) == 0:
            return QualityScore(
                audio_path=str(audio_path),
                overall_score=0.0,
                is_acceptable=False,
                issues=["Audio file is empty"],
                recommendations=["Re-synthesize chunk"],
            )

        # Calculate metrics
        duration = len(audio) / sample_rate
        snr_db = self._compute_snr(audio, sample_rate)
        silence_ratio = self._compute_silence_ratio(audio, sample_rate)
        clipping_ratio = self._compute_clipping_ratio(audio)
        spectral_clarity = self._compute_spectral_clarity(audio, sample_rate)
        amplitude_db = self._compute_amplitude_db(audio)

        # Duration variance
        duration_variance = 0.0
        if expected_duration:
            duration_variance = abs(duration - expected_duration) / max(expected_duration, 0.1)
        elif expected_chars:
            expected_dur = (expected_chars / self.config.chars_per_minute) * 60.0
            duration_variance = abs(duration - expected_dur) / max(expected_dur, 0.1)

        # Compute individual scores (0-1 scale)
        scores = {}

        # SNR score (higher is better)
        if snr_db is not None:
            snr_score = min(1.0, max(0.0, (snr_db - 5) / (self.config.min_snr_db - 5)))
            scores["snr"] = snr_score
        else:
            scores["snr"] = 0.5  # Unknown, assume neutral

        # Silence score (lower silence is better)
        silence_score = 1.0 - min(1.0, silence_ratio / self.config.max_silence_ratio)
        scores["silence"] = silence_score

        # Clipping score (lower clipping is better)
        clipping_score = 1.0 - min(1.0, clipping_ratio / self.config.max_clipping_ratio)
        scores["clipping"] = clipping_score

        # Spectral clarity score
        spectral_score = min(1.0, spectral_clarity / self.config.min_spectral_clarity)
        scores["spectral"] = spectral_score

        # Duration score (closer to expected is better)
        duration_score = 1.0 - min(1.0, duration_variance / self.config.max_duration_variance)
        scores["duration"] = duration_score

        # Weighted overall score
        overall_score = (
            scores["snr"] * self.config.snr_weight
            + scores["silence"] * self.config.silence_weight
            + scores["clipping"] * self.config.clipping_weight
            + scores["spectral"] * self.config.spectral_weight
            + scores["duration"] * self.config.duration_weight
        )

        # Identify issues and recommendations
        issues = []
        recommendations = []

        if snr_db is not None and snr_db < self.config.min_snr_db:
            issues.append(f"Low SNR ({snr_db:.1f}dB < {self.config.min_snr_db}dB)")
            recommendations.append("Try different engine or reduce background noise in reference")

        if silence_ratio > self.config.max_silence_ratio:
            issues.append(f"High silence ratio ({silence_ratio:.1%} > {self.config.max_silence_ratio:.0%})")
            recommendations.append("Check for hallucinations or pause issues")

        if clipping_ratio > self.config.max_clipping_ratio:
            issues.append(f"Audio clipping detected ({clipping_ratio:.2%})")
            recommendations.append("Reduce synthesis amplitude or apply limiter")

        if spectral_clarity < self.config.min_spectral_clarity:
            issues.append(f"Low spectral clarity ({spectral_clarity:.2f})")
            recommendations.append("Try different voice or engine")

        if duration_variance > self.config.max_duration_variance:
            issues.append(f"Duration variance too high ({duration_variance:.1%})")
            recommendations.append("Check for skipped text or hallucinations")

        if amplitude_db < self.config.min_amplitude_db:
            issues.append(f"Audio too quiet ({amplitude_db:.1f}dB)")
            recommendations.append("Normalize audio or check synthesis parameters")

        is_acceptable = overall_score >= self.config.min_acceptable_score and len(issues) == 0

        return QualityScore(
            audio_path=str(audio_path),
            overall_score=overall_score,
            is_acceptable=is_acceptable,
            issues=issues,
            recommendations=recommendations,
            snr_db=snr_db,
            silence_ratio=silence_ratio,
            clipping_ratio=clipping_ratio,
            spectral_clarity=spectral_clarity,
            duration_variance=duration_variance,
            amplitude_db=amplitude_db,
            thresholds={
                "min_snr_db": self.config.min_snr_db,
                "max_silence_ratio": self.config.max_silence_ratio,
                "max_clipping_ratio": self.config.max_clipping_ratio,
                "min_spectral_clarity": self.config.min_spectral_clarity,
                "max_duration_variance": self.config.max_duration_variance,
                "min_acceptable_score": self.config.min_acceptable_score,
            },
        )

    def _load_audio(self, audio_path: Path) -> Tuple[np.ndarray, int]:
        """Load audio file and return (samples, sample_rate)."""
        if sf is not None:
            audio, sr = sf.read(str(audio_path))
            # Convert to mono if stereo
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            return audio.astype(np.float32), sr

        # Fallback to librosa
        if librosa is not None:
            audio, sr = librosa.load(str(audio_path), sr=None, mono=True)
            return audio.astype(np.float32), sr

        raise ImportError("Neither soundfile nor librosa available")

    def _compute_snr(self, audio: np.ndarray, sample_rate: int) -> Optional[float]:
        """Estimate signal-to-noise ratio in dB."""
        try:
            # Simple SNR estimation: compare RMS of signal vs noise floor
            # Noise is estimated from the quietest 10% of frames
            frame_size = int(sample_rate * 0.025)  # 25ms frames
            hop_size = int(sample_rate * 0.010)  # 10ms hop

            frames = []
            for i in range(0, len(audio) - frame_size, hop_size):
                frame = audio[i : i + frame_size]
                rms = np.sqrt(np.mean(frame**2))
                if rms > 0:
                    frames.append(rms)

            if not frames:
                return None

            frames = np.array(frames)
            # Noise floor: 10th percentile
            noise_floor = np.percentile(frames, 10)
            # Signal: 90th percentile
            signal_level = np.percentile(frames, 90)

            if noise_floor > 0 and signal_level > noise_floor:
                snr = 20 * np.log10(signal_level / noise_floor)
                return float(snr)

            return None

        except Exception as e:
            logger.warning("SNR computation failed: %s", e)
            return None

    def _compute_silence_ratio(self, audio: np.ndarray, sample_rate: int) -> float:
        """Compute ratio of audio that is silent."""
        try:
            # Silence threshold: -40dB below peak
            peak = np.max(np.abs(audio))
            if peak == 0:
                return 1.0

            threshold = peak * 0.01  # -40dB
            silent_samples = np.sum(np.abs(audio) < threshold)
            return float(silent_samples / len(audio))

        except Exception as e:
            logger.warning("Silence ratio computation failed: %s", e)
            return 0.0

    def _compute_clipping_ratio(self, audio: np.ndarray) -> float:
        """Compute ratio of samples that are clipped."""
        try:
            # Count samples at or near maximum
            clipping_threshold = 0.99
            clipped = np.sum(np.abs(audio) >= clipping_threshold)
            return float(clipped / len(audio))

        except Exception as e:
            logger.warning("Clipping ratio computation failed: %s", e)
            return 0.0

    def _compute_spectral_clarity(self, audio: np.ndarray, sample_rate: int) -> float:
        """
        Compute spectral clarity score.

        Higher values indicate clearer, more distinct speech.
        Uses spectral centroid and flatness if librosa available.
        """
        if librosa is None:
            # Fallback: use simple energy variance
            try:
                frame_size = int(sample_rate * 0.025)
                hop_size = int(sample_rate * 0.010)

                energies = []
                for i in range(0, len(audio) - frame_size, hop_size):
                    frame = audio[i : i + frame_size]
                    energy = np.sum(frame**2)
                    energies.append(energy)

                if energies:
                    variance = np.var(energies) / (np.mean(energies) + 1e-10)
                    # Normalize to 0-1 range (empirical scaling)
                    return min(1.0, variance / 10.0)

            except Exception as e:
                logger.warning("Fallback spectral clarity failed: %s", e)

            return 0.5  # Neutral if we can't compute

        try:
            # Use librosa for proper spectral analysis
            # Spectral centroid: center of mass of spectrum
            centroid = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)[0]

            # Spectral flatness: how noise-like vs tonal
            flatness = librosa.feature.spectral_flatness(y=audio)[0]

            # Higher centroid + lower flatness = clearer speech
            avg_centroid = np.mean(centroid) / (sample_rate / 2)  # Normalize
            avg_flatness = np.mean(flatness)

            # Combine: high centroid (speech formants) + low flatness (tonal)
            clarity = (avg_centroid * 0.5 + (1 - avg_flatness) * 0.5)
            return float(min(1.0, clarity * 2))  # Scale to 0-1

        except Exception as e:
            logger.warning("Spectral clarity computation failed: %s", e)
            return 0.5

    def _compute_amplitude_db(self, audio: np.ndarray) -> float:
        """Compute peak amplitude in dB."""
        try:
            peak = np.max(np.abs(audio))
            if peak > 0:
                return float(20 * np.log10(peak))
            return -100.0
        except Exception as e:
            logger.warning("Amplitude computation failed: %s", e)
            return -100.0

    def batch_score(
        self,
        audio_paths: List[str | Path],
        expected_chars_list: Optional[List[int]] = None,
    ) -> List[QualityScore]:
        """Score multiple audio files."""
        results = []
        for i, audio_path in enumerate(audio_paths):
            expected_chars = expected_chars_list[i] if expected_chars_list and i < len(expected_chars_list) else None
            results.append(self.score(audio_path, expected_chars=expected_chars))
        return results


def quick_check(audio_path: str | Path) -> bool:
    """
    Quick quality check - returns True if audio passes basic thresholds.

    Use this for fast screening during synthesis.
    """
    scorer = AudioQualityScorer()
    result = scorer.score(audio_path)
    return result.is_acceptable


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python quality_scorer.py <audio_file.wav> [expected_chars]")
        sys.exit(1)

    audio_file = sys.argv[1]
    expected = int(sys.argv[2]) if len(sys.argv) > 2 else None

    scorer = AudioQualityScorer()
    result = scorer.score(audio_file, expected_chars=expected)

    print(f"\nQuality Score: {result.overall_score:.2f}")
    print(f"Acceptable: {result.is_acceptable}")
    print("\nMetrics:")
    print(f"  SNR: {result.snr_db:.1f} dB" if result.snr_db else "  SNR: N/A")
    print(f"  Silence Ratio: {result.silence_ratio:.1%}")
    print(f"  Clipping Ratio: {result.clipping_ratio:.2%}")
    print(f"  Spectral Clarity: {result.spectral_clarity:.2f}")
    print(f"  Duration Variance: {result.duration_variance:.1%}")
    print(f"  Amplitude: {result.amplitude_db:.1f} dB")

    if result.issues:
        print("\nIssues:")
        for issue in result.issues:
            print(f"  - {issue}")

    if result.recommendations:
        print("\nRecommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")
