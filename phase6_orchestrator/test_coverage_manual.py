"""
Manual coverage test with corrected paths
Run this to verify Phase 2→3 text coverage with the ACTUAL file locations
"""
import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_coverage import normalize_text, calculate_text_similarity

# CORRECTED PATHS (found via file search)
EXTRACTED_TEXT_PATH = Path("../phase2-extraction/extracted_text/The_Analects_of_Confucius_20240228.txt")
CHUNKS_DIR = Path("../phase3-chunking/chunks")
FILE_ID = "The_Analects_of_Confucius_20240228"

print("="*70)
print("MANUAL COVERAGE TEST - Phase 2→3")
print("="*70)
print(f"\nUsing CORRECTED paths:")
print(f"  Phase 2: {EXTRACTED_TEXT_PATH}")
print(f"  Phase 3: {CHUNKS_DIR}")

# Read Phase 2 extracted text
if not EXTRACTED_TEXT_PATH.exists():
    print(f"\n❌ ERROR: Phase 2 file not found: {EXTRACTED_TEXT_PATH}")
    sys.exit(1)

with open(EXTRACTED_TEXT_PATH, 'r', encoding='utf-8') as f:
    original_text = f.read()

print(f"\n📄 Phase 2 extracted text:")
print(f"  Length: {len(original_text):,} characters")
print(f"  First 100 chars: {original_text[:100]}...")

# Find all chunk files
chunk_files = sorted(CHUNKS_DIR.glob(f"{FILE_ID}_chunk_*.txt"),
                    key=lambda p: int(p.stem.split('_')[-1]))

print(f"\n📚 Phase 3 chunks:")
print(f"  Found: {len(chunk_files)} chunk files")

if len(chunk_files) == 0:
    print(f"❌ ERROR: No chunks found in {CHUNKS_DIR}")
    sys.exit(1)

# Read and concatenate chunks
chunk_texts = []
for chunk_file in chunk_files:
    try:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            chunk_texts.append(f.read())
    except Exception as e:
        print(f"⚠️  Warning: Could not read {chunk_file.name}: {e}")
        chunk_texts.append("")

concatenated_text = ''.join(chunk_texts)

print(f"  Total concatenated length: {len(concatenated_text):,} characters")

# Normalize and compare
original_norm = normalize_text(original_text)
concat_norm = normalize_text(concatenated_text)

similarity = calculate_text_similarity(original_norm, concat_norm)

print(f"\n🔍 Comparison:")
print(f"  Original (normalized): {len(original_norm):,} chars")
print(f"  Concatenated (normalized): {len(concat_norm):,} chars")
print(f"  Similarity: {similarity:.6f} ({similarity*100:.4f}%)")

# Results
print(f"\n{'='*70}")
if original_norm == concat_norm:
    print("✅ EXACT MATCH - All text preserved in chunks!")
    print("="*70)
    sys.exit(0)
elif similarity > 0.99:
    print(f"⚠️  NEAR MATCH - {similarity*100:.4f}% similar")
    print("   (Likely just whitespace differences)")
    print("="*70)
    sys.exit(0)
else:
    print(f"❌ MISMATCH - Only {similarity*100:.4f}% similar")
    print(f"   Difference: {abs(len(original_norm) - len(concat_norm)):,} characters")
    
    # Show sample difference
    if len(original_norm) > len(concat_norm):
        print(f"\n   Missing text (first 200 chars):")
        # Find first difference
        for i, (o, c) in enumerate(zip(original_norm, concat_norm)):
            if o != c:
                print(f"   Position {i}: '{original_norm[i:i+200]}'")
                break
    else:
        print(f"\n   Extra text (first 200 chars):")
        for i, (o, c) in enumerate(zip(original_norm, concat_norm)):
            if o != c:
                print(f"   Position {i}: '{concat_norm[i:i+200]}'")
                break
    
    print("="*70)
    sys.exit(1)
