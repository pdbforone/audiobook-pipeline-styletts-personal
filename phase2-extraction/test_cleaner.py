from pathlib import Path
from phase2_extraction.cleaner import clean_for_tts

# Your sample text
raw = """T h e G i f t o f t h e M a g i
p
The Gift of the Magi
O
NE DOLLAR AND EIGHTY-SEVEN CENTS.
That was all. She had put it aside, one cent and then another and then
another, in her careful buying of meat and other food. Della counted
it three times. One dollar and eighty-seven cents."""

cleaned = clean_for_tts(raw)
print("=== CLEANED OUTPUT ===")
print(cleaned)
print("\n=== LENGTH ===")
print(f"Original: {len(raw)} chars")
print(f"Cleaned: {len(cleaned)} chars")

# Save to file to inspect
Path("test_output.txt").write_text(cleaned)
print("\nSaved to test_output.txt")