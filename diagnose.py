#!/usr/bin/env python
"""Quick diagnostic to identify Meditations vs Gift of Magi mismatch."""

import json
from pathlib import Path

print("=" * 70)
print("PIPELINE MISMATCH DIAGNOSTIC")
print("=" * 70)

# Load pipeline.json
with open("pipeline.json") as f:
    data = json.load(f)

print("\n[1] TOP-LEVEL INFO:")
print(f"  Input file: {data.get('input_file', 'NOT SET')}")
print(f"  File ID: {data.get('file_id', 'NOT SET')}")

print("\n[2] PHASE 2 (Text Extraction):")
phase2_files = data.get("phase2", {}).get("files", {})
for fid, info in phase2_files.items():
    print(f"  File ID: {fid}")
    print(f"    Title: {info.get('metadata', {}).get('title', 'NO TITLE')}")
    print(f"    Path: {info.get('path')}")
    print(f"    Words: {info.get('word_count')}")

print("\n[3] PHASE 3 (Chunking):")
phase3 = data.get("phase3", {})
print(f"  Status: {phase3.get('status')}")
phase3_files = phase3.get("files", {})
print(f"  Total chunks in pipeline.json: {len(phase3_files)}")

if phase3_files:
    # Get first and last chunk IDs
    chunk_ids = list(phase3_files.keys())
    print(f"  First chunk ID: {chunk_ids[0]}")
    print(f"  Last chunk ID: {chunk_ids[-1]}")

    # Check base file_id
    base_id = chunk_ids[0].rsplit("_c", 1)[0]
    print(f"  Base file_id from chunks: {base_id}")

print("\n[4] ACTUAL CHUNK FILES:")
chunks_dir = Path("artifacts/chunks")
if chunks_dir.exists():
    txt_files = sorted(chunks_dir.glob("*.txt"))
    print(f"  Total .txt files in artifacts/chunks/: {len(txt_files)}")

    if txt_files:
        # Show first few
        print("  First 3 files:")
        for f in txt_files[:3]:
            print(f"    - {f.name}")

        # Read first chunk to see content
        with open(txt_files[0], "r", encoding="utf-8") as f:
            sample = f.read(150)
        print("\n  FIRST CHUNK PREVIEW (150 chars):")
        print(f"  '{sample}...'")
        print()

        # Check if "Gift of the Magi" or "Meditations" appears
        if any("magi" in f.name.lower() for f in txt_files[:5]):
            print("  ⚠️  Found 'magi' in chunk filenames - OLD CHUNKS PRESENT!")
        if "meditations" in sample.lower():
            print("  ✅ First chunk contains 'meditations' - correct book")
        elif "christmas" in sample.lower() or "della" in sample.lower():
            print(
                "  ❌ First chunk appears to be Gift of the Magi - WRONG BOOK!"
            )
else:
    print("  ⚠️  artifacts/chunks/ doesn't exist!")

print("\n[5] PHASE 4 (TTS):")
phase4 = data.get("phase4", {})
print(f"  Status: {phase4.get('status')}")
phase4_files = phase4.get("files", {})
print(f"  Audio files generated: {len(phase4_files)}")

if phase4_files:
    audio_ids = list(phase4_files.keys())[:3]
    print("  First 3 audio file IDs:")
    for aid in audio_ids:
        print(f"    - {aid}")

print("\n" + "=" * 70)
print("DIAGNOSIS:")
print("=" * 70)

# Compare file IDs
p2_ids = list(phase2_files.keys())
p3_base = (
    list(phase3_files.keys())[0].rsplit("_c", 1)[0] if phase3_files else None
)

if p2_ids and p3_base:
    if p2_ids[0] != p3_base:
        print("❌ FILE ID MISMATCH DETECTED!")
        print(f"   Phase 2: {p2_ids[0]}")
        print(f"   Phase 3: {p3_base}")
        print("\n   → Phase 3 processed WRONG input!")
        print("   → Re-run Phase 3 with correct --file-id")
    else:
        print("✅ File IDs match between Phase 2 and Phase 3")

print("\n" + "=" * 70)
