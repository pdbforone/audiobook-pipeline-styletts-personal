#!/usr/bin/env python3
"""
Test script to check what file_id Phase 3 actually wrote to pipeline.json
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
print("PHASE 3 OUTPUT ANALYSIS")
print("="*60)

phase3 = pipeline.get("phase3", {})
files = phase3.get("files", {})

if not files:
    print("WARNING: No files found in Phase 3 output")
    print("\nPhase 3 structure:")
    print(json.dumps(phase3, indent=2)[:500])
else:
    print(f"\nFound {len(files)} file(s) in Phase 3:")
    print()
    
    for file_id, data in files.items():
        chunk_paths = data.get("chunk_paths", [])
        status = data.get("status", "unknown")
        
        print(f"File ID: '{file_id}'")
        print(f"  Status: {status}")
        print(f"  Chunks: {len(chunk_paths)}")
        
        if chunk_paths:
            first_chunk = chunk_paths[0]
            print(f"  First chunk: {first_chunk}")
            print(f"  Last chunk: {chunk_paths[-1]}")
            
            # Check if paths are relative or absolute
            from pathlib import Path
            first_path = Path(first_chunk)
            if first_path.is_absolute():
                print(f"  ✓ Paths are ABSOLUTE")
                if first_path.exists():
                    print(f"  ✓ First chunk file EXISTS")
                else:
                    print(f"  ✗ First chunk file NOT FOUND")
            else:
                print(f"  ⚠ Paths are RELATIVE (problem!)")
                # Try to find where they might be
                possible_bases = [
                    Path("../phase3-chunking") / first_chunk,
                    Path("..") / first_chunk,
                    Path("../chunks") / Path(first_chunk).name
                ]
                for base_path in possible_bases:
                    if base_path.exists():
                        print(f"  ✓ Found at: {base_path.resolve()}")
                        break
                else:
                    print(f"  ✗ Could not find chunk files")
        print()

print("="*60)
print("\nTo run Phase 4 with the correct file_id, use:")
if files:
    actual_id = list(files.keys())[0]
    print(f'python orchestrator.py "your_file.pdf" --phases 4')
    print(f'\nThe orchestrator will now auto-detect: "{actual_id}"')
print("="*60 + "\n")
