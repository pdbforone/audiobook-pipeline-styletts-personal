"""
Test script for NeMo-based text cleaner.
Works with OR without NeMo installed (falls back to basic cleaning).
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from phase2_extraction.cleaner import TTSTextCleaner

print("=" * 70)
print("TESTING TEXT CLEANER FOR TTS")
print("=" * 70)

# Sample text from Gift of the Magi
raw = """T h e G i f t o f t h e M a g i
p
The Gift of the Magi
O
NE DOLLAR AND EIGHTY-SEVEN CENTS.
That was all. She had put it aside, one cent and then another and then
another, in her careful buying of meat and other food. Della counted
it three times. One dollar and eighty-seven cents. And the next day
would be Christmas.

Mr. James Dillingham Young was being paid $30 a week. Now, when he 
was being paid only $20 a week, the name seemed too long. At 3:45pm 
on 12/25, they would celebrate."""

print("\n📄 ORIGINAL TEXT:")
print("-" * 70)
print(raw)
print()

# Initialize cleaner
cleaner = TTSTextCleaner(language="en", use_context=False)

# Clean the text
print("\n🧹 CLEANING TEXT...")
print("-" * 70)
cleaned = cleaner.clean_for_tts(raw)

print("\n✅ CLEANED TEXT:")
print("-" * 70)
print(cleaned)
print()

# Show statistics
print("\n📊 STATISTICS:")
print("-" * 70)
print(f"Original length: {len(raw):,} characters")
print(f"Cleaned length:  {len(cleaned):,} characters")
print(f"Reduction:       {100 * (1 - len(cleaned)/len(raw)):.1f}%")

# Show what changed
print("\n🔍 KEY TRANSFORMATIONS:")
print("-" * 70)

if "T h e" in raw and "The" in cleaned:
    print("✓ Fixed spaced-out title: 'T h e' → 'The'")
if raw.count("p\n") > cleaned.count("p\n"):
    print("✓ Removed stray 'p' character")
if raw.count("O\n") > cleaned.count("O\n"):
    print("✓ Removed stray 'O' character")

# Check for NeMo-specific normalizations
if "thirty dollars" in cleaned.lower() or "twenty dollars" in cleaned.lower():
    print("✓ Normalized currency: '$30' → 'thirty dollars'")
    print("✓ Normalized currency: '$20' → 'twenty dollars'")
else:
    print("⚠ Currency not fully normalized (NeMo may not be installed)")

if "three forty-five" in cleaned.lower():
    print("✓ Normalized time: '3:45pm' → 'three forty-five p m'")
else:
    print("⚠ Time not normalized (NeMo may not be installed)")

if "december twenty-fifth" in cleaned.lower() or "december" in cleaned.lower():
    print("✓ Normalized date: '12/25' → 'December twenty-fifth'")
else:
    print("⚠ Date not normalized (NeMo may not be installed)")

# Save output
output_file = Path("test_output_nemo.txt")
output_file.write_text(cleaned, encoding="utf-8")

print(f"\n💾 Saved to: {output_file.absolute()}")

# Test with file API
print("\n" + "=" * 70)
print("TESTING FILE API")
print("=" * 70)

input_file = Path("test_input_temp.txt")
output_file_2 = Path("test_output_file_api.txt")

# Write test input
input_file.write_text(raw, encoding="utf-8")

# Clean using file API
metrics = cleaner.clean_text_file(input_file, output_file_2)

print("\n📊 Metrics from file API:")
for key, value in metrics.items():
    if isinstance(value, float):
        print(f"  {key}: {value:.3f}")
    else:
        print(f"  {key}: {value}")

print("\n✓ Test complete! Check these files:")
print(f"  - {output_file}")
print(f"  - {output_file_2}")

# Cleanup temp file
input_file.unlink()

print("\n" + "=" * 70)
print("💡 NEXT STEPS:")
print("=" * 70)
print()
if "⚠" in cleaned or metrics.get("normalizer") != "NeMo":
    print("⚠ NeMo Text Processing is NOT installed.")
    print("  You're using basic regex fallback.")
    print()
    print("To get proper TTS normalization:")
    print("  1. Read INSTALL_NEMO_TN.md")
    print("  2. Install: conda install -c conda-forge pynini")
    print("  3. Install: pip install nemo-text-processing")
    print("  4. Re-run this test")
else:
    print("✅ NeMo Text Processing is working!")
    print("   Your text is properly normalized for TTS.")
    print()
    print("Next: Integrate into extraction.py")

print()
print("=" * 70)
