"""
Test the enhanced normalize.py with number conversion and inline number removal
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phase2_extraction.normalize import normalize_text, convert_numbers_to_words

def test_number_conversion():
    """Test that numbers are converted to words correctly."""
    print("=" * 60)
    print("Testing Number-to-Word Conversion")
    print("=" * 60)
    
    test_cases = [
        ("Book 1", "Book First"),
        ("Chapter 3", "Chapter Third"),
        ("3 The Master said", "Three The Master said"),
        ("15 Some text here", "Fifteen Some text here"),
    ]
    
    for input_text, expected_contains in test_cases:
        output, count = convert_numbers_to_words(input_text)
        print(f"\nInput:  '{input_text}'")
        print(f"Output: '{output}'")
        print(f"Conversions: {count}")
        
        if expected_contains.lower() in output.lower():
            print("✓ PASS")
        else:
            print(f"✗ FAIL - Expected to contain: '{expected_contains}'")


def test_inline_number_removal():
    """Test that inline page numbers are removed."""
    print("\n" + "=" * 60)
    print("Testing Inline Number Removal")
    print("=" * 60)
    
    test_text = """3 The Master said, "Fine words and an insinuating appearance are seldom associated
with true virtue."

The philosopher Tsang said, "I daily examine myself on three points."

7. Tsze-hsia said, "If a man withdraws his mind from the love of beauty."
"""
    
    normalized, metrics = normalize_text(test_text, "test_inline", Path("extracted_text"))
    
    print("\nOriginal:")
    print(test_text[:200])
    
    print("\nNormalized:")
    print(normalized[:200])
    
    print(f"\nMetrics:")
    print(f"  Removed inline numbers: {metrics.get('removed_inline_numbers', 0)}")
    print(f"  Converted numbers to words: {metrics.get('converted_numbers_to_words', 0)}")
    
    # Check that inline numbers are gone
    lines = normalized.split('\n')
    for line in lines:
        if line.strip() and re.match(r'^\d+\s+[A-Z]', line.strip()):
            print(f"✗ FAIL - Found unconverted inline number: {line[:50]}")
            return
    
    print("✓ PASS - All inline numbers removed or converted")


def test_full_analects_sample():
    """Test with a sample from The Analects."""
    print("\n" + "=" * 60)
    print("Testing Full Analects Sample")
    print("=" * 60)
    
    sample_text = """3 The Master said, "Fine words and an insinuating appearance are seldom associated
with true virtue. "

The philosopher Tsang said, "I daily examine myself on three points: -whether, in
transacting business for others, I may have been not faithful; -whether, in intercourse
with friends, I may have been not sincere; -whether I may have not mastered and
practiced the instructions of my teacher. "

7. Tsze-hsia said, "If a man withdraws his mind from the love of beauty, and applies it
as sincerely to the love of the virtuous; if, in serving his parents, he can exert his utmost
strength; if, in serving his prince, he can devote his life; if, in his intercourse with his
friends, his words are sincere: -although men say that he has not learned, I will certainly
say that he has.
"""
    
    normalized, metrics = normalize_text(sample_text, "test_analects", Path("extracted_text"))
    
    print("\nChanges applied:")
    for change in metrics.get('changes', []):
        print(f"  - {change}")
    
    print("\nFirst 300 chars of normalized text:")
    print(normalized[:300])
    
    # Check for number-to-word conversion
    if "Three The Master" in normalized or "three The Master" in normalized.lower():
        print("\n✓ PASS - Found number-to-word conversion")
    else:
        print("\n✗ Check output - number conversion may not have worked as expected")
    
    # Check inline number removal
    if metrics.get('removed_inline_numbers', 0) > 0:
        print(f"✓ PASS - Removed {metrics['removed_inline_numbers']} inline numbers")
    else:
        print("✗ Check - Expected some inline numbers to be removed")


if __name__ == "__main__":
    import re
    
    try:
        test_number_conversion()
        test_inline_number_removal()
        test_full_analects_sample()
        
        print("\n" + "=" * 60)
        print("TESTING COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
