#!/usr/bin/env python3
"""
Quick verification script for Phase 7 batch processing.

Checks:
- Dependencies installed
- Phase 6 orchestrator found
- Configuration valid
- Input directory exists
"""

import sys
from pathlib import Path


def check_imports():
    """Check all required imports"""
    print("Checking imports...")
    try:
        import trio
        import psutil
        import yaml
        from rich.console import Console

        print("  ✓ All dependencies available")
        return True
    except ImportError as e:
        print(f"  ✗ Missing dependency: {e}")
        print("\n  Run: poetry install")
        return False


def check_phase6():
    """Check Phase 6 orchestrator exists"""
    print("\nChecking Phase 6 orchestrator...")

    project_root = Path(__file__).resolve().parent.parent
    orchestrator = project_root / "phase6_orchestrator" / "orchestrator.py"

    if orchestrator.exists():
        print(f"  ✓ Found: {orchestrator}")
        return True
    else:
        print(f"  ✗ Not found: {orchestrator}")
        print("\n  Phase 7 requires Phase 6 to be present")
        return False


def check_config():
    """Check configuration file"""
    print("\nChecking configuration...")

    config_path = Path(__file__).parent / "config.yaml"

    if not config_path.exists():
        print(f"  ✗ Config not found: {config_path}")
        return False

    try:
        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f)

        required_keys = [
            "phases_to_run",
            "input_dir",
            "pipeline_json",
            "max_workers",
        ]

        missing = [k for k in required_keys if k not in config]
        if missing:
            print(f"  ✗ Missing config keys: {missing}")
            return False

        print("  ✓ Config valid")
        print(f"    - Input dir: {config['input_dir']}")
        print(f"    - Max workers: {config['max_workers']}")
        print(f"    - Phases: {config['phases_to_run']}")
        return True

    except Exception as e:
        print(f"  ✗ Config error: {e}")
        return False


def check_input_dir():
    """Check input directory"""
    print("\nChecking input directory...")

    try:
        import yaml

        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        input_dir = Path(config["input_dir"])
        if not input_dir.is_absolute():
            input_dir = (Path(__file__).parent / input_dir).resolve()

        if not input_dir.exists():
            print(f"  ⚠ Directory doesn't exist: {input_dir}")
            print("    Will be created on first run")
            return True

        # Count files
        pdf_count = len(list(input_dir.glob("*.pdf")))
        epub_count = len(list(input_dir.glob("*.epub")))
        total = pdf_count + epub_count

        print(f"  ✓ Input directory: {input_dir}")
        print(f"    - PDFs: {pdf_count}")
        print(f"    - EPUBs: {epub_count}")
        print(f"    - Total: {total}")

        if total == 0:
            print("\n  ⚠ No input files found")
            print(f"    Add PDFs or EPUBs to {input_dir}")

        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all checks"""
    print("=" * 60)
    print("Phase 7 Batch Processing - Installation Check")
    print("=" * 60)

    checks = [
        check_imports(),
        check_phase6(),
        check_config(),
        check_input_dir(),
    ]

    print("\n" + "=" * 60)
    if all(checks):
        print("✓ All checks passed!")
        print("\nReady to run:")
        print("  poetry run batch-audiobook")
        print("\nOr with custom config:")
        print("  poetry run batch-audiobook --config my_config.yaml")
        return 0
    else:
        print("✗ Some checks failed")
        print("\nFix the issues above and try again")
        return 1


if __name__ == "__main__":
    sys.exit(main())
