#!/usr/bin/env python3
"""
Properly process Systematic Theology.pdf through Phase 1 → Phase 2
This ensures pipeline.json tracking and proper classification.
"""
import subprocess
import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]

print("=" * 80)
print("SYSTEMATIC THEOLOGY - PROPER PIPELINE PROCESSING")
print("=" * 80)

# Paths
pdf_path = PROJECT_ROOT / "input" / "Systematic Theology.pdf"
phase1_dir = PROJECT_ROOT / "phase1-validation"
phase2_dir = PROJECT_ROOT / "phase2-extraction"
pipeline_json = PROJECT_ROOT / "pipeline.json"

# Check if PDF exists
if not pdf_path.exists():
    print(f"❌ ERROR: PDF not found at {pdf_path}")
    print("\nPlease ensure the PDF is in the input folder.")
    sys.exit(1)

print(f"\n✓ Found PDF: {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")

# Step 1: Run Phase 1 (Validation & Classification)
print("\n" + "=" * 80)
print("STEP 1: PHASE 1 - VALIDATION & CLASSIFICATION")
print("=" * 80)

phase1_cmd = [
    "poetry", "run", "python", "-m", "phase1_validation.cli",
    "--file", str(pdf_path)
]

print(f"\nRunning: {' '.join(phase1_cmd)}")
print(f"Working directory: {phase1_dir}\n")

try:
    result = subprocess.run(
        phase1_cmd,
        cwd=str(phase1_dir),
        capture_output=True,
        text=True,
        timeout=60
    )
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"\n❌ Phase 1 failed with return code {result.returncode}")
        sys.exit(1)
    
    print("\n✓ Phase 1 completed successfully")
    
except subprocess.TimeoutExpired:
    print("❌ Phase 1 timed out (>60s)")
    sys.exit(1)
except Exception as e:
    print(f"❌ Phase 1 error: {e}")
    sys.exit(1)

# Check pipeline.json for file_id
print("\n" + "=" * 80)
print("CHECKING PIPELINE.JSON FOR FILE_ID")
print("=" * 80)

try:
    with open(pipeline_json, 'r') as f:
        data = json.load(f)
    
    if 'phase1' not in data or 'files' not in data['phase1']:
        print("❌ No Phase 1 data in pipeline.json")
        sys.exit(1)
    
    # Find the file_id (might be sanitized filename)
    file_id = None
    for fid, fdata in data['phase1']['files'].items():
        file_path_in_json = fdata.get('file_path', '')
        if 'Systematic Theology' in file_path_in_json or 'Systematic' in fid:
            file_id = fid
            classification = fdata.get('classification', 'unknown')
            print(f"\n✓ Found file_id: {file_id}")
            print(f"  Classification: {classification}")
            break
    
    if not file_id:
        print("❌ Could not find Systematic Theology in Phase 1 output")
        print("\nFiles in Phase 1:")
        for fid in data['phase1']['files'].keys():
            print(f"  - {fid}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error reading pipeline.json: {e}")
    sys.exit(1)

# Step 2: Run Phase 2 (Text Extraction with pypdf fix)
print("\n" + "=" * 80)
print("STEP 2: PHASE 2 - TEXT EXTRACTION (WITH PYPDF FIX)")
print("=" * 80)

# First, check if pypdf is installed
print("\nChecking if pypdf is installed...")
check_pypdf = subprocess.run(
    ["poetry", "run", "python", "-c", "import pypdf; print('pypdf installed')"],
    cwd=str(phase2_dir),
    capture_output=True,
    text=True
)

if "pypdf installed" not in check_pypdf.stdout:
    print("⚠️  pypdf not installed. Installing now...")
    install_result = subprocess.run(
        ["poetry", "add", "pypdf"],
        cwd=str(phase2_dir),
        capture_output=True,
        text=True
    )
    if install_result.returncode == 0:
        print("✓ pypdf installed successfully")
    else:
        print("⚠️  Could not install pypdf automatically. Install manually with:")
        print("   cd phase2-extraction")
        print("   poetry add pypdf")
