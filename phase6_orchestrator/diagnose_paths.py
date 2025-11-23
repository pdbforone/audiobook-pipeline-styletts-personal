#!/usr/bin/env python3
"""
Diagnostic script: Show what's in pipeline.json vs what Phase 5 sees
"""

import json
import sys
from pathlib import Path

# Paths
project_root = Path(__file__).parent.parent
pipeline_json = project_root / "pipeline.json"
phase4_audio_dir = project_root / "phase4_tts" / "audio_chunks"
file_id = "The_Analects_of_Confucius_20240228"

print("=" * 80)
print("DIAGNOSTIC: Phase 4 → Phase 5 Path Resolution")
print("=" * 80)
print()

# 1. Check pipeline.json structure
print("[1] Loading pipeline.json...")
try:
    with open(pipeline_json, "r") as f:
        pipeline = json.load(f)
    print(f"✓ Loaded pipeline.json: {pipeline_json}")
except Exception as e:
    print(f"✗ Failed to load pipeline.json: {e}")
    sys.exit(1)

# 2. Check Phase 4 structure
print()
print("[2] Checking Phase 4 structure...")
phase4 = pipeline.get("phase4", {})
print(f"  Phase 4 status: {phase4.get('status', 'N/A')}")

phase4_files = phase4.get("files", {})
print(f"  File IDs in Phase 4: {list(phase4_files.keys())}")

if file_id not in phase4_files:
    print(f"\n✗ ERROR: file_id '{file_id}' not found in Phase 4!")
    print(f"  Available IDs: {list(phase4_files.keys())}")
    sys.exit(1)

file_data = phase4_files[file_id]
print(f"\n  File '{file_id}' data keys: {list(file_data.keys())}")
print(f"  Status: {file_data.get('status', 'N/A')}")

# 3. Check chunk_audio_paths
print()
print("[3] Checking chunk_audio_paths array...")
chunk_audio_paths = file_data.get("chunk_audio_paths", [])
print(f"  Found: {len(chunk_audio_paths)} paths in chunk_audio_paths")

if len(chunk_audio_paths) == 0:
    print("\n✗ ERROR: chunk_audio_paths is empty or missing!")
    print("  This is why Phase 5 skips files!")
    print("\n  Run: python finalize_phase4_only.py")
    sys.exit(1)

# 4. Sample paths and check if they exist
print()
print("[4] Validating sample paths...")
print("  First 3 paths:")
for i, path in enumerate(chunk_audio_paths[:3]):
    exists = Path(path).exists()
    status_icon = "✓" if exists else "✗"
    print(f"    {i}: {status_icon} {path}")

print("  Last 3 paths:")
for i, path in enumerate(
    chunk_audio_paths[-3:], start=len(chunk_audio_paths) - 3
):
    exists = Path(path).exists()
    status_icon = "✓" if exists else "✗"
    print(f"    {i}: {status_icon} {path}")

# 5. Count how many paths actually exist
print()
print("[5] Checking path validity...")
existing_paths = [p for p in chunk_audio_paths if Path(p).exists()]
missing_paths = [p for p in chunk_audio_paths if not Path(p).exists()]

print(f"  Total paths in JSON: {len(chunk_audio_paths)}")
print(f"  Existing files:      {len(existing_paths)} ✓")
print(f"  Missing files:       {len(missing_paths)} ✗")

if missing_paths:
    print("\n  Sample missing paths:")
    for path in missing_paths[:5]:
        print(f"    - {path}")

# 6. Check Phase 4 audio directory
print()
print("[6] Checking Phase 4 audio_chunks directory...")
if not phase4_audio_dir.exists():
    print(f"  ✗ Directory not found: {phase4_audio_dir}")
else:
    actual_files = list(phase4_audio_dir.glob("*.wav"))
    print(f"  ✓ Directory exists: {phase4_audio_dir}")
    print(f"  Actual WAV files: {len(actual_files)}")

    if actual_files:
        print("  Sample files:")
        for f in actual_files[:3]:
            print(f"    - {f.name}")

# 7. Simulate what Phase 5 will see
print()
print("[7] Simulating Phase 5's get_audio_chunks_from_json()...")

chunks_phase5_will_find = []
for idx, wav_path in enumerate(chunk_audio_paths):
    abs_wav = Path(wav_path)

    if abs_wav.is_absolute() and abs_wav.exists():
        chunks_phase5_will_find.append(idx)
    else:
        print(f"  ✗ Chunk {idx}: Path invalid or doesn't exist")
        print(f"      Path: {wav_path}")
        print(f"      Absolute: {abs_wav.is_absolute()}")
        print(f"      Exists: {abs_wav.exists()}")

print(
    f"\n  Phase 5 will process: {len(chunks_phase5_will_find)} / {len(chunk_audio_paths)} chunks"
)

# 8. Summary
print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

if len(chunk_audio_paths) == 0:
    print("❌ CRITICAL: chunk_audio_paths is empty!")
    print("   Fix: Run finalize_phase4_only.py")
elif len(missing_paths) > 0:
    print(f"⚠️  WARNING: {len(missing_paths)} paths don't exist!")
    print("   Fix: Check if paths are absolute and correct")
elif len(chunks_phase5_will_find) < len(chunk_audio_paths):
    print(
        f"⚠️  WARNING: Phase 5 will only process {len(chunks_phase5_will_find)} / {len(chunk_audio_paths)} chunks"
    )
    print("   Fix: Check Phase 5's path resolution logic")
else:
    print(
        f"✅ SUCCESS: All {len(chunk_audio_paths)} paths are valid and Phase 5 should process them!"
    )

print()
