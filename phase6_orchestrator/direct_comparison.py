#!/usr/bin/env python3
"""
Direct comparison: Run Phase 4 exactly like test vs exactly like orchestrator
"""

import subprocess
from pathlib import Path
import json

print("="*80)
print("EXACT COMMAND COMPARISON TEST")
print("="*80)

# First, check what file_id and chunks are in pipeline.json
pipeline_json = Path("../pipeline.json")
with open(pipeline_json) as f:
    pipeline = json.load(f)

phase3_files = pipeline.get("phase3", {}).get("files", {})
print(f"\nPhase 3 file_ids: {list(phase3_files.keys())}")

# Let's use the actual file_id from orchestrator
for file_id, data in phase3_files.items():
    if "Analects" in file_id or "Confucius" in file_id:
        print(f"\nUsing file_id: '{file_id}'")
        chunks = data.get("chunk_paths", [])
        print(f"Total chunks: {len(chunks)}")
        if chunks:
            print(f"Chunk 1 path: {chunks[1]}")  # chunk_id=1 for orchestrator
            
            # Check if it exists and preview
            chunk_path = Path(chunks[1])
            if chunk_path.exists():
                text = chunk_path.read_text(encoding='utf-8')
                print(f"\nChunk 1 text ({len(text)} chars):")
                print(text[:200])
            else:
                print(f"❌ Chunk not found: {chunk_path}")
        
        # Now run Phase 4 EXACTLY like orchestrator does
        print("\n" + "="*80)
        print("RUNNING PHASE 4 - ORCHESTRATOR STYLE")
        print("="*80)
        
        phase4_dir = Path("../phase4_tts")
        main_script = phase4_dir / "src" / "phase4_tts" / "main.py"
        ref_file = phase4_dir / "greenman_ref.wav"
        
        cmd_orchestrator = [
            "conda", "run",
            "-n", "phase4_tts",
            "--no-capture-output",
            "python", str(main_script),
            f"--chunk_id=1",
            f"--file_id={file_id}",
            f"--json_path={str(pipeline_json.absolute())}"
        ]
        
        if ref_file.exists():
            cmd_orchestrator.append(f"--ref_file={str(ref_file)}")
        
        print(f"\nCommand: {' '.join(cmd_orchestrator)}")
        print(f"Working directory: {phase4_dir.absolute()}")
        print(f"Running...")
        
        result = subprocess.run(
            cmd_orchestrator,
            cwd=str(phase4_dir),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print(f"\nExit code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ SUCCESS")
            print("\nCheck audio_chunks/chunk_1.wav")
            print("Does it sound good or garbage?")
        else:
            print("❌ FAILED")
            print(f"\nSTDERR:\n{result.stderr}")
            print(f"\nSTDOUT:\n{result.stdout}")
        
        # Now let's also create a test using the SAME chunk text
        print("\n" + "="*80)
        print("RUNNING PHASE 4 - TEST STYLE (same chunk text)")
        print("="*80)
        
        if chunk_path.exists():
            # Copy chunk 1 to test location
            test_file = phase4_dir / "test_chunk_1.txt"
            test_file.write_text(text, encoding='utf-8')
            
            # Update pipeline.json temporarily
            test_file_id = "TEST_CHUNK_1"
            pipeline["phase3"]["files"][test_file_id] = {
                "chunk_paths": [str(test_file.absolute())]
            }
            
            with open(pipeline_json, 'w') as f:
                json.dump(pipeline, f, indent=4)
            
            cmd_test = [
                "conda", "run",
                "-n", "phase4_tts",
                "--no-capture-output",
                "python", "src/phase4_tts/main.py",
                f"--chunk_id=0",
                f"--file_id={test_file_id}",
                f"--json_path={str(pipeline_json.absolute())}",
                f"--ref_file=greenman_ref.wav"
            ]
            
            print(f"\nCommand: {' '.join(cmd_test)}")
            print(f"Working directory: {phase4_dir.absolute()}")
            print(f"Running...")
            
            result_test = subprocess.run(
                cmd_test,
                cwd=str(phase4_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            print(f"\nExit code: {result_test.returncode}")
            
            if result_test.returncode == 0:
                print("✅ SUCCESS")
                print("\nCheck audio_chunks/chunk_0.wav")
                print("Does it sound good or garbage?")
                print("\nNow compare:")
                print("  - chunk_0.wav (test style) - should be GOOD")
                print("  - chunk_1.wav (orchestrator style) - is it GARBAGE?")
                print("\nIf chunk_0 is good but chunk_1 is garbage,")
                print("then there's something wrong with how orchestrator calls it.")
            else:
                print("❌ FAILED")
                print(f"\nSTDERR:\n{result_test.stderr}")
        
        break

print("\n" + "="*80)
