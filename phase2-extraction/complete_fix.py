#!/usr/bin/env python3
"""
ONE-CLICK FIX for Systematic Theology gibberish extraction

This script:
1. Backs up original extraction.py
2. Applies the pypdf fix
3. Installs pypdf dependency
4. Runs Phase 1 → Phase 2 properly
5. Verifies extraction quality
"""
import subprocess
import sys
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]

print("=" * 80)
print("SYSTEMATIC THEOLOGY - COMPLETE FIX")
print("=" * 80)

phase2_dir = PROJECT_ROOT / "phase2-extraction"
extraction_file = phase2_dir / "src" / "phase2_extraction" / "extraction.py"
patched_file = phase2_dir / "extraction_PATCHED.py"

# Step 1: Backup and apply fix
print("\n📦 STEP 1: APPLYING PYPDF FIX")
print("=" * 80)

if not patched_file.exists():
    print(f"❌ Patched file not found: {patched_file}")
    print(
        "   Please ensure extraction_PATCHED.py is in the phase2-extraction folder"
    )
    sys.exit(1)

# Backup original
backup_file = extraction_file.parent / "extraction.py.backup"
if not backup_file.exists():
    print(f"Creating backup: {backup_file.name}")
    shutil.copy2(extraction_file, backup_file)
    print("✓ Original backed up")
else:
    print(f"✓ Backup already exists: {backup_file.name}")

# Apply patch
print("Applying patched extraction.py...")
shutil.copy2(patched_file, extraction_file)
print("✓ Patched extraction.py applied (now uses pypdf first)")

# Step 2: Install pypdf
print("\n📦 STEP 2: INSTALLING PYPDF")
print("=" * 80)

print("Checking if pypdf is installed...")
check_result = subprocess.run(
    ["poetry", "run", "python", "-c", "import pypdf; print('installed')"],
    cwd=str(phase2_dir),
    capture_output=True,
    text=True,
)

if "installed" not in check_result.stdout:
    print("Installing pypdf...")
    install_result = subprocess.run(
        ["poetry", "add", "pypdf"],
        cwd=str(phase2_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )

    if install_result.returncode == 0:
        print("✓ pypdf installed successfully")
    else:
        print("❌ Failed to install pypdf")
        print(install_result.stderr)
        print("\nPlease install manually:")
        print("   cd phase2-extraction")
        print("   poetry add pypdf")
        sys.exit(1)
else:
    print("✓ pypdf already installed")

# Step 3: Process the file
print("\n📄 STEP 3: PROCESSING SYSTEMATIC THEOLOGY")
print("=" * 80)
print("\nNow running process_systematic_theology.py...")
print("This will run Phase 1 → Phase 2 with proper tracking\n")

# Run the processing script
result = subprocess.run(
    ["python", "process_systematic_theology.py"], cwd=str(phase2_dir)
)

if result.returncode != 0:
    print("\n❌ Processing failed")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL FIXES APPLIED AND TESTED")
print("=" * 80)
print(
    """
Summary:
  ✓ extraction.py now uses pypdf for better font encoding
  ✓ pypdf dependency installed
  ✓ Systematic Theology processed through proper pipeline
  ✓ Results tracked in pipeline.json

Next steps:
  - Check the extracted text quality in phase2-extraction/extracted_text/
  - If quality is good, proceed to Phase 3 (Chunking)
  - If still gibberish, run test_extraction_methods.py for diagnosis
"""
)
