"""Full test using the actual Gift of the Magi text file."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from phase2_extraction.cleaner import clean_for_tts

# Load the actual text file
input_file = Path(__file__).parent / "Gift of the Magi.txt"

if not input_file.exists():
    print(f"ERROR: {input_file} not found!")
    print(f"Looking in: {input_file.parent}")
    print(f"Files available: {list(input_file.parent.glob('*.txt'))}")
    sys.exit(1)

print(f"Loading: {input_file}")
raw_text = input_file.read_text(encoding="utf-8")

print("\n=== ORIGINAL TEXT (first 500 chars) ===")
print(raw_text[:500])
print("...\n")

# Clean it
cleaned_text = clean_for_tts(raw_text)

print("=== CLEANED TEXT (first 500 chars) ===")
print(cleaned_text[:500])
print("...\n")

# Statistics
print("=== STATISTICS ===")
print(f"Original: {len(raw_text):,} characters")
print(f"Cleaned:  {len(cleaned_text):,} characters")
print(f"Reduction: {100 * (1 - len(cleaned_text)/len(raw_text)):.1f}%")

# Count specific fixes
import re

currency_original = len(re.findall(r"\$\s*\d+\.\d{2}", raw_text))
single_chars = len(re.findall(r"^\s*[a-zA-Z]\s*$", raw_text, re.MULTILINE))
print("\nFixed:")
print(f"  - Currency patterns: {currency_original}")
print(f"  - Single-char lines: {single_chars}")

# Save output
output_file = Path(__file__).parent / "Gift_of_Magi_CLEANED.txt"
output_file.write_text(cleaned_text, encoding="utf-8")
print(f"\n✓ Saved cleaned text to: {output_file.absolute()}")

# Show a sample comparison of a problematic section
print("\n=== SAMPLE COMPARISON: Title Section ===")
title_section_raw = raw_text[:100]
title_section_clean = cleaned_text[:100]
print(f"BEFORE: {repr(title_section_raw)}")
print(f"AFTER:  {repr(title_section_clean)}")
