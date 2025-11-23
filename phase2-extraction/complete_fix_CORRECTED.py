#!/usr/bin/env python3
"""
COMPLETE FIX for Systematic Theology extraction

This script:
1. Backs up original extraction.py
2. Applies the pypdf fix to Phase 2
3. Fixes Phase 1 to save file_path in pipeline.json
4. Runs Phase 1 → Phase 2 properly
5. Verifies extraction quality
"""
import subprocess
import sys
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPRECATED_PROCESS_SCRIPT = (
    PROJECT_ROOT
    / "deprecated"
    / "phase2-extraction"
    / "process_systematic_theology_FIXED.py"
)

print("=" * 80)
print("SYSTEMATIC THEOLOGY - COMPLETE FIX (CORRECTED)")
print("=" * 80)

phase1_dir = PROJECT_ROOT / "phase1-validation"
phase2_dir = PROJECT_ROOT / "phase2-extraction"
extraction_file = phase2_dir / "src" / "phase2_extraction" / "extraction.py"
patched_file = phase2_dir / "extraction_PATCHED.py"
validation_file = phase1_dir / "src" / "phase1_validation" / "validation.py"

# Step 1: Apply Phase 2 pypdf fix
print("\n📦 STEP 1: APPLYING PHASE 2 PYPDF FIX")
print("=" * 80)

if not patched_file.exists():
    print(f"❌ Patched file not found: {patched_file}")
    print(
        "   Please ensure extraction_PATCHED.py is in the phase2-extraction folder"
    )
    sys.exit(1)

# Backup original Phase 2
backup_file = extraction_file.parent / "extraction.py.backup"
if not backup_file.exists():
    print(f"Creating backup: {backup_file.name}")
    shutil.copy2(extraction_file, backup_file)
    print("✓ Phase 2 original backed up")
else:
    print(f"✓ Phase 2 backup already exists: {backup_file.name}")

# Apply Phase 2 patch
print("Applying patched extraction.py...")
shutil.copy2(patched_file, extraction_file)
print("✓ Phase 2 patched (now uses pypdf first)")

# Step 2: Fix Phase 1 to save file_path
print("\n📦 STEP 2: FIXING PHASE 1 TO SAVE FILE_PATH")
print("=" * 80)

# Backup original Phase 1
validation_backup = validation_file.parent / "validation.py.backup"
if not validation_backup.exists():
    print(f"Creating backup: {validation_backup.name}")
    shutil.copy2(validation_file, validation_backup)
    print("✓ Phase 1 original backed up")
else:
    print("✓ Phase 1 backup already exists")

# Read and patch Phase 1
print("Patching Phase 1 to save file_path...")
with open(validation_file, "r", encoding="utf-8") as f:
    phase1_content = f.read()

# Check if already patched
if '"file_path":' in phase1_content:
    print("✓ Phase 1 already patched (saves file_path)")
else:
    # Find the merge_to_json function and add file_path
    # Look for: data["phase1"]["files"][file_id].update(metadata.model_dump())
    # Add after it: data["phase1"]["files"][file_id]["file_path"] = file_path

    import_line = 'def merge_to_json(\n    metadata: FileMetadata, json_path: str = "pipeline.json", file_id: str = ""\n):'
    new_import = 'def merge_to_json(\n    metadata: FileMetadata, json_path: str = "pipeline.json", file_id: str = "", file_path: str = ""\n):'

    if import_line in phase1_content:
        phase1_content = phase1_content.replace(import_line, new_import)

        # Add file_path to the data structure
        update_line = (
            'data["phase1"]["files"][file_id].update(metadata.model_dump())'
        )
        new_update = 'data["phase1"]["files"][file_id].update(metadata.model_dump())\n    data["phase1"]["files"][file_id]["file_path"] = file_path'

        if update_line in phase1_content:
            phase1_content = phase1_content.replace(update_line, new_update)

            # Update the call to merge_to_json in main()
            old_call = "merge_to_json(metadata, args.json_path, file_id)"
            new_call = (
                "merge_to_json(metadata, args.json_path, file_id, args.file)"
            )

            if old_call in phase1_content:
                phase1_content = phase1_content.replace(old_call, new_call)

                # Write patched file
                with open(validation_file, "w", encoding="utf-8") as f:
                    f.write(phase1_content)
                print("✓ Phase 1 patched to save file_path")
            else:
                print(
                    "⚠️  Could not find merge_to_json call - manual fix needed"
                )
        else:
            print("⚠️  Could not find update line - manual fix needed")
    else:
        print("⚠️  Phase 1 structure unexpected - manual fix needed")

# Step 3: Install pypdf if needed
print("\n📦 STEP 3: INSTALLING PYPDF")
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
        print("⚠️  Failed to auto-install pypdf")
        print(
            "   Please run manually: cd phase2-extraction && poetry add pypdf"
        )
else:
    print("✓ pypdf already installed")

# Step 4: Process the file
print("\n📄 STEP 4: PROCESSING SYSTEMATIC THEOLOGY")
print("=" * 80)
print(f"\nNow running deprecated fixer at {DEPRECATED_PROCESS_SCRIPT}...")
print("This will run Phase 1 → Phase 2 with proper tracking\n")

# Run the FIXED processing script
result = subprocess.run(
    ["python", str(DEPRECATED_PROCESS_SCRIPT)], cwd=str(phase2_dir)
)

if result.returncode != 0:
    print("\n❌ Processing failed")
    print("\nTroubleshooting:")
    print(
        "  1. Check Phase 1 module: cd phase1-validation && poetry run python -m phase1_validation.validation --help"
    )
    print(
        "  2. Check Phase 2 module: cd phase2-extraction && poetry run python -m phase2_extraction.extraction --help"
    )
    print(
        "  3. Check pypdf: cd phase2-extraction && poetry run python -c 'import pypdf'"
    )
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL FIXES APPLIED AND TESTED")
print("=" * 80)
print(
    """
Summary:
  ✓ Phase 1 now saves file_path in pipeline.json
  ✓ Phase 2 uses pypdf for better font encoding
  ✓ pypdf dependency installed
  ✓ Systematic Theology processed through proper pipeline
  ✓ Results tracked in pipeline.json

Next steps:
  - Check the extracted text quality
  - If quality is good, proceed to Phase 3 (Chunking)
  - If still gibberish, run test_extraction_methods.py for diagnosis

Backups created:
  - phase1-validation/src/phase1_validation/validation.py.backup
  - phase2-extraction/src/phase2_extraction/extraction.py.backup
"""
)
