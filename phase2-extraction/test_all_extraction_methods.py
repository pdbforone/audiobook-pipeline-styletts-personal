#!/usr/bin/env python3
"""
Test and compare all extraction methods on Systematic Theology
Shows you which approach gives the best TTS-grade quality.
"""
from pathlib import Path
import sys

pdf_path = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\input\Systematic Theology.pdf")

if not pdf_path.exists():
    print(f"❌ PDF not found: {pdf_path}")
    print("Please check the path and try again.")
    sys.exit(1)

print("=" * 80)
print("SYSTEMATIC THEOLOGY - EXTRACTION METHOD COMPARISON")
print("=" * 80)
print(f"File: {pdf_path.name}")
print(f"Size: {pdf_path.stat().st_size / 1024 / 1024:.1f} MB\n")

# Test 1: Multi-Pass Extraction
print("\n" + "=" * 80)
print("TEST 1: MULTI-PASS EXTRACTION (30-60 seconds)")
print("=" * 80)
try:
    from multi_pass_extractor import extract_with_self_correction
    import time
    
    start = time.time()
    text1, meta1 = extract_with_self_correction(str(pdf_path), min_confidence=0.7)
    duration1 = time.time() - start
    
    # Save output
    output1 = Path("Systematic_Theology_multipass.txt")
    with open(output1, 'w', encoding='utf-8') as f:
        f.write(text1)
    
    print(f"\n✅ Multi-Pass Complete ({duration1:.1f}s)")
    print(f"   Saved to: {output1}")
    
except Exception as e:
    print(f"❌ Multi-Pass failed: {e}")
    text1, meta1, duration1, output1 = None, None, 0, None

# Test 2: Consensus Extraction (optional - slower)
print("\n" + "=" * 80)
print("TEST 2: CONSENSUS EXTRACTION (2-5 minutes)")
print("=" * 80)
print("This is slower but more thorough. Run it? (y/n): ", end='')
run_consensus = input().lower().strip() == 'y'

if run_consensus:
    try:
        from consensus_extractor import extract_with_consensus
        import time
        
        start = time.time()
        text2, meta2 = extract_with_consensus(str(pdf_path), min_confidence=0.7, use_ocr_fallback=False)
        duration2 = time.time() - start
        
        # Save output
        output2 = Path("Systematic_Theology_consensus.txt")
        with open(output2, 'w', encoding='utf-8') as f:
            f.write(text2)
        
        print(f"\n✅ Consensus Complete ({duration2:.1f}s)")
        print(f"   Saved to: {output2}")
        
    except Exception as e:
        print(f"❌ Consensus failed: {e}")
        text2, meta2, duration2, output2 = None, None, 0, None
else:
    print("Skipped (can run later if needed)")
    text2, meta2, duration2, output2 = None, None, 0, None

# Test 3: Compare with existing file
print("\n" + "=" * 80)
print("TEST 3: COMPARE WITH EXISTING EXTRACTION")
print("=" * 80)

existing_file = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction\extracted_text\Systematic Theology.txt")
if existing_file.exists():
    with open(existing_file, 'r', encoding='utf-8') as f:
        text_existing = f.read()
    print(f"✓ Found existing extraction: {len(text_existing):,} chars")
else:
    print("⚠️  No existing extraction found")
    text_existing = None

# COMPARISON REPORT
print("\n" + "=" * 80)
print("📊 RESULTS COMPARISON")
print("=" * 80)

results = []

if text1 and meta1:
    results.append({
        "name": "Multi-Pass",
        "confidence": meta1.get("confidence", 0),
        "length": len(text1),
        "status": meta1.get("status", "unknown"),
        "duration": duration1,
        "method": meta1.get("method_used", "unknown"),
        "issues": len(meta1.get("issues", [])),
        "file": output1
    })