else:
    print("✓ pypdf already installed")

phase2_cmd = [
    "poetry", "run", "python", "-m", "phase2_extraction.extraction",
    "--file_id", file_id,
    "--file", str(pdf_path)
]

print(f"\nRunning: {' '.join(phase2_cmd)}")
print(f"Working directory: {phase2_dir}\n")

try:
    result = subprocess.run(
        phase2_cmd,
        cwd=str(phase2_dir),
        capture_output=True,
        text=True,
        timeout=180  # 3 minutes for extraction
    )
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"\n❌ Phase 2 failed with return code {result.returncode}")
        sys.exit(1)
    
    print("\n✓ Phase 2 completed successfully")
    
except subprocess.TimeoutExpired:
    print("❌ Phase 2 timed out (>3min)")
    sys.exit(1)
except Exception as e:
    print(f"❌ Phase 2 error: {e}")
    sys.exit(1)

# Step 3: Verify extraction quality
print("\n" + "=" * 80)
print("STEP 3: VERIFY EXTRACTION QUALITY")
print("=" * 80)

try:
    with open(pipeline_json, 'r') as f:
        data = json.load(f)
    
    if 'phase2' not in data or 'files' not in data['phase2']:
        print("❌ No Phase 2 data in pipeline.json")
        sys.exit(1)
    
    phase2_data = data['phase2']['files'].get(file_id)
    if not phase2_data:
        print(f"❌ No Phase 2 data for file_id: {file_id}")
        sys.exit(1)
    
    print(f"\n📊 Extraction Metrics:")
    print(f"   Tool used: {phase2_data.get('tool_used', 'unknown')}")
    print(f"   Status: {phase2_data.get('status', 'unknown')}")
    print(f"   Yield: {phase2_data.get('yield_pct', 0):.2f}%")
    print(f"   Gibberish score: {phase2_data.get('gibberish_score', 'N/A')}")
    print(f"   Perplexity: {phase2_data.get('perplexity', 'N/A')}")
    print(f"   Language: {phase2_data.get('language', 'unknown')} (confidence: {phase2_data.get('lang_confidence', 0):.2f})")
    
    extracted_path = phase2_data.get('extracted_text_path', '')
    if extracted_path:
        print(f"   Output: {extracted_path}")
        
        # Check if the file is readable
        if Path(extracted_path).exists():
            with open(extracted_path, 'r', encoding='utf-8') as f:
                sample = f.read(500)
            
            print(f"\n📄 First 500 characters:")
            print("-" * 80)
            print(sample)
            print("-" * 80)
            
            # Quick quality check
            gibberish = phase2_data.get('gibberish_score', 1.0)
            perplexity = phase2_data.get('perplexity', 0.0)
            
            print(f"\n🎯 QUALITY ASSESSMENT:")
            if gibberish > 0.7:
                print("   ❌ HIGH GIBBERISH - Extraction failed")
                print("      Next steps:")
                print("      1. Try the test_extraction_methods.py script")
                print("      2. Check if PDF is protected/encrypted")
                print("      3. May need OCR or manual extraction")
            elif perplexity < 0.5:
                print("   ⚠️  LOW PERPLEXITY - May have quality issues")
            else:
                print("   ✓ LOOKS GOOD - Readable text extracted")
        else:
            print(f"   ⚠️  Extracted file not found at: {extracted_path}")
    
    if phase2_data.get('errors'):
        print(f"\n⚠️  Errors encountered:")
        for error in phase2_data['errors']:
            print(f"      - {error}")

except Exception as e:
    print(f"❌ Error verifying extraction: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✓ PROCESSING COMPLETE")
print("=" * 80)
print("\nSystematic Theology is now properly tracked in pipeline.json")
print("You can proceed to Phase 3 (Chunking) or use Phase 6 orchestrator.")
