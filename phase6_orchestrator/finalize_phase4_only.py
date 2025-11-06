#!/usr/bin/env python3
"""
Quick fix: Update pipeline.json with absolute paths from Phase 4 audio files.
This skips re-running Phase 4 TTS (which takes forever).
"""

import json
import sys
from pathlib import Path
import re

# Paths
project_root = Path(__file__).parent.parent
pipeline_json = project_root / "pipeline.json"
phase4_audio_dir = project_root / "phase4_tts" / "audio_chunks"
file_id = "The_Analects_of_Confucius_20240228"

print("="*60)
print("Phase 4 Finalization (Without Re-running TTS)")
print("="*60)
print()

# Check audio directory exists
if not phase4_audio_dir.exists():
    print(f"ERROR: Audio directory not found: {phase4_audio_dir}")
    sys.exit(1)

# Scan for all audio files
all_files = list(phase4_audio_dir.glob("*.wav"))
print(f"Found {len(all_files)} total audio files in {phase4_audio_dir}")

if len(all_files) == 0:
    print("ERROR: No audio files found!")
    sys.exit(1)

# Try multiple filename patterns
pattern1_files = [f for f in all_files if f.stem.startswith(f"{file_id}_chunk_")]
pattern2_files = [f for f in all_files if f.stem.startswith("chunk_") and not f.stem.startswith(f"{file_id}_")]

if pattern1_files:
    print(f"Using filename pattern: {file_id}_chunk_NNN.wav")
    audio_files = pattern1_files
elif pattern2_files:
    print(f"Using filename pattern: chunk_NNN.wav")
    audio_files = pattern2_files
else:
    print(f"ERROR: No matching chunk files found for file_id '{file_id}'")
    print(f"Sample files: {[f.name for f in all_files[:5]]}")
    sys.exit(1)

# Sort by chunk number
def extract_chunk_num(path: Path) -> int:
    match = re.search(r'chunk[_-](\d+)', path.stem)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)', path.stem)
    return int(match.group(1)) if match else 0

audio_files = sorted(audio_files, key=extract_chunk_num)
print(f"Sorted {len(audio_files)} audio files")

# Build absolute paths
audio_paths = [str(f.resolve()) for f in audio_files]

print(f"\nSample paths:")
print(f"  First: {audio_paths[0]}")
print(f"  Last:  {audio_paths[-1]}")

# Update pipeline.json
print(f"\nUpdating pipeline.json...")
try:
    with open(pipeline_json, 'r') as f:
        pipeline = json.load(f)
    
    # Ensure phase4 structure exists
    if 'phase4' not in pipeline:
        pipeline['phase4'] = {'status': 'success', 'files': {}}
    if 'files' not in pipeline['phase4']:
        pipeline['phase4']['files'] = {}
    if file_id not in pipeline['phase4']['files']:
        pipeline['phase4']['files'][file_id] = {}
    
    # Update with absolute paths
    pipeline['phase4']['files'][file_id]['chunk_audio_paths'] = audio_paths
    pipeline['phase4']['files'][file_id]['status'] = 'success'
    pipeline['phase4']['files'][file_id]['total_chunks'] = len(audio_paths)
    pipeline['phase4']['files'][file_id]['audio_dir'] = str(phase4_audio_dir.resolve())
    pipeline['phase4']['status'] = 'success'
    
    # Write back
    with open(pipeline_json, 'w') as f:
        json.dump(pipeline, f, indent=4)
    
    print(f"✓ Updated pipeline.json with {len(audio_paths)} ABSOLUTE audio paths")
    print()
    print("="*60)
    print("SUCCESS! pipeline.json updated")
    print("="*60)
    print()
    print("Now run Phase 5:")
    print("  cd phase6_orchestrator")
    print(f"  poetry run python orchestrator.py \"{project_root / 'input' / 'The_Analects_of_Confucius_20240228.pdf'}\" --phases 5 --no-resume")
    
except Exception as e:
    print(f"ERROR: Failed to update pipeline.json: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
