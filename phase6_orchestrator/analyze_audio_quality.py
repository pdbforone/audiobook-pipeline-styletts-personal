#!/usr/bin/env python3
"""
AUDIO QUALITY DIAGNOSTIC
Compare actual audio files: test (good) vs orchestrator (garbage)
"""

import librosa
import numpy as np
from pathlib import Path

print("=" * 80)
print("AUDIO DIAGNOSTIC: Test vs Orchestrator Audio Analysis")
print("=" * 80)

# Find the audio files
test_audio = Path(
    "../phase4_tts/audio_chunks/chunk_0.wav"
)  # From test_simple_text.py
real_audio_1 = Path(
    "../phase4_tts/audio_chunks/chunk_1.wav"
)  # From orchestrator
real_audio_10 = Path("../phase4_tts/audio_chunks/chunk_10.wav")


def analyze_audio(audio_path, label):
    """Deep analysis of audio file"""
    if not audio_path.exists():
        print(f"\n❌ {label}: FILE NOT FOUND - {audio_path}")
        return None

    print(f"\n{'='*80}")
    print(f"{label}: {audio_path.name}")
    print(f"{'='*80}")

    try:
        # Load audio
        y, sr = librosa.load(audio_path, sr=None)

        print("\n📊 BASIC INFO:")
        print(f"  Sample rate: {sr} Hz")
        print(f"  Duration: {len(y)/sr:.2f} seconds")
        print(f"  Total samples: {len(y)}")
        print(f"  Shape: {y.shape}")
        print(f"  Data type: {y.dtype}")

        # Audio quality metrics
        rms = librosa.feature.rms(y=y)[0]
        zcr = librosa.feature.zero_crossing_rate(y)[0]

        print("\n📈 QUALITY METRICS:")
        print(f"  RMS energy: {rms.mean():.6f} (avg)")
        print(f"  Zero crossing rate: {zcr.mean():.6f}")
        print(f"  Dynamic range: {y.max() - y.min():.6f}")
        print(f"  Peak amplitude: {abs(y).max():.6f}")

        # Check for silence
        is_silent = rms.mean() < 0.01
        print(f"  Silent: {'YES ❌' if is_silent else 'NO ✅'}")

        # Check for clipping
        is_clipped = abs(y).max() > 0.99
        print(f"  Clipped: {'YES ❌' if is_clipped else 'NO ✅'}")

        # Spectral analysis
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        print("\n🎵 SPECTRAL ANALYSIS:")
        print(f"  Spectral centroid: {spectral_centroids.mean():.1f} Hz (avg)")
        print(
            f"  Spectral centroid range: {spectral_centroids.min():.1f} - {spectral_centroids.max():.1f} Hz"
        )

        # Tempo/rhythm
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        print(f"  Detected tempo: {tempo:.1f} BPM")

        # Energy distribution (check for reversal)
        # Split into 10 segments and compare energy
        segments = np.array_split(y, 10)
        segment_energies = [
            librosa.feature.rms(y=seg)[0].mean() for seg in segments
        ]

        print("\n⚡ ENERGY DISTRIBUTION (10 segments):")
        print(f"  First segment: {segment_energies[0]:.6f}")
        print(f"  Middle segment: {segment_energies[5]:.6f}")
        print(f"  Last segment: {segment_energies[-1]:.6f}")

        # Check for reversal (energy should typically decay at end)
        first_half_energy = np.mean(segment_energies[:5])
        second_half_energy = np.mean(segment_energies[5:])
        energy_ratio = first_half_energy / (second_half_energy + 1e-10)

        print(f"  First half avg: {first_half_energy:.6f}")
        print(f"  Second half avg: {second_half_energy:.6f}")
        print(f"  Energy ratio: {energy_ratio:.3f}")

        if energy_ratio < 0.5:
            print("  ⚠️  POSSIBLY REVERSED (energy increases toward end)")
        elif energy_ratio > 2.0:
            print("  ⚠️  UNUSUAL ENERGY PATTERN (too much front-loading)")
        else:
            print("  ✅ Normal energy distribution")

        # Check for repetitive patterns (gibberish indicator)
        # Autocorrelation to detect loops
        autocorr = np.correlate(y, y, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]

        # Find peaks in autocorrelation (excluding first peak at lag 0)
        from scipy.signal import find_peaks

        peaks, _ = find_peaks(
            autocorr[sr // 10 :], height=autocorr.max() * 0.3
        )

        print("\n🔁 REPETITION ANALYSIS:")
        if len(peaks) > 0:
            # Convert peak positions to time
            peak_times = [(p + sr // 10) / sr for p in peaks[:3]]
            print(f"  Found {len(peaks)} repetitive patterns")
            print(f"  Pattern periods: {[f'{t:.2f}s' for t in peak_times]}")
            if len(peaks) > 5:
                print("  ⚠️  EXCESSIVE REPETITION - possible TTS loop")
        else:
            print("  No significant repetition detected ✅")

        # Mel spectrogram for visual inspection
        mel_spec = librosa.feature.melspectrogram(y=y, sr=sr)
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

        print("\n🎨 SPECTROGRAM:")
        print(f"  Frequency bins: {mel_spec_db.shape[0]}")
        print(f"  Time frames: {mel_spec_db.shape[1]}")
        print(f"  Spectral density: {mel_spec_db.mean():.2f} dB")

        return {
            "duration": len(y) / sr,
            "rms": rms.mean(),
            "zcr": zcr.mean(),
            "spectral_centroid": spectral_centroids.mean(),
            "energy_ratio": energy_ratio,
            "peak_amplitude": abs(y).max(),
            "repetition_count": len(peaks),
            "is_silent": is_silent,
            "possibly_reversed": energy_ratio < 0.5,
        }

    except Exception as e:
        print(f"\n❌ ERROR analyzing audio: {e}")
        import traceback

        traceback.print_exc()
        return None


# Analyze all files
test_metrics = analyze_audio(test_audio, "TEST AUDIO (GOOD)")
real1_metrics = analyze_audio(
    real_audio_1, "ORCHESTRATOR AUDIO - CHUNK 1 (GARBAGE)"
)
real10_metrics = analyze_audio(
    real_audio_10, "ORCHESTRATOR AUDIO - CHUNK 10 (GARBAGE?)"
)

# Comparison
if test_metrics and real1_metrics:
    print("\n" + "=" * 80)
    print("COMPARISON: Test vs Orchestrator")
    print("=" * 80)

    print("\nDuration:")
    print(f"  Test: {test_metrics['duration']:.2f}s")
    print(f"  Chunk 1: {real1_metrics['duration']:.2f}s")
    print(
        f"  Difference: {abs(test_metrics['duration'] - real1_metrics['duration']):.2f}s"
    )

    print("\nRMS Energy:")
    print(f"  Test: {test_metrics['rms']:.6f}")
    print(f"  Chunk 1: {real1_metrics['rms']:.6f}")
    print(
        f"  Ratio: {real1_metrics['rms'] / (test_metrics['rms'] + 1e-10):.2f}x"
    )

    print("\nSpectral Centroid (voice quality indicator):")
    print(f"  Test: {test_metrics['spectral_centroid']:.1f} Hz")
    print(f"  Chunk 1: {real1_metrics['spectral_centroid']:.1f} Hz")
    print(
        f"  Difference: {abs(test_metrics['spectral_centroid'] - real1_metrics['spectral_centroid']):.1f} Hz"
    )

    print("\nRepetition:")
    print(f"  Test: {test_metrics['repetition_count']} patterns")
    print(f"  Chunk 1: {real1_metrics['repetition_count']} patterns")

    print("\nReversal indicators:")
    print(f"  Test reversed: {test_metrics['possibly_reversed']}")
    print(f"  Chunk 1 reversed: {real1_metrics['possibly_reversed']}")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

print(
    """
If chunk 1 shows:
  - Similar duration but sounds different → Parameter/model state issue
  - Much shorter duration → Text truncation or early stopping
  - Higher repetition count → TTS loop (text or parameter issue)
  - Reversed energy pattern → Audio being flipped somewhere
  - Very different spectral centroid → Wrong voice/language model
  - Silent or very low RMS → Generation failure

Run this script to see what's actually different between the good and bad audio.
"""
)

print("\nNext step: Listen to both files and describe EXACTLY what you hear:")
print(f"  1. {test_audio}")
print(f"  2. {real_audio_1}")
print("\nDescribe:")
print("  - Is it reversed?")
print("  - Is it repeating words?")
print("  - Is it a different voice?")
print("  - Is it a different language?")
print("  - Is it gibberish phonemes?")
print("  - Is it silent/corrupted?")
