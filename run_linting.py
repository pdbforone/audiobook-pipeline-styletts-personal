"""
Automated linting and formatting script for the audiobook pipeline.

This script runs Black, Flake8, and other linting tools on the codebase.
It handles installation and runs the tools in the correct environments.

Usage:
    python run_linting.py [--fix] [--check-only]

Options:
    --fix         Apply automatic fixes (Black formatting)
    --check-only  Only check for issues, don't fix
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def run_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*80}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        success = result.returncode == 0
        status = "[PASSED]" if success else "[FAILED]"
        print(f"\n{status}: {description}\n")

        return success, result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT]: {description}")
        return False, "Command timed out"
    except Exception as e:
        print(f"[ERROR]: {description}")
        print(f"   {e}")
        return False, str(e)


def ensure_tool_installed(tool_name: str) -> bool:
    """Ensure a Python tool is installed globally."""
    print(f"[*] Checking if {tool_name} is installed...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", tool_name, "--version"],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"    [OK] {tool_name} is already installed")
            return True
    except Exception:
        pass

    print(f"    Installing {tool_name}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", tool_name],
        capture_output=True,
        timeout=120
    )

    if result.returncode == 0:
        print(f"    [OK] {tool_name} installed successfully")
        return True
    else:
        print(f"    [ERROR] Failed to install {tool_name}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run linting on audiobook pipeline"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply automatic fixes with Black"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check formatting, don't apply fixes"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("Audiobook Pipeline - Linting Suite")
    print("=" * 80)

    # Ensure tools are installed
    tools = ["black", "flake8"]
    print("\n[*] Installing/verifying linting tools...")
    for tool in tools:
        if not ensure_tool_installed(tool):
            print(f"\n[ERROR] Failed to install {tool}. Please install manually:")
            print(f"   pip install {tool}")
            sys.exit(1)

    # Define directories to lint
    target_dirs = [
        "phase1-validation/src",
        "phase2-extraction/src",
        "phase3-chunking/src",
        "phase4_tts/src",
        "phase5_enhancement/src",
        "phase6_orchestrator",
        "ui",
    ]

    # Filter to only existing directories
    existing_dirs = [d for d in target_dirs if Path(d).exists()]
    print(f"\n[*] Target directories: {len(existing_dirs)}")
    for d in existing_dirs:
        print(f"   - {d}")

    results = []

    # Run Black (formatter)
    if not args.check_only:
        mode = "format" if args.fix else "check"
        black_cmd = [sys.executable, "-m", "black"]

        if not args.fix:
            black_cmd.append("--check")

        black_cmd.extend([
            "--line-length", "100",
            "--target-version", "py39",
        ])
        black_cmd.extend(existing_dirs)

        success, output = run_command(
            black_cmd,
            f"Black - Code Formatting ({mode})"
        )
        results.append(("Black", success))
    else:
        print("\n[*] Skipping Black (--check-only mode)")

    # Run Flake8 (style checker)
    flake8_cmd = [
        sys.executable, "-m", "flake8",
        "--max-line-length", "100",
        "--extend-ignore", "E203,W503,E501",  # Black compatibility
        "--exclude", ".venv,venv,.git,__pycache__,.pytest_cache,.engine_envs",
        "--statistics",
        "--count",
    ]
    flake8_cmd.extend(existing_dirs)

    success, output = run_command(
        flake8_cmd,
        "Flake8 - Style Checking"
    )
    results.append(("Flake8", success))

    # Print summary
    print("\n" + "=" * 80)
    print("LINTING SUMMARY")
    print("=" * 80)

    all_passed = True
    for tool, success in results:
        status = "[PASSED]" if success else "[FAILED]"
        print(f"{status}: {tool}")
        if not success:
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("\n[SUCCESS] All linting checks passed!")
        return 0
    else:
        print("\n[WARNING] Some linting checks failed.")
        if not args.fix:
            print("   Run with --fix to automatically fix formatting issues:")
            print("   python run_linting.py --fix")
        return 1


if __name__ == "__main__":
    sys.exit(main())
