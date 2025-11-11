"""
Professional Audio Mastering System
Implements preset-based mastering chains for audiobook production
"""

import logging
import numpy as np
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MasteringResult:
    """Result of mastering operation"""
    audio: np.ndarray
    sample_rate: int
    preset_name: str
    metrics: Dict[str, float]
    processing_time_sec: float


class AudioProcessor:
    """
    Professional audio processing using multiple libraries

    Uses:
    - pedalboard (Spotify's audio effects) - preferred
    - pyloudnorm (LUFS normalization)
    - librosa (analysis)
    - numpy (core processing)
    """

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self._pedalboard_available = False
        self._load_dependencies()

    def _load_dependencies(self):
        """Lazy load audio processing libraries"""
        try:
            import pedalboard
            self._pedalboard_available = True
            self.pedalboard = pedalboard
            logger.info("Pedalboard available - using professional effects")
        except ImportError:
            logger.warning(
                "Pedalboard not installed. Install with: pip install pedalboard\n"
                "Falling back to basic processing."
            )

    def process_chain(
        self,
        audio: np.ndarray,
        chain: List[Dict[str, Any]],
        sample_rate: Optional[int] = None
    ) -> np.ndarray:
        """
        Process audio through a chain of effects

        Args:
            audio: Input audio (mono or stereo, float32)
            chain: List of processing steps from preset
            sample_rate: Override sample rate

        Returns:
            Processed audio (same shape as input)
        """
        sr = sample_rate or self.sample_rate
        processed = audio.copy()

        for step in chain:
            effect_type = step.get("type")

            try:
                if effect_type == "noise_gate":
                    processed = self._noise_gate(processed, sr, step)
                elif effect_type == "eq":
                    processed = self._eq(processed, sr, step)
                elif effect_type == "compressor":
                    processed = self._compressor(processed, sr, step)
                elif effect_type == "multiband_compressor":
                    processed = self._multiband_compressor(processed, sr, step)
                elif effect_type == "limiter":
                    processed = self._limiter(processed, sr, step)
                elif effect_type == "harmonic_exciter":
                    processed = self._harmonic_exciter(processed, sr, step)
                elif effect_type == "transient_shaper":
                    processed = self._transient_shaper(processed, sr, step)
                elif effect_type == "stereo_widener":
                    processed = self._stereo_widener(processed, sr, step)
                elif effect_type == "lufs_normalize":
                    processed = self._lufs_normalize(processed, sr, step)
                else:
                    logger.warning(f"Unknown effect type: {effect_type}")

            except Exception as e:
                logger.error(f"Effect {effect_type} failed: {e}")
                # Continue processing, skip failed effect

        return processed

    def _noise_gate(
        self,
        audio: np.ndarray,
        sr: int,
        params: Dict
    ) -> np.ndarray:
        """Noise gate - removes audio below threshold"""
        if not self._pedalboard_available:
            return self._basic_gate(audio, params)

        from pedalboard import NoiseGate

        threshold_db = params.get("threshold_db", -40)
        ratio_db = params.get("ratio", 10)
        attack_ms = params.get("attack_ms", 1)
        release_ms = params.get("release_ms", 100)

        gate = NoiseGate(
            threshold_db=threshold_db,
            ratio=ratio_db,
            attack_ms=attack_ms,
            release_ms=release_ms
        )

        # Ensure 2D array for pedalboard
        if audio.ndim == 1:
            audio_2d = audio.reshape(1, -1)
        else:
            audio_2d = audio

        return gate(audio_2d, sr).reshape(audio.shape)

    def _basic_gate(self, audio: np.ndarray, params: Dict) -> np.ndarray:
        """Fallback gate using numpy"""
        threshold_db = params.get("threshold_db", -40)
        threshold_linear = 10 ** (threshold_db / 20)

        mask = np.abs(audio) > threshold_linear
        return audio * mask

    def _eq(self, audio: np.ndarray, sr: int, params: Dict) -> np.ndarray:
        """Parametric EQ"""
        if not self._pedalboard_available:
            return audio  # Skip if pedalboard not available

        from pedalboard import Pedalboard, HighpassFilter, LowShelfFilter, PeakFilter

        effects = []

        # High-pass filter
        if "high_pass_hz" in params:
            effects.append(HighpassFilter(cutoff_frequency_hz=params["high_pass_hz"]))

        # Low shelf
        if "low_shelf" in params:
            shelf = params["low_shelf"]
            effects.append(LowShelfFilter(
                cutoff_frequency_hz=shelf["freq_hz"],
                gain_db=shelf["gain_db"]
            ))

        # Presence boost
        if "presence" in params:
            pres = params["presence"]
            effects.append(PeakFilter(
                cutoff_frequency_hz=pres["freq_hz"],
                gain_db=pres["gain_db"],
                q=pres.get("q", 1.0)
            ))

        # Brightness (high shelf)
        if "brightness" in params:
            bright = params["brightness"]
            if bright.get("shelf"):
                # Would need HighShelfFilter from pedalboard
                pass

        board = Pedalboard(effects)

        if audio.ndim == 1:
            audio_2d = audio.reshape(1, -1)
        else:
            audio_2d = audio

        return board(audio_2d, sr).reshape(audio.shape)

    def _compressor(
        self,
        audio: np.ndarray,
        sr: int,
        params: Dict
    ) -> np.ndarray:
        """Standard compressor"""
        if not self._pedalboard_available:
            return self._basic_compressor(audio, params)

        from pedalboard import Compressor

        compressor = Compressor(
            threshold_db=params.get("threshold_db", -20),
            ratio=params.get("ratio", 4.0),
            attack_ms=params.get("attack_ms", 5),
            release_ms=params.get("release_ms", 100)
        )

        if audio.ndim == 1:
            audio_2d = audio.reshape(1, -1)
        else:
            audio_2d = audio

        return compressor(audio_2d, sr).reshape(audio.shape)

    def _basic_compressor(self, audio: np.ndarray, params: Dict) -> np.ndarray:
        """Simple compressor fallback"""
        threshold_db = params.get("threshold_db", -20)
        ratio = params.get("ratio", 4.0)

        threshold_linear = 10 ** (threshold_db / 20)

        # Simple hard-knee compression
        mask = np.abs(audio) > threshold_linear
        compressed = audio.copy()

        over_threshold = np.abs(audio) - threshold_linear
        gain_reduction = 1 - (1 - 1/ratio) * (over_threshold / np.abs(audio))

        compressed[mask] *= gain_reduction[mask]

        return compressed

    def _multiband_compressor(
        self,
        audio: np.ndarray,
        sr: int,
        params: Dict
    ) -> np.ndarray:
        """
        Multi-band compressor - the secret sauce for pro sound

        Splits audio into frequency bands and compresses separately
        """
        import scipy.signal as signal

        bands = params.get("bands", [])
        if not bands:
            return audio

        # Accumulator for output
        output = np.zeros_like(audio)

        for band_params in bands:
            freq_range = band_params.get("freq_range", [20, 20000])
            low_freq, high_freq = freq_range

            # Design bandpass filter
            sos = signal.butter(
                4,  # Order
                [low_freq, high_freq],
                btype='bandpass',
                fs=sr,
                output='sos'
            )

            # Extract band
            band_audio = signal.sosfilt(sos, audio)

            # Compress band
            compressed_band = self._compressor(band_audio, sr, band_params)

            # Add to output
            output += compressed_band

        return output

    def _limiter(
        self,
        audio: np.ndarray,
        sr: int,
        params: Dict
    ) -> np.ndarray:
        """Limiter - prevents clipping"""
        if not self._pedalboard_available:
            return self._basic_limiter(audio, params)

        from pedalboard import Limiter

        limiter = Limiter(
            threshold_db=params.get("ceiling_db", -1.0),
            release_ms=params.get("release_ms", 100)
        )

        if audio.ndim == 1:
            audio_2d = audio.reshape(1, -1)
        else:
            audio_2d = audio

        return limiter(audio_2d, sr).reshape(audio.shape)

    def _basic_limiter(self, audio: np.ndarray, params: Dict) -> np.ndarray:
        """Simple limiter fallback"""
        ceiling_db = params.get("ceiling_db", -1.0)
        ceiling_linear = 10 ** (ceiling_db / 20)

        return np.clip(audio, -ceiling_linear, ceiling_linear)

    def _harmonic_exciter(
        self,
        audio: np.ndarray,
        sr: int,
        params: Dict
    ) -> np.ndarray:
        """Add harmonic saturation for warmth"""
        amount = params.get("amount", 0.1)

        # Simple tube-style saturation
        excited = np.tanh(audio * (1 + amount * 2))

        # Blend with original
        return audio * (1 - amount) + excited * amount

    def _transient_shaper(
        self,
        audio: np.ndarray,
        sr: int,
        params: Dict
    ) -> np.ndarray:
        """Enhance or reduce transients (attack)"""
        attack_db = params.get("attack_db", 0)

        if attack_db == 0:
            return audio

        # Detect transients using envelope
        envelope = np.abs(audio)

        # Smooth envelope
        from scipy.ndimage import maximum_filter1d
        smooth_env = maximum_filter1d(envelope, size=int(sr * 0.01))

        # Transient mask
        transient_mask = (envelope > smooth_env * 1.2).astype(float)

        # Apply gain to transients
        gain = 10 ** (attack_db / 20)
        return audio * (1 + transient_mask * (gain - 1))

    def _stereo_widener(
        self,
        audio: np.ndarray,
        sr: int,
        params: Dict
    ) -> np.ndarray:
        """Widen stereo image (only works on stereo)"""
        if audio.ndim == 1:
            return audio  # Can't widen mono

        width_percent = params.get("width_percent", 0)
        if width_percent == 0:
            return audio

        # Mid-side processing
        mid = (audio[0] + audio[1]) / 2
        side = (audio[0] - audio[1]) / 2

        # Widen
        width_factor = 1 + (width_percent / 100)
        side_widened = side * width_factor

        # Convert back to L/R
        left = mid + side_widened
        right = mid - side_widened

        return np.stack([left, right])

    def _lufs_normalize(
        self,
        audio: np.ndarray,
        sr: int,
        params: Dict
    ) -> np.ndarray:
        """LUFS normalization - industry standard loudness"""
        try:
            import pyloudnorm as pln

            target_lufs = params.get("target_lufs", -23.0)
            max_peak_db = params.get("max_true_peak_db", -1.0)

            # Measure current loudness
            meter = pln.Meter(sr)

            # pyloudnorm needs 2D array
            if audio.ndim == 1:
                audio_2d = audio.reshape(-1, 1)
            else:
                audio_2d = audio.T  # (samples, channels)

            loudness = meter.integrated_loudness(audio_2d)

            # Normalize
            normalized = pln.normalize.loudness(
                audio_2d,
                loudness,
                target_lufs
            )

            # Peak limit
            peak = np.max(np.abs(normalized))
            max_peak_linear = 10 ** (max_peak_db / 20)

            if peak > max_peak_linear:
                normalized *= max_peak_linear / peak

            # Restore original shape
            if audio.ndim == 1:
                normalized = normalized.flatten()
            else:
                normalized = normalized.T

            return normalized

        except ImportError:
            logger.warning("pyloudnorm not installed, using peak normalization")
            return self._peak_normalize(audio, params)
        except Exception as e:
            logger.error(f"LUFS normalization failed: {e}")
            return audio

    def _peak_normalize(self, audio: np.ndarray, params: Dict) -> np.ndarray:
        """Fallback peak normalization"""
        target_db = params.get("target_lufs", -23.0)
        target_linear = 10 ** (target_db / 20)

        peak = np.max(np.abs(audio))
        if peak > 0:
            return audio * (target_linear / peak)
        return audio


