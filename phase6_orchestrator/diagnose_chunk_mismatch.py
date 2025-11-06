"""
Deep diagnostic: Compare Phase 2 vs Phase 3 chunk by chunk
"""
from pathlib import Path

EXTRACTED_TEXT_PATH = Path("../phase2-extraction/extracted_text/The_Analects_of_Confucius_20240228.txt")
CHUNKS_DIR = Path("../phase3-chunking/chunks")
FILE_ID = "The_Analects_of_Confucius_20240228"

# Read original
with open(EXTRACTED_TEXT_PATH, 'r', encoding='utf-8') as f:
    original = f.read()

# Read first 5 chunks
chunk_files = sorted(CHUNKS_DIR.glob(f"{FILE_ID}_chunk_*.txt"),
                    key=lambda p: int(p.stem.split('_')[-1]))[:5]

print("="*70)
print("SAMPLE COMPARISON: First 5 Chunks")
print("="*70)

print(f"\n📄 Original Text (first 500 chars):")
print(f"{original[:500]}")
print(f"\n{'='*70}")

for i, chunk_file in enumerate(chunk_files, 1):
    with open(chunk_file, 'r', encoding='utf-8') as f:
        chunk_text = f.read()
    
    print(f"\n📝 Chunk {i} ({chunk_file.name}):")
    print(f"   Length: {len(chunk_text)} chars")
    print(f"   Content: {chunk_text[:200]}...")
    print()

# Check if chunk text appears in original
print("="*70)
print("VERIFICATION: Do chunks appear in original?")
print("="*70)

for i, chunk_file in enumerate(chunk_files, 1):
    with open(chunk_file, 'r', encoding='utf-8') as f:
        chunk_text = f.read().strip()
    
    # Check if chunk appears in original
    if chunk_text in original:
        print(f"✅ Chunk {i}: FOUND in original")
    else:
        # Try normalized version
        chunk_norm = ' '.join(chunk_text.lower().split())
        original_norm = ' '.join(original.lower().split())
        
        if chunk_norm in original_norm:
            print(f"⚠️  Chunk {i}: Found (with normalization)")
        else:
            print(f"❌ Chunk {i}: NOT FOUND in original!")
            print(f"   First 100 chars of chunk: {chunk_text[:100]}")

# Check table of contents
print(f"\n{'='*70}")
print("CHECKING FOR TABLE OF CONTENTS")
print("="*70)

toc_indicators = ["Contents", "I.", "II.", "III.", "IV.", "V."]
for indicator in toc_indicators:
    if indicator in original[:2000]:
        print(f"✅ Found '{indicator}' in original (position {original.find(indicator)})")
    else:
        print(f"❌ '{indicator}' not found in original")

# Check if chunks start from TOC or from actual content
print(f"\n{'='*70}")
print("WHERE DO CHUNKS START?")
print("="*70)

with open(chunk_files[0], 'r', encoding='utf-8') as f:
    first_chunk = f.read()

print(f"First chunk starts with: {first_chunk[:100]}")
print(f"\nDoes original start with this? {original[:100] == first_chunk[:100]}")

# Find where first chunk text appears in original
first_50 = first_chunk[:50].strip()
if first_50 in original:
    pos = original.find(first_50)
    print(f"\n✅ First chunk found at position {pos} in original")
    print(f"   Skipped content: {pos} characters")
    print(f"   Skipped text: {original[:pos][:200]}...")
else:
    print(f"\n❌ First chunk text not found in original!")
