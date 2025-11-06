#!/usr/bin/env python3
"""
📊 PHASE 2 STATUS REPORT
Shows what's been done and what needs to happen next
"""
from pathlib import Path
import json

print("=" * 80)
print("PHASE 2 EXTRACTION - STATUS REPORT")
print("=" * 80)

# Check pipeline.json
pipeline_file = Path("pipeline.json")
if pipeline_file.exists():
    with open(pipeline_file, 'r') as f:
        pipeline = json.load(f)
    phase2 = pipeline.get("phase2", {})
    files_processed = phase2.get("files", {})
    
    print(f"\n📋 Pipeline Status:")
    print(f"   Files in pipeline.json: {len(files_processed)}")
    for file_id, data in files_processed.items():
        status = data.get("status", "unknown")
        tool = data.get("tool_used", "unknown")
        print(f"\n   📄 {file_id}")
        print(f"      Status: {status}")
        print(f"      Tool: {tool}")
        print(f"      Yield: {data.get('yield_pct', 0):.1f}%")
        if data.get("errors"):
            print(f"      ⚠️  Errors: {len(data['errors'])}")
            for err in data["errors"][:3]:  # Show first 3 errors
                print(f"         - {err}")
else:
    print("\n⚠️  No pipeline.json found!")
    phase2 = {}
    files_processed = {}

# Check for test extraction files
print(f"\n{'=' * 80}")
print("🧪 TEST EXTRACTIONS (Not in Pipeline)")
print("=" * 80)

test_files = [
    "Systematic_Theology_multipass.txt",
    "Systematic_Theology_multipass_TTS_READY.txt", 
    "Systematic_Theology_consensus.txt",
]

found_tests = []
for filename in test_files:
    filepath = Path(filename)
    if filepath.exists():
        size_mb = filepath.stat().st_size / 1024 / 1024
        found_tests.append(filename)
        print(f"\n✓ {filename}")
        print(f"  Size: {size_mb:.2f} MB")

if not found_tests:
    print("\n⚠️  No test extractions found")

# Check extracted_text folder
print(f"\n{'=' * 80}")
print("📁 EXTRACTED TEXT FOLDER")
print("=" * 80)

extracted_dir = Path("extracted_text")
if extracted_dir.exists():
    extracted_files = list(extracted_dir.glob("*.txt"))
    print(f"\nFound {len(extracted_files)} extracted files:")
    for f in extracted_files:
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  - {f.name} ({size_mb:.2f} MB)")
else:
    print("\n⚠️  extracted_text folder not found!")

# Check for Systematic Theology PDF
print(f"\n{'=' * 80}")
print("📖 SYSTEMATIC THEOLOGY STATUS")
print("=" * 80)

sys_theo_pdf = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\input\Systematic Theology.pdf")
if sys_theo_pdf.exists():
    print(f"\n✓ PDF found: {sys_theo_pdf.name}")
    print(f"  Size: {sys_theo_pdf.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Check if it's in pipeline
    if "Systematic_Theology" in files_processed or "Systematic Theology" in files_processed:
        print(f"  ✓ IN PIPELINE (Phase 2 complete)")
    else:
        print(f"  ⚠️  NOT IN PIPELINE (needs Phase 2 processing)")
    
    # Check if test extractions exist
    if found_tests:
        print(f"  ✓ Test extractions exist: {len(found_tests)}")
        print(f"    → These are standalone tests, not in the pipeline")
else:
    print(f"\n❌ PDF not found!")

# RECOMMENDATIONS
print(f"\n{'=' * 80}")
print("💡 NEXT STEPS")
print("=" * 80)

if found_tests:
    print("\n1️⃣ VERIFY TEST EXTRACTION QUALITY:")
    print("   python verify_extraction_quality.py")
    print("")
    print("   This will show you the quality of your test extractions.")
    
    print("\n2️⃣ IF QUALITY IS GOOD, INTEGRATE INTO PIPELINE:")
    print("   Option A: Copy best extraction to extracted_text folder")
    print("   Option B: Update extraction.py to use multi_pass_extractor.py")
    print("   Option C: Run Phase 2 through Phase 6 orchestrator")
    
    print("\n3️⃣ PROCEED TO PHASE 3 (CHUNKING):")
    print("   cd ../phase3-chunking")
    print("   poetry run python -m phase3_chunking.cli --file_id Systematic_Theology")

else:
    print("\n1️⃣ RUN TEST EXTRACTION:")
    print("   python test_all_extraction_methods.py")
    print("")
    print("   This will test Multi-Pass and Consensus extraction methods.")
    
    print("\n2️⃣ VERIFY QUALITY:")
    print("   python verify_extraction_quality.py")
    
    print("\n3️⃣ IF GOOD, INTEGRATE INTO PIPELINE")

# Known Issues
print(f"\n{'=' * 80}")
print("⚠️  KNOWN ISSUES")
print("=" * 80)

issues_found = []

# Check for language detection problems
for file_id, data in files_processed.items():
    if data.get("language") == "unknown" or data.get("lang_confidence", 0) < 0.5:
        issues_found.append(f"Language detection failed for {file_id}")

# Check for low yield
for file_id, data in files_processed.items():
    if data.get("yield_pct", 0) < 50:
        issues_found.append(f"Low text yield ({data['yield_pct']:.1f}%) for {file_id}")

if issues_found:
    print("")
    for issue in issues_found:
        print(f"⚠️  {issue}")
    print("\nThese may indicate extraction problems that need investigation.")
else:
    print("\n✅ No critical issues detected!")

print("\n" + "=" * 80)
print("END OF REPORT")
print("=" * 80)
