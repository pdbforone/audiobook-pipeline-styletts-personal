#!/usr/bin/env python3
"""
Check working directory resolution
"""

from pathlib import Path

print("="*80)
print("WORKING DIRECTORY CHECK")
print("="*80)

# Where is the test script?
test_script = Path("../phase4_tts/test_simple_text.py")
print(f"\nTest script location: {test_script.absolute()}")

# What is Path(".") from test script directory?
test_dir = Path("../phase4_tts")
print(f"\nTest working directory: {test_dir.absolute()}")
print(f"  Resolved from Path('.'): {Path('.').absolute() if Path.cwd().name == 'phase4_tts' else 'N/A'}")

# What does orchestrator use?
phase_dir = Path("../phase4_tts")
print(f"\nOrchestrator phase_dir: {phase_dir.absolute()}")
print(f"  str(phase_dir): {str(phase_dir)}")

# Are they the same?
print(f"\nAre they equivalent?")
print(f"  Test:        cwd=Path('.')")
print(f"  Orchestrator: cwd=str({phase_dir})")
print(f"  Both resolve to: {phase_dir.absolute()}")

# Check main script paths
print(f"\n" + "="*80)
print("MAIN SCRIPT PATHS")
print("="*80)

# Test uses relative path
test_main = "src/phase4_tts/main.py"
print(f"\nTest: python {test_main}")
print(f"  From: {test_dir.absolute()}")
print(f"  Resolves to: {(test_dir / test_main).absolute()}")

# Orchestrator uses absolute path  
orch_main = phase_dir / "src" / "phase4_tts" / "main.py"
print(f"\nOrchestrator: python {str(orch_main)}")
print(f"  From: {phase_dir.absolute()}")
print(f"  Resolves to: {orch_main.absolute()}")

# Are they the same file?
test_resolved = (test_dir / test_main).absolute()
orch_resolved = orch_main.absolute()

print(f"\nSame file? {test_resolved == orch_resolved}")

if test_resolved != orch_resolved:
    print(f"\n❌ DIFFERENT FILES!")
    print(f"  Test:        {test_resolved}")
    print(f"  Orchestrator: {orch_resolved}")
else:
    print(f"\n✅ Same file: {test_resolved}")

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

print("""
If the paths are the same, then the difference must be in:
1. Command line arguments
2. Environment variables  
3. Pipeline.json content
4. Timing/caching issues

Let me check the commands one more time...
""")

print("\nTEST COMMAND:")
print("""
cmd = [
    "conda", "run",
    "-n", "phase4_tts",
    "--no-capture-output",
    "python", "src/phase4_tts/main.py",  # ← RELATIVE
    "--chunk_id=0",
    "--file_id=TEST_SIMPLE",
    "--json_path={absolute_path}",
    "--ref_file=greenman_ref.wav"
]
cwd = Path(".")  # phase4_tts directory
""")

print("\nORCHESTRATOR COMMAND:")
print(f"""
cmd = [
    "conda", "run",
    "-n", "phase4_tts",
    "--no-capture-output",
    "python", "{str(orch_main)}",  # ← ABSOLUTE
    "--chunk_id=0",
    "--file_id=The_Analects_of_Confucius_20240228",
    "--json_path={{absolute_path}}",
    "--ref_file={str(phase_dir / 'greenman_ref.wav')}"
]
cwd = str({phase_dir})  # phase4_tts directory
""")

print("\n⚠️  KEY DIFFERENCE:")
print("  Test uses:        'python src/phase4_tts/main.py'")
print(f"  Orchestrator uses: 'python {orch_main}'")
print("\nThis might affect how Python resolves imports!")
print("Let me test if this is the issue...")
