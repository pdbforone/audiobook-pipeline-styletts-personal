#!/usr/bin/env python3
"""
Find the exact difference causing garbage audio
"""

import json
from pathlib import Path
import subprocess

print("="*80)
print("FINDING THE EXACT DIFFERENCE")
print("="*80)

# Step 1: Check what the test actually writes to pipeline.json
test_dir = Path("../phase4_tts")
pipeline_json = Path("../pipeline.json")

print("\n1. Loading pipeline.json...")
with open(pipeline_json) as f:
    pipeline = json.load(f)

# Find the test entry
if "phase3" in pipeline and "files" in pipeline["phase3"]:
    files = pipeline["phase3"]["files"]
    
    print(f"\nFound {len(files)} file_ids in Phase 3:")
    for fid in files.keys():
        print(f"  - {fid}")
    
    # Check TEST_SIMPLE
    if "TEST_SIMPLE" in files:
        test_data = files["TEST_SIMPLE"]
        test_chunks = test_data.get("chunk_paths", [])
        print(f"\nTEST_SIMPLE:")
        print(f"  Chunk paths: {test_chunks}")
        if test_chunks:
            test_chunk_file = Path(test_chunks[0])
            print(f"  Exists: {test_chunk_file.exists()}")
            if test_chunk_file.exists():
                test_text = test_chunk_file.read_text(encoding='utf-8')
                print(f"  Length: {len(test_text)} chars")
                print(f"  Preview: {test_text[:100]}")

print("\n" + "="*80)
print("2. Now let's run Phase 4 with EXACT test parameters")
print("="*80)

# Create a test chunk using chunk 2 text (which looked clean)
chunk2_file = Path("../phase3-chunking/chunks/The Analects of Confucius_20240228_chunk_002.txt")
if chunk2_file.exists():
    chunk2_text = chunk2_file.read_text(encoding='utf-8')
    
    # Write it as a test file
    test_file = test_dir / "test_chunk2_copy.txt"
    test_file.write_text(chunk2_text, encoding='utf-8')
    
    print(f"\nCreated test file: {test_file}")
    print(f"Text length: {len(chunk2_text)} chars")
    print(f"First 100 chars: {chunk2_text[:100]}")
    
    # Update pipeline.json with this test
    test_id = "TEST_CHUNK2"
    if "phase3" not in pipeline:
        pipeline["phase3"] = {"files": {}}
    
    pipeline["phase3"]["files"][test_id] = {
        "chunk_paths": [str(test_file.absolute())]
    }
    
    with open(pipeline_json, 'w') as f:
        json.dump(pipeline, f, indent=4)
    
    print(f"\nAdded to pipeline.json as: {test_id}")
    
    # Run Phase 4 with test-style command
    print("\n" + "="*80)
    print("Running Phase 4 - TEST STYLE")
    print("="*80)
    
    cmd_test = [
        "conda", "run",
        "-n", "phase4_tts",
        "--no-capture-output",
        "python", "src/phase4_tts/main.py",
        "--chunk_id=0",
        f"--file_id={test_id}",
        f"--json_path={pipeline_json.absolute()}",
        "--ref_file=greenman_ref.wav"
    ]
    
    print(f"Command: {' '.join(cmd_test)}")
    print(f"Working dir: {test_dir}")
    
    result = subprocess.run(cmd_test, cwd=str(test_dir))
    
    if result.returncode == 0:
        print("\n✅ Test style completed")
        print("Check: audio_chunks/chunk_0.wav")
    else:
        print("\n❌ Test style failed")
    
    # Now run with orchestrator-style command
    print("\n" + "="*80)
    print("Running Phase 4 - ORCHESTRATOR STYLE")
    print("="*80)
    
    # Use the SAME file_id and chunk_id
    main_script = test_dir / "src" / "phase4_tts" / "main.py"
    ref_file = test_dir / "greenman_ref.wav"
    
    cmd_orch = [
        "conda", "run",
        "-n", "phase4_tts",
        "--no-capture-output",
        "python", str(main_script),
        "--chunk_id=0",
        f"--file_id={test_id}",
        f"--json_path={str(pipeline_json.absolute())}"
    ]
    
    if ref_file.exists():
        cmd_orch.append(f"--ref_file={str(ref_file)}")
    
    print(f"Command: {' '.join(cmd_orch)}")
    print(f"Working dir: {test_dir}")
    
    # Save chunk_0.wav first
    chunk0_backup = test_dir / "audio_chunks" / "chunk_0_test_style.wav"
    chunk0_orig = test_dir / "audio_chunks" / "chunk_0.wav"
    if chunk0_orig.exists():
        import shutil
        shutil.copy(chunk0_orig, chunk0_backup)
        print(f"\nBacked up test output to: {chunk0_backup}")
    
    result = subprocess.run(cmd_orch, cwd=str(test_dir))
    
    if result.returncode == 0:
        print("\n✅ Orchestrator style completed")
        print("Check: audio_chunks/chunk_0.wav (orchestrator style)")
        print("\nNow compare:")
        print(f"  1. {chunk0_backup} (test style)")
        print(f"  2. {chunk0_orig} (orchestrator style)")
        print("\nDo they BOTH sound good? Or is orchestrator one garbage?")
    else:
        print("\n❌ Orchestrator style failed")
    
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    print("\nBoth commands used:")
    print("  - SAME text (chunk 2)")
    print("  - SAME file_id (TEST_CHUNK2)")
    print("  - SAME working directory")
    print("  - SAME reference audio")
    print("\nThe ONLY differences:")
    print("  Test:        python src/phase4_tts/main.py")
    print("  Orchestrator: python {full_path}/main.py")
    print("\nIf orchestrator STILL produces garbage, the issue is:")
    print("  - How Python resolves the main script path")
    print("  - Or some hidden state/caching issue")

else:
    print(f"\n❌ Chunk 2 file not found: {chunk2_file}")
