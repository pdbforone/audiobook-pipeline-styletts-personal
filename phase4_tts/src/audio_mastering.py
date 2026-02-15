"""
Audio Mastering Chain for ACX Compliance

Applies deterministic signal processing to ensure synthesized audio meets
Audible/ACX audiobook standards:
- RMS Amplitude: -23dB to -18dB
- True Peak: Max -3.0dB
- Noise Floor: Max -60dB RMS

This module implements the research findings from Gemini Deep Research:
"Don't rely on TTS engines to get volume right. Apply deterministic post-processing."

Reference: TTS_VALIDATION_RESEARCH_FINDINGS.md
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

# Try to import pyloudnorm for LUFS-based normalization
PYLOUDNORM_AVAILABLE = False
try:
    import pyloudnorm as pyln
    PYLOUDNORM_AVAILABLE = True
    logger.debug("✅ pyloudnorm available for LUFS-based mastering")
except ImportError:
    logger.warning("⚠️  pyloudnorm not installed - falling back to RMS normalization")


# ACX/Audible Standards
ACX_TARGET_LUFS = -20.0        # Target loudness (LUFS)
ACX_RMS_MIN_DB = -23.0         # Minimum RMS amplitude
ACX_RMS_MAX_DB = -18.0         # Maximum RMS amplitude
ACX_TRUE_PEAK_MAX_DB = -3.0    # Maximum true peak
ACX_NOISE_FLOOR_MAX_DB = -60.0 # Maximum noise floor in silence


def calculate_rms_db(audio: np.ndarray) -> float:
    """Calculate RMS amplitude in dB."""
    rms = np.sqrt(np.mean(audio**2))
    if rms < 1e-10:
        return -100.0
    return 20 * np.log10(rms)


def calculate_peak_db(audio: np.ndarray) -> float:
    """Calculate peak amplitude in dB."""
    peak = np.max(np.abs(audio))
    if peak < 1e-10:
        return -100.0
    return 20 * np.log10(peak)


def calculate_lufs(audio: np.ndarray, sample_rate: int) -> float:
    """
    Calculate integrated loudness in LUFS.

    Falls back to RMS estimation if pyloudnorm unavailable.
    """
    if PYLOUDNORM_AVAILABLE:
        try:
            meter = pyln.Meter(sample_rate)
            # Handle mono/stereo
            if audio.ndim == 1:
                loudness = meter.integrated_loudness(audio)
            else:
                loudness = meter.integrated_loudness(audio.T)
            return loudness
        except Exception as e:
            logger.warning(f"LUFS calculation failed, falling back to RMS: {e}")

    # Fallback: RMS approximation (LUFS ≈ RMS - 3dB for speech)
    rms_db = calculate_rms_db(audio)
    return rms_db - 3.0  # Approximate LUFS from RMS


def calculate_noise_floor_db(audio: np.ndarray, silence_threshold: float = 0.01) -> float:
    """
    Calculate noise floor in silent regions.

    Args:
        audio: Audio samples (normalized to -1.0 to 1.0)
        silence_threshold: Linear threshold for detecting silence (default: -40dB)

    Returns:
        Noise floor RMS in dB, or -100 if no silence detected
    """
    # Find silent regions (amplitude below threshold)
    silent_mask = np.abs(audio) < silence_threshold

    if not np.any(silent_mask):
        return -100.0  # No silence detected

    silent_samples = audio[silent_mask]
    if len(silent_samples) < 100:
        return -100.0  # Not enough silence samples

    noise_rms = np.sqrt(np.mean(silent_samples**2))
    if noise_rms < 1e-10:
        return -100.0

    return 20 * np.log10(noise_rms)


def apply_loudness_normalization(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = ACX_TARGET_LUFS
) -> np.ndarray:
    """
    Normalize audio to target loudness (LUFS).

    Args:
        audio: Input audio samples
        sample_rate: Audio sample rate
        target_lufs: Target loudness in LUFS (default: -20)

    Returns:
        Normalized audio samples
    """
    if PYLOUDNORM_AVAILABLE:
        try:
            meter = pyln.Meter(sample_rate)
            current_loudness = meter.integrated_loudness(audio)

            if np.isinf(current_loudness) or current_loudness < -70:
                logger.warning("Audio too quiet for LUFS normalization, using RMS fallback")
            else:
                normalized = pyln.normalize.loudness(audio, current_loudness, target_lufs)
                return normalized
        except Exception as e:
            logger.warning(f"LUFS normalization failed: {e}")

    # Fallback: RMS-based normalization
    current_rms_db = calculate_rms_db(audio)
    target_rms_db = target_lufs + 3.0  # Approximate RMS from LUFS

    if current_rms_db < -60:
        logger.warning("Audio too quiet for RMS normalization")
        return audio

    gain_db = target_rms_db - current_rms_db
    gain_linear = 10 ** (gain_db / 20)

    return audio * gain_linear


def apply_true_peak_limiter(
    audio: np.ndarray,
    max_peak_db: float = ACX_TRUE_PEAK_MAX_DB
) -> np.ndarray:
    """
    Apply true peak limiting to prevent clipping.

    Args:
        audio: Input audio samples
        max_peak_db: Maximum allowed peak in dB (default: -3.0)

    Returns:
        Limited audio samples
    """
    max_peak_linear = 10 ** (max_peak_db / 20)
    current_peak = np.max(np.abs(audio))

    if current_peak > max_peak_linear:
        # Apply soft limiting
        scale_factor = max_peak_linear / current_peak
        audio = audio * scale_factor
        logger.debug(f"Applied peak limiter: reduced by {20 * np.log10(scale_factor):.1f}dB")

    return audio


def apply_noise_gate(
    audio: np.ndarray,
    threshold_db: float = -50.0,
    reduction_db: float = -20.0
) -> np.ndarray:
    """
    Apply gentle noise gate to reduce noise floor in silent regions.

    Args:
        audio: Input audio samples
        threshold_db: Gate threshold in dB (below this = "silence")
        reduction_db: Gain reduction applied to silent regions

    Returns:
        Gated audio samples
    """
    threshold_linear = 10 ** (threshold_db / 20)
    reduction_linear = 10 ** (reduction_db / 20)

    # Create envelope using RMS windowing
    window_size = 1024
    hop_size = 512

    envelope = np.zeros_like(audio)
    for i in range(0, len(audio) - window_size, hop_size):
        window_rms = np.sqrt(np.mean(audio[i:i+window_size]**2))
        envelope[i:i+hop_size] = window_rms

    # Apply gentle reduction to quiet regions
    gate_mask = envelope < threshold_linear
    gated_audio = audio.copy()
    gated_audio[gate_mask] *= reduction_linear

    return gated_audio


def master_audio_chunk(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = ACX_TARGET_LUFS,
    max_peak_db: float = ACX_TRUE_PEAK_MAX_DB,
    apply_gate: bool = False,
    gate_threshold_db: float = -50.0
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Apply full ACX-compliant mastering chain to synthesized audio.

    Chain:
    1. Loudness normalization to target LUFS
    2. True peak limiting at max_peak_db
    3. Optional noise gate for XTTS room tone

    Args:
        audio: Input audio samples (numpy array)
        sample_rate: Audio sample rate
        target_lufs: Target loudness in LUFS (default: -20)
        max_peak_db: Maximum true peak in dB (default: -3.0)
        apply_gate: Whether to apply noise gate (recommended for XTTS)
        gate_threshold_db: Noise gate threshold

    Returns:
        Tuple of (mastered_audio, metrics_dict)
    """
    metrics = {
        "input_rms_db": calculate_rms_db(audio),
        "input_peak_db": calculate_peak_db(audio),
        "input_lufs": calculate_lufs(audio, sample_rate),
        "input_noise_floor_db": calculate_noise_floor_db(audio),
    }

    logger.debug(
        f"Mastering input: RMS={metrics['input_rms_db']:.1f}dB, "
        f"Peak={metrics['input_peak_db']:.1f}dB, "
        f"LUFS={metrics['input_lufs']:.1f}"
    )

    # Step 1: Loudness normalization
    audio = apply_loudness_normalization(audio, sample_rate, target_lufs)

    # Step 2: True peak limiting
    audio = apply_true_peak_limiter(audio, max_peak_db)

    # Step 3: Optional noise gate
    if apply_gate:
        audio = apply_noise_gate(audio, gate_threshold_db)

    # Calculate output metrics
    metrics.update({
        "output_rms_db": calculate_rms_db(audio),
        "output_peak_db": calculate_peak_db(audio),
        "output_lufs": calculate_lufs(audio, sample_rate),
        "output_noise_floor_db": calculate_noise_floor_db(audio),
        "target_lufs": target_lufs,
        "max_peak_db": max_peak_db,
        "gate_applied": apply_gate,
    })

    logger.debug(
        f"Mastering output: RMS={metrics['output_rms_db']:.1f}dB, "
        f"Peak={metrics['output_peak_db']:.1f}dB, "
        f"LUFS={metrics['output_lufs']:.1f}"
    )

    return audio, metrics


