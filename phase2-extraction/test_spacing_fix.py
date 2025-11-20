"""
Test the character spacing fix for Phase 2 extraction.

Validates that "T h e G i f t o f t h e M a g i" becomes "TheGiftoftheMagi"
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from phase2_extraction.cleaner import TTSTextCleaner


def test_character_spacing_fix():
    """Test that spaced characters are correctly fixed."""
    cleaner = TTSTextCleaner()

    # Test case from Gift of the Magi issue
    test_cases = [
        # (input, expected)
        ("T h e G i f t o f t h e M a g i", "TheGiftoftheMagi"),
        ("O. H e n r y", "O. Henry"),  # Period breaks word boundary - keeps space (correct)
        ("T h e", "The"),
        ("A B C D E F", "ABCDEF"),
        # Normal text should not be affected
        ("The quick brown fox", "The quick brown fox"),
        ("ONE DOLLAR AND EIGHTY-SEVEN CENTS", "ONE DOLLAR AND EIGHTY-SEVEN CENTS"),
    ]

    print("=" * 70)
    print("CHARACTER SPACING FIX TEST")
    print("=" * 70)

    all_passed = True
    for input_text, expected in test_cases:
        result = cleaner._normalize_whitespace(input_text)
        passed = result == expected

        status = "[OK]" if passed else "[FAIL]"
        print(f"\n{status} Test:")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")

        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("[OK] All tests passed!")
        return 0
    else:
        print("[FAIL] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(test_character_spacing_fix())
