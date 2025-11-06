"""Working test script - adds src to path for import."""
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Now import should work
from phase2_extraction.cleaner import clean_for_tts

# Your sample text
raw = """T h e G i f t o f t h e M a g i
p
The Gift of the Magi
O
NE DOLLAR AND EIGHTY-SEVEN CENTS.
That was all. She had put it aside, one cent and then another and then
another, in her careful buying of meat and other food. Della counted
it three times. One dollar and eighty-seven cents. And the next day
would be Christmas."""

print("=== ORIGINAL TEXT ===")
print(raw)
print("\n" + "="*60 + "\n")

cleaned = clean_for_tts(raw)

print("=== CLEANED OUTPUT ===")
print(cleaned)
print("\n" + "="*60 + "\n")

print("=== STATISTICS ===")
print(f"Original: {len(raw)} characters")
print(f"Cleaned:  {len(cleaned)} characters")
print(f"Reduction: {100 * (1 - len(cleaned)/len(raw)):.1f}%")

# Count specific fixes
import re
currency_matches = len(re.findall(r'\$\s*\d+\.\d{2}', raw))
print(f"Currency normalizations: {currency_matches}")

# Save to file to inspect
output_path = Path("test_output.txt")
output_path.write_text(cleaned, encoding='utf-8')
print(f"\n✓ Saved to {output_path.absolute()}")
