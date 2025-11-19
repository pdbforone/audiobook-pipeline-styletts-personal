#!/usr/bin/env python3
"""
FIXED: Properly process Systematic Theology.pdf through Phase 1 → Phase 2
"""
import subprocess
import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]

print("=" * 80)
print("SYSTEMATIC THEOLOGY - PROPER PIPELINE PROCESSING (FIXED)")
print("=" * 80)

# Paths
pdf_path = PROJECT_ROOT / "input" / "Systematic Theology.pdf"
phase1_dir = PROJECT_ROOT / "phase1-validation"
phase2_dir = PROJECT_ROOT / "phase2-extraction"
pipeline_json_phase1 = phase1_dir / "pipeline.json"
pipeline_json_phase2 = phase2_dir / "pipeline.json"

# Check if PDF exists
if not pdf_path.exists():
    print(f"❌ ERROR: PDF not found at {pdf_path}")
    sys.exit(1)

print(f"\n✓ Found PDF: {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")

# Step 1: Run Phase 1 (Validation & Classification)
print("\n" + "=" * 80)
print("STEP 1: PHASE 1 - VALIDATION & CLASSIFICATION")
print("=" * 80)

phase1_cmd = [
    "poetry", "run", "python", "-m", "phase1_validation.validation",
    "--file", str(pdf_path),
    "--json_path", str(pipeline_json_phase1)
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
    with open(pipeline_json_phase1, 'r') as f:
        data = json.load(f)
    
    if 'phase1' not in data or 'files' not in data['phase1']:
        print("❌ No Phase 1 data in pipeline.json")
        sys.exit(1)
    
    # Find the file_id (sanitized from filename)
    file_id = None
    for fid, fdata in data['phase1']['files'].items():
        # Phase 1 uses stem (filename without extension) as file_id
        if 'Systematic' in fid or fid == pdf_path.stem:
            file_id = fid
            classification = fdata.get('classification', 'unknown')
            print(f"\n✓ Found file_id: {file_id}")
            print(f"  Classification: {classification}")
            print(f"  Hash: {fdata.get('hash', 'N/A')[:16]}...")
            print(f"  Repair status: {fdata.get('repair_status', 'N/A')}")
            
            # CRITICAL FIX: Add file_path to Phase 1 data if missing
            if 'file_path' not in fdata:
                print(f"\n⚠️  file_path missing from Phase 1 data - adding it now")
                fdata['file_path'] = str(pdf_path)
                with open(pipeline_json_phase1, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"✓ Added file_path: {pdf_path}")
            
            break
    
    if not file_id:
        print("❌ Could not find Systematic Theology in Phase 1 output")
        print("\nFiles in Phase 1:")
        for fid in data['phase1']['files'].keys():
            print(f"  - {fid}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error reading pipeline.json: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Run Phase 2 (Text Extraction with pypdf fix)
print("\n" + "=" * 80)
print("STEP 2: PHASE 2 - TEXT EXTRACTION (WITH PYPDF FIX)")
print("=" * 80)

phase2_cmd = [
    "poetry", "run", "python", "-m", "phase2_extraction.extraction",
    "--file_id", file_id,
    "--file", str(pdf_path),
    "--json_path", str(pipeline_json_phase2)
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
        print("\nTroubleshooting:")
        print("  1. Check if pypdf is installed: poetry run pip list | findstr pypdf")
        print("  2. Try running test_extraction_methods.py to test all methods")
        print("  3. Check the Phase 2 error logs above")
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
    with open(pipeline_json_phase2, 'r') as f:
        data = json.load(f)
    
    if 'phase2' not in data or 'files' not in data['phase2']:
        print("❌ No Phase 2 data in pipeline.json")
        sys.exit(1)
    
    phase2_data = data['phase2']['files'].get(file_id)
    if not phase2_data:
        print(f"❌ No Phase 2 data for file_id: {file_id}")
        print("\nFiles in Phase 2:")
        for fid in data['phase2']['files'].keys():
            print(f"  - {fid}")
        sys.exit(1)
    
    print(f"\n📊 Extraction Metrics:")
    print(f"   Tool used: {phase2_data.get('tool_used', 'unknown')}")
    print(f"   Status: {phase2_data.get('status', 'unknown')}")
    print(f"   Yield: {phase2_data.get('yield_pct', 0):.2f}%")
    print(f"   Gibberish score: {phase2_data.get('gibberish_score', 'N/A'):.3f}")
    print(f"   Perplexity: {phase2_data.get('perplexity', 'N/A'):.3f}")
    print(f"   Language: {phase2_data.get('language', 'unknown')} (confidence: {phase2_data.get('lang_confidence', 0):.3f})")
    
    extracted_path = phase2_data.get('extracted_text_path', '')
    if extracted_path:
        # Handle relative paths
        if not Path(extracted_path).is_absolute():
            extracted_path = phase2_dir / extracted_path
        else:
            extracted_path = Path(extracted_path)
            
        print(f"   Output: {extracted_path}")
        
        # Check if the file is readable
        if extracted_path.exists():
            with open(extracted_path, 'r', encoding='utf-8') as f:
                sample = f.read(500)
            
            print(f"\n📄 First 500 characters:")
            print("-" * 80)
            print(sample)
            print("-" * 80)
            
            # Quality assessment
            gibberish = phase2_data.get('gibberish_score', 1.0)
            perplexity = phase2_data.get('perplexity', 0.0)
            lang_conf = phase2_data.get('lang_confidence', 0.0)
            
            print(f"\n🎯 QUALITY ASSESSMENT:")
            
            if gibberish > 0.7:
                print("   ❌ HIGH GIBBERISH (>0.7) - Extraction likely failed")
                print("      Text is not readable. Possible causes:")
                print("      - PDF uses custom fonts that pypdf can't decode")
                print("      - PDF is encrypted or DRM-protected")
                print("      - PDF contains scanned images (needs OCR)")
                print("\n      Next steps:")
                print("      1. Run: python test_extraction_methods.py")
                print("      2. Check if PDF is protected in Adobe Reader")
                print("      3. Try OCR extraction (Phase 2 with --classification=scanned)")
            elif gibberish > 0.5:
                print("   ⚠️  MODERATE GIBBERISH (0.5-0.7) - Some quality issues")
                print("      Text may be partially readable but has encoding problems")
            elif perplexity < 0.5:
                print("   ⚠️  LOW PERPLEXITY (<0.5) - Low vocabulary diversity")
                print("      May indicate repeated text or extraction artifacts")
            elif lang_conf < 0.8:
                print("   ⚠️  LOW LANGUAGE CONFIDENCE - May not be English or mixed content")
            else:
                print("   ✅ EXCELLENT QUALITY - Text extraction successful!")
                print("      - Gibberish score < 0.5 (readable)")
                print("      - Perplexity > 0.5 (good vocabulary)")
                print("      - Language confidence > 0.8 (clearly English)")
                print("\n   Ready for Phase 3 (Chunking)!")
        else:
            print(f"   ❌ Extracted file not found at: {extracted_path}")
    
    if phase2_data.get('errors'):
        print(f"\n⚠️  Warnings/Errors:")
        for error in phase2_data['errors']:
            print(f"      - {error}")

except Exception as e:
    print(f"❌ Error verifying extraction: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✓ PROCESSING COMPLETE")
print("=" * 80)
print(f"\nSystematic Theology is now tracked in:")
print(f"  Phase 1: {pipeline_json_phase1}")
print(f"  Phase 2: {pipeline_json_phase2}")
print("\nNext steps:")
print("  - If quality is good: Proceed to Phase 3 (Chunking)")
print("  - If quality is poor: Run test_extraction_methods.py for diagnosis")
