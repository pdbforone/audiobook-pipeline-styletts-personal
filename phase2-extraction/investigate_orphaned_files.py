#!/usr/bin/env python3
"""
Investigate the orphaned Systematic Theology extraction
"""
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
extracted_dir = PROJECT_ROOT / "phase2-extraction" / "extracted_text"
input_dir = PROJECT_ROOT / "input"

print("=" * 80)
print("EXTRACTED TEXT FILES (not tracked in pipeline.json)")
print("=" * 80)

for txt_file in extracted_dir.glob("*.txt"):
    size = txt_file.stat().st_size
    print(f"\n📄 {txt_file.name}")
    print(f"   Size: {size:,} bytes ({size/1024:.1f} KB)")
    print(f"   Modified: {txt_file.stat().st_mtime}")
    
    # Read first 300 chars to check if gibberish
    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            sample = f.read(300)
        
        # Quick gibberish check
        words = sample.split()[:20]
        english_like = sum(w.isalpha() and len(w) > 2 for w in words)
        
        print(f"   First 300 chars: {sample[:100]}...")
        print(f"   English-like words in first 20: {english_like}/20")
        
        if english_like < 10:
            print(f"   ⚠️  LOOKS LIKE GIBBERISH")
        else:
            print(f"   ✓ Looks readable")
    except Exception as e:
        print(f"   ❌ Error reading: {e}")

print("\n" + "=" * 80)
print("SOURCE PDF FILES IN INPUT FOLDER")
print("=" * 80)

if input_dir.exists():
    for pdf_file in input_dir.glob("*.pdf"):
        size = pdf_file.stat().st_size
        print(f"\n📄 {pdf_file.name}")
        print(f"   Size: {size:,} bytes ({size/1024/1024:.1f} MB)")
        print(f"   Path: {pdf_file}")
else:
    print(f"\n❌ Input directory not found: {input_dir}")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("""
To properly process Systematic Theology through the pipeline:

1. Run Phase 1 first (validation & classification):
   cd path\\to\\repo\\phase1-validation
   poetry run python -m phase1_validation.cli --file "path\\to\\repo\\input\\Systematic Theology.pdf"

2. Then run Phase 2 (extraction):
   cd path\\to\\repo\\phase2-extraction
   poetry run python -m phase2_extraction.extraction --file_id "Systematic_Theology" --file "path\\to\\repo\\input\\Systematic Theology.pdf"

3. Or use Phase 6 orchestrator (when implemented) to run all phases

The existing extracted_text/Systematic Theology.txt was created outside the pipeline
and should be regenerated properly to ensure quality and tracking.
""")