if text2 and meta2:
    results.append({
        "name": "Consensus",
        "confidence": meta2.get("confidence", 0),
        "length": len(text2),
        "status": meta2.get("status", "unknown"),
        "duration": duration2,
        "method": "page-by-page voting",
        "issues": len(meta2.get("failed_pages", [])),
        "file": output2
    })

if text_existing:
    results.append({
        "name": "Existing",
        "confidence": "?",
        "length": len(text_existing),
        "status": "unknown",
        "duration": "N/A",
        "method": "unknown",
        "issues": "?",
        "file": existing_file
    })

# Print comparison table
print("\n| Method     | Confidence | Length    | Status  | Duration | Issues | File |")
print("|------------|------------|-----------|---------|----------|--------|------|")
for r in results:
    conf = f"{r['confidence']:.1%}" if isinstance(r['confidence'], (int, float)) else str(r['confidence'])
    dur = f"{r['duration']:.0f}s" if isinstance(r['duration'], (int, float)) else str(r['duration'])
    print(f"| {r['name']:10s} | {conf:10s} | {r['length']:>9,} | {r['status']:7s} | {dur:8s} | {str(r['issues']):6s} | {r['file'].name if r['file'] else 'N/A'} |")

# Recommendation
print("\n" + "=" * 80)
print("💡 RECOMMENDATION")
print("=" * 80)

if text1 and meta1:
    if meta1.get("confidence", 0) >= 0.85:
        print("\n✅ Multi-Pass extraction is EXCELLENT quality")
        print(f"   Confidence: {meta1['confidence']:.1%}")
        print(f"   Status: {meta1['status']}")
        print(f"   Method: {meta1['method_used']}")
        print(f"\n   ✓ Use this for Phase 3!")
        print(f"   ✓ File: {output1}")
    elif meta1.get("confidence", 0) >= 0.7:
        print("\n⚠️  Multi-Pass extraction is ACCEPTABLE quality")
        print(f"   Confidence: {meta1['confidence']:.1%}")
        print(f"   Issues: {len(meta1.get('issues', []))}")
        if not run_consensus:
            print(f"\n   Consider running Consensus extraction for better quality:")
            print(f"   python consensus_extractor.py \"{pdf_path}\" 0.8")
    else:
        print("\n❌ Multi-Pass extraction has LOW quality")
        print(f"   Confidence: {meta1['confidence']:.1%}")
        print(f"   Issues: {meta1.get('issues', [])}")
        print(f"\n   Recommended actions:")
        print(f"   1. Run Consensus extraction (slower but better)")
        print(f"   2. Check if PDF is encrypted/protected")
        print(f"   3. May need OCR for scanned content")

if text2 and meta2:
    print(f"\n📊 Consensus Results:")
    print(f"   Confidence: {meta2['confidence']:.1%}")
    print(f"   Failed pages: {len(meta2.get('failed_pages', []))}")
    print(f"   Low confidence pages: {len(meta2.get('low_confidence_pages', []))}")
    if meta2.get("confidence", 0) >= meta1.get("confidence", 0) if meta1 else 0:
        print(f"\n   ✅ Consensus is BETTER than Multi-Pass")
        print(f"   ✓ Use: {output2}")

# Text quality preview
print("\n" + "=" * 80)
print("📄 TEXT QUALITY PREVIEW")
print("=" * 80)

if text1:
    print(f"\nMulti-Pass (first 300 chars):")
    print("-" * 80)
    print(text1[:300])
    print("-" * 80)

if text2:
    print(f"\nConsensus (first 300 chars):")
    print("-" * 80)
    print(text2[:300])
    print("-" * 80)

if text_existing:
    print(f"\nExisting (first 300 chars):")
    print("-" * 80)
    print(text_existing[:300])
    print("-" * 80)

print("\n" + "=" * 80)
print("✅ COMPARISON COMPLETE")
print("=" * 80)
print("\nNext steps:")
print("  1. Review the confidence scores above")
print("  2. Check the output files for quality")
print("  3. If satisfied, integrate into Phase 2 pipeline")
print("  4. Process through Phase 3 (Chunking)")
