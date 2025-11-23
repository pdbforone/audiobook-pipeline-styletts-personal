"""
Detailed character-level diff between Phase 2 and Phase 3
Shows exactly what's different
"""

from pathlib import Path
import difflib


def normalize_aggressive(text):
    """Aggressive normalization for comparison"""
    # Convert to lowercase
    text = text.lower()
    # Replace all whitespace with single space
    text = " ".join(text.split())
    return text


# Read Phase 2 text
phase2_path = Path(
    "../phase2-extraction/extracted_text/The_Analects_of_Confucius_20240228.txt"
)
with open(phase2_path, "r", encoding="utf-8") as f:
    phase2_text = f.read()

# Read all Phase 3 chunks
chunks_dir = Path("../phase3-chunking/chunks")
chunk_files = sorted(
    chunks_dir.glob("The_Analects_of_Confucius_20240228_chunk_*.txt")
)

phase3_text = ""
for chunk_file in chunk_files:
    with open(chunk_file, "r", encoding="utf-8") as f:
        phase3_text += f.read() + " "

# Normalize both
p2_norm = normalize_aggressive(phase2_text)
p3_norm = normalize_aggressive(phase3_text)

print("=" * 70)
print("DETAILED CHARACTER-LEVEL COMPARISON")
print("=" * 70)
print(f"Phase 2 (normalized): {len(p2_norm):,} chars")
print(f"Phase 3 (normalized): {len(p3_norm):,} chars")
print(f"Difference: {abs(len(p2_norm) - len(p3_norm)):,} chars")
print()

# Check if they're identical after aggressive normalization
if p2_norm == p3_norm:
    print("✅ PERFECT MATCH after aggressive normalization!")
    print("   The difference is just whitespace/formatting")
else:
    print("❌ Still differences after normalization")
    print()

    # Find first difference
    for i, (c1, c2) in enumerate(zip(p2_norm, p3_norm)):
        if c1 != c2:
            print(f"First difference at position {i}:")
            print(f"  Phase 2: '{p2_norm[max(0,i-50):i+50]}'")
            print(f"  Phase 3: '{p3_norm[max(0,i-50):i+50]}'")
            break

    # Use difflib to find all differences
    print("\n" + "=" * 70)
    print("DETAILED DIFF (first 10 differences)")
    print("=" * 70)

    differ = difflib.Differ()
    diff = list(differ.compare(p2_norm.split(), p3_norm.split()))

    differences = [
        (i, line)
        for i, line in enumerate(diff)
        if line.startswith("- ") or line.startswith("+ ")
    ]

    for i, (idx, line) in enumerate(differences[:20]):
        if i % 2 == 0:
            print()
        print(f"{line}")

        if i >= 19:
            print(f"\n... and {len(differences) - 20} more differences")
            break

print("\n" + "=" * 70)
