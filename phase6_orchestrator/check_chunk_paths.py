#!/usr/bin/env python3
"""
Check what chunk paths Phase 4 is reading
"""

import json
from pathlib import Path

pipeline_path = Path("../pipeline.json")

with open(pipeline_path) as f:
    pipeline = json.load(f)

phase3 = pipeline.get("phase3", {})
files = phase3.get("files", {})

print("\n" + "="*60)
print("PHASE 3 CHUNK PATHS CHECK")
print("="*60)

for file_id in ["The Analects of Confucius", "The_Analects_of_Confucius_20240228_converted_with_pdfplumber"]:
    if file_id in files:
        chunk_paths = files[file_id].get("chunk_paths", [])
        print(f"\nFile ID: '{file_id}'")
        print(f"Total chunks: {len(chunk_paths)}")
        if chunk_paths:
            print(f"First chunk: {chunk_paths[0]}")
            print(f"Second chunk: {chunk_paths[1]}")
            
            # Check if files exist
            for i, path in enumerate(chunk_paths[:3]):
                p = Path(path)
                exists = p.exists()
                print(f"  Chunk {i}: {'EXISTS' if exists else 'MISSING'} - {path}")
                
                if exists and i == 0:
                    # Read first few lines
                    with open(p, 'r', encoding='utf-8') as f:
                        content = f.read(300)
                    print(f"\n  First 300 chars of chunk 0:")
                    print(f"  {repr(content)}\n")

print("="*60)
