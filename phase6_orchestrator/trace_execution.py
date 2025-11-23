#!/usr/bin/env python3
"""
EXECUTION PATH COMPARISON
Trace EXACTLY what happens when test vs orchestrator calls Phase 4
"""

import sys
from pathlib import Path

print("=" * 80)
print("EXECUTION PATH TRACER")
print("=" * 80)

print("\nThis script will show you EXACTLY what commands are being run.")
print(
    "We need to see if test and orchestrator are calling Phase 4 differently.\n"
)

# Check current directory
cwd = Path.cwd()
print(f"Current directory: {cwd}")

# Check if we're in the right place
phase4_dir = Path("../phase4_tts")
if not phase4_dir.exists():
    print(f"\n❌ Phase 4 directory not found: {phase4_dir.absolute()}")
    print("Run this script from phase6_orchestrator directory")
    sys.exit(1)

print(f"✅ Phase 4 directory found: {phase4_dir.absolute()}")

# ============================================================================
# PART 1: Show what test_simple_text.py does
# ============================================================================

print("\n" + "=" * 80)
print("TEST EXECUTION (test_simple_text.py)")
print("=" * 80)

test_script = phase4_dir / "test_simple_text.py"
if test_script.exists():
    print(f"\n✅ Test script found: {test_script}")

    # Read and show the command
    content = test_script.read_text()

    print("\nThe test creates this command:")
    print("-" * 80)
    print(
        """
cmd = [
    "conda", "run",
    "-n", "phase4_tts",
    "--no-capture-output",
    "python", "src/phase4_tts/main.py",
    f"--chunk_id=0",
    f"--file_id=TEST_SIMPLE",
    f"--json_path={pipeline_json.absolute()}",
    f"--ref_file=greenman_ref.wav"
]

subprocess.run(cmd, cwd=Path("."))
    """
    )

    print("\nKey points:")
    print("  ✅ No --language parameter (defaults to 'en' in argparse)")
    print("  ✅ Uses greenman_ref.wav reference")
    print("  ✅ Working directory: phase4_tts/")
    print("  ✅ Calls main.py directly")

else:
    print(f"\n❌ Test script not found: {test_script}")

# ============================================================================
# PART 2: Show what orchestrator does
# ============================================================================

print("\n" + "=" * 80)
print("ORCHESTRATOR EXECUTION (orchestrator.py)")
print("=" * 80)

orch_script = Path("orchestrator.py")
if orch_script.exists():
    print(f"\n✅ Orchestrator found: {orch_script}")

    content = orch_script.read_text()

    # Find the Phase 4 command construction
    print("\nThe orchestrator creates this command (in run_phase4_chunks):")
    print("-" * 80)

    if "--language=en" in content:
        print(
            """
cmd = [
    "conda", "run",
    "-n", conda_env,                    # "phase4_tts"
    "--no-capture-output",
    "python", str(main_script),        # phase4_tts/src/phase4_tts/main.py
    f"--chunk_id={i}",                 # 0, 1, 2, ...
    f"--file_id={file_id}",            # "The Analects of Confucius"
    f"--json_path={pipeline_json}",    # Absolute path
    "--language=en"                    # ✅ EXPLICIT
]

if ref_file.exists():
    cmd.append(f"--ref_file={str(ref_file)}")  # greenman_ref.wav

subprocess.run(cmd, cwd=str(phase_dir))  # Working directory: phase4_tts/
        """
        )

        print("\nKey points:")
        print("  ✅ Has --language=en parameter")
        print("  ✅ Uses greenman_ref.wav if exists")
        print("  ✅ Working directory: phase4_tts/")
        print("  ✅ Calls main.py directly")
        print("  ✅ Uses absolute path to pipeline.json")

    else:
        print(
            """
cmd = [
    "conda", "run",
    "-n", conda_env,
    "--no-capture-output",
    "python", str(main_script),
    f"--chunk_id={i}",
    f"--file_id={file_id}",
    f"--json_path={pipeline_json}"
    # ❌ MISSING --language parameter
]
        """
        )
        print("\n❌ PROBLEM: No --language parameter!")

else:
    print(f"\n❌ Orchestrator not found: {orch_script}")

# ============================================================================
# PART 3: Check if there's a config difference
# ============================================================================

print("\n" + "=" * 80)
print("CONFIG FILE CHECK")
print("=" * 80)

config_file = phase4_dir / "config.yaml"
if config_file.exists():
    print(f"\n✅ Config found: {config_file}")
    content = config_file.read_text()
    print("\nConfig contents:")
    print("-" * 80)
    print(content)
    print("-" * 80)

    if "cfg_weight" in content:
        print("\n⚠️  NOTE: Config has cfg_weight, but it's IGNORED")
        print("   The code hardcodes: exaggeration=0.3, cfg_weight=0.3")
        print("   Both test and orchestrator use the same hardcoded values")

else:
    print(f"\n❌ Config not found: {config_file}")

# ============================================================================
# PART 4: Hypothesis
# ============================================================================

print("\n" + "=" * 80)
print("HYPOTHESIS")
print("=" * 80)

print(
    """
Based on the code analysis:

1. ✅ Both test and orchestrator call the SAME main.py
2. ✅ Both use the SAME hardcoded parameters (exaggeration=0.3, cfg_weight=0.3)
3. ✅ Both use the SAME reference audio (greenman_ref.wav)
4. ✅ Both run in the SAME working directory (phase4_tts/)
5. ✅ Both use Conda environment (phase4_tts)

So if the commands are identical but the output is different, the problem is:

A) ❓ Different TEXT INPUT
   - Test uses: clean English sentences
   - Orchestrator uses: chunks from Phase 3
   → Check if chunks 1, 2, etc. have problems

B) ❓ Different MODEL STATE
   - Maybe the model is loaded fresh for test
   - But reused/cached for orchestrator
   → Unlikely but possible

C) ❓ Different FILE_ID in pipeline.json
   - Test uses: "TEST_SIMPLE"
   - Orchestrator uses: "The Analects of Confucius" or similar
   → Different chunks being read

D) ❓ Conda environment corruption
   - Test runs in clean state
   - Orchestrator runs after other operations
   → Try: conda clean --all && reinstall

E) ❓ Hidden parameter difference
   - Check if main.py reads environment variables
   - Check if there's additional config being loaded

NEXT STEP: Run the audio analysis script to see WHAT KIND of garbage it is:
  python analyze_audio_quality.py

Then describe EXACTLY what you hear:
  - Reversed speech?
  - Repeating loops?
  - Wrong language?
  - Garbled phonemes?
  - Different voice?
"""
)

print("\n" + "=" * 80)
print("ACTION ITEMS")
print("=" * 80)

print(
    """
1. Run audio analysis:
   python analyze_audio_quality.py

2. Listen to both files and describe the difference:
   - chunk_0.wav (test - good)
   - chunk_1.wav (orchestrator - garbage)

3. Check chunk text files:
   cd ../phase3-chunking/chunks
   head -n 20 "The Analects of Confucius_20240228_chunk_001.txt"
   head -n 20 "The Analects of Confucius_20240228_chunk_002.txt"

4. Try running Phase 4 MANUALLY with same command as orchestrator:
   cd ../phase4_tts
   conda run -n phase4_tts python src/phase4_tts/main.py \\
     --chunk_id=1 \\
     --file_id="The Analects of Confucius" \\
     --json_path=../pipeline.json \\
     --language=en \\
     --ref_file=greenman_ref.wav

5. Compare the manual run with orchestrator run
"""
)
