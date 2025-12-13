#!/usr/bin/env python3
"""
Test XTTS Sentence Splitting

Quick validation that long sentences from Plutarch are split correctly
at clause boundaries to prevent XTTS 250-character warnings.

This is a standalone test - run it with the Phase 3 environment:
    cd phase3-chunking
    .venv\Scripts\python ..\test_sentence_splitting.py
"""

import sys
from pathlib import Path

# Test sentences from Plutarch's Life of Alexander
test_sentences = [
    # 287 chars - should be split
    "We are told that Philip and Olympias first met during their initiation into the sacred mysteries at Samothrace, and that he, while yet a boy, fell in love with the orphan girl, and persuaded her brother Arymbas to consent to their marriage.",

    # 327 chars - should be split
    "Alexander was born on the sixth day of the month Hekatombæon, which the Macedonians call Lous, the same day on which the temple of Artemis at Ephesus was burned, which coincidence inspired Hegesias of Magnesia to construct a ponderous joke, dull enough to have put out the fire.",

    # 190 chars - should NOT be split
    "His personal appearance is best shown by the statues of Lysippus, the only artist whom he allowed to represent him in whose works we can trace his characteristics.",

    # 420 chars - should be split multiple times
    "When Philoneikus the Thessalian brought the horse Boukephalus and offered it to Philip for the sum of thirteen talents, the king and his friends proceeded to some level ground to try the horse's paces, and they found that he was very savage and unmanageable, for he allowed no one to mount him, and paid no attention to any man's voice, but refused to allow any one to approach him.",
]


def main():
    """Run test with Phase 3 environment."""
    print("\n" + "=" * 70)
    print("XTTS Sentence Splitting Test Suite")
    print("=" * 70)
    print("\nThis test requires the Phase 3 environment.")
    print("\nUsage:")
    print("  cd phase3-chunking")
    print("  .venv\\Scripts\\python ..\\test_sentence_splitting.py")
    print("\n" + "=" * 70)

    # Try to import Phase 3 utils
    try:
        # Add phase3 to path if not already there
        phase3_src = Path(__file__).parent / "phase3-chunking" / "src"
        if str(phase3_src) not in sys.path:
            sys.path.insert(0, str(phase3_src))

        from phase3_chunking.utils import split_long_sentences_for_xtts, split_at_clause_boundaries

        print("\n✓ Phase 3 imports successful!")
        print("\nRunning sentence splitting tests...\n")

        # Run tests
        success = run_tests(split_long_sentences_for_xtts, split_at_clause_boundaries)

        print("\n" + "=" * 70)
        if success:
            print("✅ ALL TESTS PASSED")
            print("=" * 70)
            print("\nSentence splitting is working correctly!")
            print("XTTS warnings should be eliminated for Plutarch texts.")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            print("=" * 70)
            print("\nSome sentences still exceed 250 chars.")
            print("Review split_at_clause_boundaries() logic.")
            return 1

    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        print("\nPlease run this script with the Phase 3 virtual environment:")
        print("  cd phase3-chunking")
        print("  .venv\\Scripts\\python ..\\test_sentence_splitting.py")
        return 1


def run_tests(split_long_sentences_for_xtts, split_at_clause_boundaries):
    """Run the actual tests."""

    # Test 1: Single sentence splitting
    print("=" * 70)
    print("TEST 1: Single Sentence Splitting")
    print("=" * 70)

    for i, sent in enumerate(test_sentences, 1):
        print(f"\n--- Sentence {i} ({len(sent)} chars) ---")
        print(f"Original: {sent[:100]}...")

        segments = split_at_clause_boundaries(sent, max_chars=250)

        print(f"\nResult: {len(segments)} segment(s)")
        for j, seg in enumerate(segments, 1):
            print(f"  [{j}] ({len(seg)} chars): {seg[:80]}...")

        # Verify all segments <= 250 chars
        all_valid = all(len(seg) <= 250 for seg in segments)
        if all_valid:
            print(f"✓ All segments ≤ 250 chars")
        else:
            print(f"❌ Some segments > 250 chars!")
            for j, seg in enumerate(segments, 1):
                if len(seg) > 250:
                    print(f"    Segment {j}: {len(seg)} chars")

    # Test 2: Batch splitting
    print("\n" + "=" * 70)
    print("TEST 2: Batch Sentence Splitting")
    print("=" * 70)

    print(f"\nInput: {len(test_sentences)} sentences")
    result = split_long_sentences_for_xtts(
        test_sentences,
        max_sentence_chars=250,
        enable_splitting=True,
    )

    print(f"Output: {len(result)} sentences")
    print(f"Split {len(result) - len(test_sentences)} long sentences\n")

    # Check distribution
    lengths = [len(s) for s in result]
    over_limit = [s for s in result if len(s) > 250]

    print(f"Statistics:")
    print(f"  Min length: {min(lengths)} chars")
    print(f"  Max length: {max(lengths)} chars")
    print(f"  Avg length: {sum(lengths) / len(lengths):.1f} chars")
    print(f"  Over 250 chars: {len(over_limit)} / {len(result)}")

    if over_limit:
        print(f"\n❌ WARNING: {len(over_limit)} sentences still exceed 250 chars:")
        for s in over_limit:
            print(f"  - {len(s)} chars: {s[:100]}...")
        return False
    else:
        print(f"\n✓ All sentences ≤ 250 chars!")

    # Test 3: Example output
    print("\n" + "=" * 70)
    print("EXAMPLE: Plutarch Sentence Splitting")
    print("=" * 70)

    example = test_sentences[0]  # The Philip and Olympias sentence

    print(f"\nOriginal ({len(example)} chars):")
    print(f'  "{example}"')

    segments = split_at_clause_boundaries(example, max_chars=250)

    print(f"\nSplit into {len(segments)} parts:")
    for i, seg in enumerate(segments, 1):
        print(f'  [{i}] ({len(seg)} chars): "{seg}"')

    print(f"\n✓ Maximum segment length: {max(len(s) for s in segments)} chars")

    return True


if __name__ == "__main__":
    sys.exit(main())
