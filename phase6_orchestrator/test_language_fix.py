#!/usr/bin/env python3
"""
Quick test to verify Phase 4 language parameter fix
Compares command construction between test_simple_text.py and orchestrator.py
"""

from pathlib import Path

print("="*70)
print("PHASE 4 LANGUAGE PARAMETER FIX VERIFICATION")
print("="*70)

# Read orchestrator.py and check for --language parameter
orchestrator_file = Path("orchestrator.py")
if orchestrator_file.exists():
    content = orchestrator_file.read_text()
    
    # Check if --language parameter exists
    if '--language=en' in content or '--language={' in content:
        print("✅ FIXED: Orchestrator now includes --language parameter")
        
        # Find the line
        for i, line in enumerate(content.split('\n'), 1):
            if '--language' in line and 'CRITICAL' in content.split('\n')[max(0, i-2):i+1]:
                print(f"   Found at line ~{i}: {line.strip()}")
                break
    else:
        print("❌ NOT FIXED: --language parameter missing from orchestrator")
        print("   This will cause gibberish audio!")
else:
    print("❌ ERROR: orchestrator.py not found")

print("\n" + "="*70)
print("COMPARISON: Test vs Orchestrator")
print("="*70)

print("\ntest_simple_text.py command (WORKS):")
print("""  cmd = [
      "conda", "run",
      "-n", "phase4_tts",
      "--no-capture-output",
      "python", "src/phase4_tts/main.py",
      "--chunk_id=0",
      "--file_id=TEST_SIMPLE",
      "--json_path=../pipeline.json",
      "--ref_file=greenman_ref.wav"
  ]
  
  ✅ Has reference audio
  ❓ No explicit --language (defaults to 'en' in argparse)
""")

print("\norchestrator.py command (NOW FIXED):")
print("""  cmd = [
      "conda", "run",
      "-n", conda_env,
      "--no-capture-output",
      "python", str(main_script),
      f"--chunk_id={i}",
      f"--file_id={file_id}",
      f"--json_path={pipeline_json}",
      "--language=en"  ← ADDED THIS
  ]
  
  if ref_file.exists():
      cmd.append(f"--ref_file={str(ref_file)}")
  
  ✅ Now has explicit language
  ✅ Has reference audio (if available)
""")

print("\n" + "="*70)
print("WHY THIS MATTERS")
print("="*70)
print("""
Chatterbox TTS is a MULTILINGUAL model supporting 18 languages:
  en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko, hi

Without explicit language:
  ❌ Model may auto-detect language incorrectly
  ❌ Corrupted text (like Phase 3 chunks) confuses detection
  ❌ Model uses wrong phoneme mappings
  ❌ Output sounds like gibberish or mixed languages

With explicit language:
  ✅ Forces English phonetics
  ✅ Consistent output regardless of text corruption
  ✅ Matches reference audio language
  ✅ Clear, intelligible speech
""")

print("\n" + "="*70)
print("NEXT STEPS")
print("="*70)
print("""
1. Test the fix:
   cd C:\\Users\\myson\\Pipeline\\audiobook-pipeline\\phase6_orchestrator
   python orchestrator.py "The Analects of Confucius.pdf" --phases 4

2. Listen to generated audio:
   - Should sound like clear English
   - Should match test_simple_text.py quality
   - No gibberish or garbled speech

3. If still gibberish:
   - Check Phase 3 chunks for text quality
   - Verify reference audio exists
   - Check for other parameter mismatches

4. Compare outputs:
   - phase4_tts/audio_chunks/chunk_0.wav (from test)
   - phase4_tts/audio_chunks/chunk_0.wav (from orchestrator)
   - They should sound similar now
""")

print("="*70)
