#!/usr/bin/env python3
"""
Test the minimal version with clean chunk 2 text
"""

import subprocess
from pathlib import Path
import json

print("="*80)
print("TESTING MINIMAL MAIN.PY")
print("="*80)

# Setup
phase4_dir = Path("../phase4_tts")
pipeline_json = Path("../pipeline.json")
chunk2_file = Path("../phase3-chunking/chunks/The Analects of Confucius_20240228_chunk_002.txt")

# Check if chunk exists
if not chunk2_file.exists():
    print(f"❌ Chunk 2 not found: {chunk2_file}")
    exit(1)

# Read text
chunk2_text = chunk2_file.read_text(encoding='utf-8')
print(f"\nChunk 2 text ({len(chunk2_text)} chars):")
print(chunk2_text[:150])

# Create test entry in pipeline.json
with open(pipeline_json) as f:
    pipeline = json.load(f)

test_id = "TEST_MINIMAL"
if "phase3" not in pipeline:
    pipeline["phase3"] = {"files": {}}

pipeline["phase3"]["files"][test_id] = {
    "chunk_paths": [str(chunk2_file.absolute())]
}

with open(pipeline_json, 'w') as f:
    json.dump(pipeline, f, indent=4)

print(f"\n✓ Added to pipeline.json as: {test_id}")

# Test with minimal version
print("\n" + "="*80)
print("RUNNING MINIMAL VERSION")
print("="*80)

cmd = [
    "conda", "run",
    "-n", "phase4_tts",
    "--no-capture-output",
    "python", "src/phase4_tts/main_minimal.py",
    "--chunk_id=0",
    f"--file_id={test_id}",
    f"--json_path={pipeline_json.absolute()}",
    "--ref_file=greenman_ref.wav"
]

print(f"Command: {' '.join(cmd)}")
print(f"Working dir: {phase4_dir}\n")

result = subprocess.run(cmd, cwd=str(phase4_dir))

print("\n" + "="*80)
if result.returncode == 0:
    print("✅ SUCCESS - Check audio_chunks/chunk_0.wav")
    print("\nListen to it. Does it sound like clear English?")
    print("\nIf YES: The minimal version works!")
    print("If NO: There's something fundamentally wrong with the Chatterbox setup")
else:
    print("❌ FAILED")
    print("Check error messages above")

print("="*80)
