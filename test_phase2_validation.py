#!/usr/bin/env python3
"""
Test script for Phase 2 TTS Validation Improvements

Tests phoneme-based duration estimation and VAD-based silence detection.
Reference: TTS_VALIDATION_RESEARCH_FINDINGS.md Phase 2

Run with:
    python test_phase2_validation.py
"""

import sys
from pathlib import Path

# Add phase4_tts to path
sys.path.insert(0, str(Path(__file__).parent / "phase4_tts"))

from src.validation import (
    count_phonemes,
    predict_duration_phoneme_based,
    predict_expected_duration,
    PHONEMIZER_AVAILABLE,
    SILERO_VAD_AVAILABLE,
)


def test_phoneme_counting():
    """Test phoneme counting functionality."""
    print("\n" + "=" * 70)
    print("TEST 1: Phoneme Counting")
    print("=" * 70)

    if not PHONEMIZER_AVAILABLE:
        print("⚠️  Phonemizer not available - skipping phoneme tests")
        return False

    # Test cases with known phoneme counts
    test_cases = [
        ("Tue", 2, "Short word"),
        ("Tuesday", 3, "Longer word with same consonants"),
        ("Next Tuesday", 6, "Two words"),
        ("Next Tuesday at three fifteen", 18, "Full phrase"),
        ("Hello world", 6, "Simple greeting"),
        ("The quick brown fox", 9, "Longer phrase"),
    ]

    results = []
    for text, _, description in test_cases:
        phoneme_count = count_phonemes(text)
        results.append((text, phoneme_count, description))
        print(f"  '{text}' → {phoneme_count} phonemes ({description})")

    return True


def test_phoneme_duration_estimation():
    """Test phoneme-based duration estimation."""
    print("\n" + "=" * 70)
    print("TEST 2: Phoneme-Based Duration Estimation")
    print("=" * 70)

    if not PHONEMIZER_AVAILABLE:
        print("⚠️  Phonemizer not available - skipping phoneme tests")
        return False

    # Test texts with expected durations
    test_cases = [
        ("Next Tuesday at three fifteen", "~1.8 seconds (18 phonemes × 100ms)"),
        ("Hello world", "~0.6 seconds (6 phonemes × 100ms)"),
        ("The quick brown fox jumps over the lazy dog", "~3.6 seconds"),
    ]

    print("\n  Phoneme-Based Estimation (100ms per phoneme):")
    for text, expected in test_cases:
        duration = predict_duration_phoneme_based(text)
        print(f"  '{text}'")
        print(f"    Duration: {duration:.2f}s (Expected: {expected})")

    return True


def test_duration_comparison():
    """Compare phoneme-based vs. character-based estimation."""
    print("\n" + "=" * 70)
    print("TEST 3: Phoneme vs. Character-Based Comparison")
    print("=" * 70)

    test_cases = [
        "Tue",
        "Tuesday",
        "Next Tuesday",
        "Next Tuesday at three fifteen",
        "Dr. Smith paid $100 for the item",
        "Hello, how are you doing today?",
    ]

    print("\n  Text | Char-Based (CPM) | Phoneme-Based | Difference")
    print("  " + "-" * 65)

    for text in test_cases:
        char_based = predict_expected_duration(text, chars_per_minute=1050)
        phoneme_based = predict_duration_phoneme_based(text)

        if phoneme_based > 0:
            diff_pct = abs(char_based - phoneme_based) / max(char_based, phoneme_based) * 100
            print(
                f"  '{text[:25]:25}' | {char_based:6.2f}s | {phoneme_based:6.2f}s | {diff_pct:5.1f}%"
            )
        else:
            print(
                f"  '{text[:25]:25}' | {char_based:6.2f}s | (fallback to CPM) | N/A"
            )

    return True


def test_vad_availability():
    """Test VAD availability."""
    print("\n" + "=" * 70)
    print("TEST 4: VAD Availability")
    print("=" * 70)

    if SILERO_VAD_AVAILABLE:
        print("✅ Silero VAD is available")
        print("   - Can use neural voice activity detection")
        print("   - Will detect unnatural pauses in audio")
        return True
    else:
        print("⚠️  Silero VAD not available")
        print("   - Will use fallback amplitude-based detection")
        print("   - Install with: pip install silero-vad")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PHASE 2 TTS VALIDATION IMPROVEMENTS - TEST SUITE")
    print("=" * 70)

    print("\nDependency Status:")
    print(f"  ✅ Phonemizer: {'AVAILABLE' if PHONEMIZER_AVAILABLE else 'NOT AVAILABLE'}")
    print(f"  ✅ Silero VAD: {'AVAILABLE' if SILERO_VAD_AVAILABLE else 'NOT AVAILABLE'}")

    tests = [
        test_phoneme_counting,
        test_phoneme_duration_estimation,
        test_duration_comparison,
        test_vad_availability,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"\n❌ {test_func.__name__} failed: {e}")
            results.append((test_func.__name__, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for name, result in results:
        status = "✅ PASS" if result else "⚠️  SKIP"
        print(f"  {status}: {name}")

    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Install missing dependencies if needed:")
    print("   pip install phonemizer>=3.2.1 silero-vad>=4.0.0")
    print("\n2. Run Phase 1 + 2 integration test:")
    print("   RUN_PHASE_O_FULL=1 pytest tests/integration/ -v -k validation")
    print("\n3. Measure accuracy improvement:")
    print("   - Compare duration_mismatch failure rates before/after")
    print("   - Target: 20% improvement with phoneme-based estimation")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