def validate_acx_compliance(
    audio: np.ndarray,
    sample_rate: int
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that audio meets ACX/Audible specifications.

    Checks:
    - RMS amplitude: -23dB to -18dB
    - True peak: Max -3.0dB
    - Noise floor: Max -60dB

    Args:
        audio: Audio samples to validate
        sample_rate: Audio sample rate

    Returns:
        Tuple of (is_compliant, validation_details)
    """
    rms_db = calculate_rms_db(audio)
    peak_db = calculate_peak_db(audio)
    lufs = calculate_lufs(audio, sample_rate)
    noise_floor_db = calculate_noise_floor_db(audio)

    issues = []

    # RMS check
    if rms_db < ACX_RMS_MIN_DB:
        issues.append(f"RMS too low: {rms_db:.1f}dB < {ACX_RMS_MIN_DB}dB")
    elif rms_db > ACX_RMS_MAX_DB:
        issues.append(f"RMS too high: {rms_db:.1f}dB > {ACX_RMS_MAX_DB}dB")

    # Peak check
    if peak_db > ACX_TRUE_PEAK_MAX_DB:
        issues.append(f"Peak too high: {peak_db:.1f}dB > {ACX_TRUE_PEAK_MAX_DB}dB")

    # Noise floor check (only if we have enough silence)
    if noise_floor_db > ACX_NOISE_FLOOR_MAX_DB:
        issues.append(f"Noise floor too high: {noise_floor_db:.1f}dB > {ACX_NOISE_FLOOR_MAX_DB}dB")

    is_compliant = len(issues) == 0

    return is_compliant, {
        "is_compliant": is_compliant,
        "rms_db": rms_db,
        "peak_db": peak_db,
        "lufs": lufs,
        "noise_floor_db": noise_floor_db,
        "issues": issues,
        "acx_standards": {
            "rms_range": f"{ACX_RMS_MIN_DB}dB to {ACX_RMS_MAX_DB}dB",
            "max_peak": f"{ACX_TRUE_PEAK_MAX_DB}dB",
            "max_noise_floor": f"{ACX_NOISE_FLOOR_MAX_DB}dB",
        }
    }


def master_audio_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    target_lufs: float = ACX_TARGET_LUFS,
    apply_gate: bool = False
) -> Tuple[bool, Dict[str, Any]]:
    """
    Load, master, and save an audio file.

    Args:
        input_path: Path to input audio file
        output_path: Path for output (default: overwrite input)
        target_lufs: Target loudness
        apply_gate: Whether to apply noise gate

    Returns:
        Tuple of (success, metrics)
    """
    try:
        import soundfile as sf

        # Load audio
        audio, sample_rate = sf.read(str(input_path))

        # Master
        mastered, metrics = master_audio_chunk(
            audio, sample_rate,
            target_lufs=target_lufs,
            apply_gate=apply_gate
        )

        # Validate ACX compliance
        is_compliant, compliance = validate_acx_compliance(mastered, sample_rate)
        metrics["acx_compliance"] = compliance

        # Save
        out_path = output_path or input_path
        sf.write(str(out_path), mastered, sample_rate)

        logger.info(
            f"Mastered {input_path.name}: "
            f"LUFS {metrics['input_lufs']:.1f} → {metrics['output_lufs']:.1f}, "
            f"ACX compliant: {is_compliant}"
        )

        return True, metrics

    except Exception as e:
        logger.error(f"Failed to master audio file {input_path}: {e}")
        return False, {"error": str(e)}
