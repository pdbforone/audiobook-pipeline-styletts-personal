#!/usr/bin/env python3
"""
Check what Phase 4 wrote to pipeline.json
"""

import json
from pathlib import Path

pipeline_path = Path("../pipeline.json")

if not pipeline_path.exists():
    print("ERROR: pipeline.json not found")
    exit(1)

with open(pipeline_path) as f:
    pipeline = json.load(f)

print("\n" + "="*60)
print("PHASE 4 OUTPUT CHECK")
print("="*60)

phase4 = pipeline.get("phase4", {})
files = phase4.get("files", {})

if not files:
    print("\nWARNING: No files found in Phase 4 output")
    print("\nPhase 4 structure:")
    print(json.dumps(phase4, indent=2)[:500])
else:
    print(f"\nFound {len(files)} file(s) in Phase 4:")
    print()
    
    for file_id, data in files.items():
        chunk_audio_paths = data.get("chunk_audio_paths", [])
        status = data.get("status", "unknown")
        
        print(f"File ID: '{file_id}'")
        print(f"  Status: {status}")
        print(f"  Audio chunks: {len(chunk_audio_paths)}")
        
        if chunk_audio_paths:
            print(f"  First audio path: {chunk_audio_paths[0]}")
            
            # Check if file exists
            first_path = Path(chunk_audio_paths[0])
            if first_path.is_absolute():
                if first_path.exists():
                    print(f"  ✓ First file EXISTS at: {first_path}")
                else:
                    print(f"  ✗ First file NOT FOUND at: {first_path}")
            else:
                print(f"  ⚠ Path is RELATIVE: {chunk_audio_paths[0]}")
                # Try to find it
                possible_locations = [
                    Path("../phase4_tts") / chunk_audio_paths[0],
                    Path("..") / chunk_audio_paths[0],
                    Path("../phase4_tts/audio_chunks") / Path(chunk_audio_paths[0]).name
                ]
                for loc in possible_locations:
                    if loc.exists():
                        print(f"  ✓ Found at: {loc.resolve()}")
                        break
        print()

print("="*60)
print("\nPhase 5 looks for files in the 'input_dir' setting from its config.yaml")
print("Check phase5_enhancement/src/phase5_enhancement/config.yaml")
print("="*60 + "\n")