class MasteringEngine:
    """
    Main mastering engine - loads presets and processes audio
    """

    def __init__(self, presets_path: Optional[Path] = None):
        if presets_path is None:
            presets_path = Path(__file__).parent.parent.parent / "presets" / "mastering_presets.yaml"

        self.presets_path = presets_path
        self.presets = self._load_presets()
        self.processor = AudioProcessor()

    def _load_presets(self) -> Dict[str, Any]:
        """Load mastering presets from YAML"""
        try:
            with open(self.presets_path, 'r') as f:
                data = yaml.safe_load(f)
            logger.info(f"Loaded {len(data['presets'])} mastering presets")
            return data['presets']
        except Exception as e:
            logger.error(f"Failed to load presets: {e}")
            return {}

    def master(
        self,
        audio: np.ndarray,
        sample_rate: int,
        preset: str = "audiobook_intimate"
    ) -> MasteringResult:
        """
        Master audio using specified preset

        Args:
            audio: Input audio (mono or stereo, float32)
            sample_rate: Sample rate
            preset: Preset name

        Returns:
            MasteringResult with processed audio and metrics
        """
        import time

        start_time = time.perf_counter()

        # Get preset
        if preset not in self.presets:
            logger.warning(f"Preset '{preset}' not found, using default")
            preset = "audiobook_intimate"

        preset_config = self.presets[preset]
        chain = preset_config.get("chain", [])

        logger.info(f"Mastering with preset: {preset}")

        # Process
        processed = self.processor.process_chain(audio, chain, sample_rate)

        # Calculate metrics
        metrics = self._calculate_metrics(processed, sample_rate, preset_config)

        processing_time = time.perf_counter() - start_time

        return MasteringResult(
            audio=processed,
            sample_rate=sample_rate,
            preset_name=preset,
            metrics=metrics,
            processing_time_sec=processing_time
        )

    def _calculate_metrics(
        self,
        audio: np.ndarray,
        sample_rate: int,
        preset_config: Dict
    ) -> Dict[str, float]:
        """Calculate audio quality metrics"""
        metrics = {}

        # RMS
        metrics['rms'] = float(np.sqrt(np.mean(audio ** 2)))

        # Peak
        metrics['peak'] = float(np.max(np.abs(audio)))
        metrics['peak_db'] = float(20 * np.log10(metrics['peak']) if metrics['peak'] > 0 else -np.inf)

        # Dynamic range (rough estimate)
        percentile_10 = np.percentile(np.abs(audio), 10)
        percentile_90 = np.percentile(np.abs(audio), 90)
        if percentile_10 > 0:
            metrics['dynamic_range_db'] = float(20 * np.log10(percentile_90 / percentile_10))
        else:
            metrics['dynamic_range_db'] = 0.0

        # LUFS (if available)
        try:
            import pyloudnorm as pln
            meter = pln.Meter(sample_rate)
            audio_2d = audio.reshape(-1, 1) if audio.ndim == 1 else audio.T
            metrics['lufs'] = float(meter.integrated_loudness(audio_2d))
        except:
            metrics['lufs'] = None

        # Target compliance
        targets = preset_config.get('targets', {})
        if 'dynamic_range_db' in targets:
            target_dr = targets['dynamic_range_db']
            metrics['dynamic_range_compliance'] = abs(metrics['dynamic_range_db'] - target_dr) < 2.0

        return metrics

    def list_presets(self) -> Dict[str, str]:
        """List available presets with descriptions"""
        return {
            name: config.get("description", "")
            for name, config in self.presets.items()
        }

    def get_recommended_preset(self, genre: str) -> str:
        """Get recommended preset for genre"""
        try:
            with open(self.presets_path, 'r') as f:
                data = yaml.safe_load(f)
            recommendations = data.get('recommendations', {})
            return recommendations.get(genre.lower(), 'audiobook_intimate')
        except:
            return 'audiobook_intimate'
