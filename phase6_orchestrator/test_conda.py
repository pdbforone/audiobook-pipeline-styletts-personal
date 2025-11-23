"""Test Phase 4 Conda environment setup (manual utility)."""

import subprocess
import sys


def main() -> int:
    print("Testing Phase 4 Conda environment...\n")

    # Test 1: Conda installed
    try:
        r = subprocess.run(
            ["conda", "--version"], capture_output=True, text=True, timeout=10
        )
        print(f"✓ Conda: {r.stdout.strip()}")
    except Exception:
        print("✗ Conda not found")
        return 1

    # Test 2: Environment exists
    r = subprocess.run(
        ["conda", "env", "list"], capture_output=True, text=True, timeout=10
    )
    if "phase4_tts" in r.stdout:
        print("✓ phase4_tts environment exists")
    else:
        print("✗ phase4_tts environment not found")
        print("  Create it: conda env create -f phase4_tts/environment.yml")
        return 1

    # Test 3: Can run Python
    r = subprocess.run(
        ["conda", "run", "-n", "phase4_tts", "python", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode == 0:
        print(f"✓ Python: {r.stdout.strip()}")
    else:
        print("✗ Cannot run Python in environment")
        return 1

    print("\n✓ Phase 4 Conda environment is ready!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
