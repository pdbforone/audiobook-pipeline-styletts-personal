"""
Phase 5 Clipping Diagnostic Tool
Analyzes Phase 4 and Phase 5 audio to identify clipping source
"""

import librosa
import numpy as np
from pathlib import Path


def analyze_audio_file(filepath):
    """Analyze audio file for clipping and quality metrics"""
    try:
        audio, sr = librosa.load(filepath, sr=None, mono=True)

        # Peak amplitude
        peak = np.max(np.abs(audio))

        # RMS (loudness)
        rms = np.sqrt(np.mean(audio**2))

        # Clipping detection
        clipped_samples = np.sum(np.abs(audio) > 0.99)
        clipping_percentage = (clipped_samples / len(audio)) * 100

        # Dynamic range
        dynamic_range = 20 * np.log10(peak / (rms + 1e-10))

        return {
            "file": Path(filepath).name,
            "sample_rate": sr,
            "duration": len(audio) / sr,
            "peak_amplitude": peak,
            "rms_loudness": rms,
            "clipped_samples": clipped_samples,
            "clipping_pct": clipping_percentage,
            "dynamic_range_db": dynamic_range,
            "is_clipped": peak > 0.95 or clipping_percentage > 0.01,
        }
    except Exception as e:
        return {"file": Path(filepath).name, "error": str(e)}


def main():
    print("=" * 70)
    print("PHASE 5 CLIPPING DIAGNOSTIC")
    print("=" * 70)
    print()

    # Test files
    phase4_file = Path("../phase4_tts/audio_chunks/chunk_441.wav")
    phase5_file = Path("processed/enhanced_0441.wav")

    print("Analyzing Phase 4 output (before enhancement)...")
    if phase4_file.exists():
        p4_results = analyze_audio_file(phase4_file)
        print(f"  File: {p4_results['file']}")
        print(f"  Sample Rate: {p4_results.get('sample_rate', 'N/A')} Hz")
        print(f"  Duration: {p4_results.get('duration', 0):.2f}s")
        print(f"  Peak Amplitude: {p4_results.get('peak_amplitude', 0):.4f}")
        print(f"  RMS Loudness: {p4_results.get('rms_loudness', 0):.4f}")
        print(f"  Clipped Samples: {p4_results.get('clipped_samples', 0)}")
        print(f"  Clipping %: {p4_results.get('clipping_pct', 0):.4f}%")
        print(
            f"  Dynamic Range: {p4_results.get('dynamic_range_db', 0):.1f} dB"
        )
        print(f"  ⚠️  IS CLIPPED: {p4_results.get('is_clipped', False)}")
    else:
        print(f"  ❌ File not found: {phase4_file}")

    print()
    print("Analyzing Phase 5 output (after enhancement)...")
    if phase5_file.exists():
        p5_results = analyze_audio_file(phase5_file)
        print(f"  File: {p5_results['file']}")
        print(f"  Sample Rate: {p5_results.get('sample_rate', 'N/A')} Hz")
        print(f"  Duration: {p5_results.get('duration', 0):.2f}s")
        print(f"  Peak Amplitude: {p5_results.get('peak_amplitude', 0):.4f}")
        print(f"  RMS Loudness: {p5_results.get('rms_loudness', 0):.4f}")
        print(f"  Clipped Samples: {p5_results.get('clipped_samples', 0)}")
        print(f"  Clipping %: {p5_results.get('clipping_pct', 0):.4f}%")
        print(
            f"  Dynamic Range: {p5_results.get('dynamic_range_db', 0):.1f} dB"
        )
        print(f"  ⚠️  IS CLIPPED: {p5_results.get('is_clipped', False)}")
    else:
        print(f"  ❌ File not found: {phase5_file}")

    print()
    print("=" * 70)
    print("DIAGNOSIS:")
    print("=" * 70)

    if phase4_file.exists() and phase5_file.exists():
        p4_clipped = p4_results.get("is_clipped", False)
        p5_clipped = p5_results.get("is_clipped", False)

        if p4_clipped and p5_clipped:
            print("❌ PROBLEM: Phase 4 output is already clipped!")
            print("   → Fix needed in Phase 4 TTS configuration")
            print("   → Phase 5 cannot fix audio that's already clipped")
        elif not p4_clipped and p5_clipped:
            print("❌ PROBLEM: Phase 5 is introducing clipping!")
            print("   → Likely causes:")
            print("     1. Volume normalization too aggressive")
            print("     2. LUFS target too loud")
            print("     3. Noise reduction introducing artifacts")
        elif not p4_clipped and not p5_clipped:
            print("✅ GOOD: No clipping detected in digital signal")
            print("   → If you still hear clipping, it may be:")
            print("     1. Speaker/headphone distortion")
            print("     2. Noise reduction artifacts (not digital clipping)")
            print("     3. Volume normalization changing audio character")
        else:
            print("✅ Phase 5 reduced clipping (good!)")

    print("=" * 70)


if __name__ == "__main__":
    main()
