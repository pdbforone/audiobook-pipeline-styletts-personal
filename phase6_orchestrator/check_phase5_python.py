"""Check Phase 5 Python version"""

import subprocess
from pathlib import Path

phase5_dir = Path(__file__).parent.parent / "phase5_enhancement"

print("Checking Phase 5 virtual environment...")
print()

# Check what Python version the venv is using
try:
    result = subprocess.run(
        ["poetry", "env", "info"],
        cwd=str(phase5_dir),
        capture_output=True,
        text=True,
        timeout=10,
    )

    print(result.stdout)

    if "3.11" in result.stdout:
        print()
        print("⚠ PROBLEM FOUND: Phase 5 is using Python 3.11 but needs 3.12!")
        print()
        print("Fix by deleting and recreating the environment:")
        print(f"  Remove-Item {phase5_dir / '.venv'} -Recurse -Force")
        print("  python setup_phase5.py")
    elif "3.12" in result.stdout:
        print()
        print("✓ Phase 5 is using Python 3.12 (correct)")

except Exception as e:
    print(f"Error: {e}")
