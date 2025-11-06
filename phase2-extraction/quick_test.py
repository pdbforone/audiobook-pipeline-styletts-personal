#!/usr/bin/env python3
"""
QUICK TEST - Automatic extraction accuracy verification

Runs both tests automatically and generates a report.
Perfect for quick validation before proceeding to Phase 3.
"""
import subprocess
import sys
from pathlib import Path

def run_test(script_name, test_name):
    """Run a test script and capture output."""
    print(f"\n{'='*80}")
    print(f"RUNNING: {test_name}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⏱️  Test timed out (>60s)")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    print("="*80)
    print("SYSTEMATIC THEOLOGY - QUICK EXTRACTION VERIFICATION")
    print("="*80)
    print("\nThis will automatically:")
    print("  1. Test extraction methods (pypdf, pdfplumber, pymupdf)")
    print("  2. Compare output to PDF input")
    print("  3. Generate accuracy report")
    print("\nEstimated time: 2-3 minutes\n")
    
    input("Press Enter to start...")
    
    # Test 1: Method comparison
    print("\n\n🧪 TEST 1: Extraction Method Comparison")
    print("Testing pypdf, pdfplumber, pymupdf on sample pages...")
    
    test1_success = run_test(
        "test_extraction_accuracy.py",
        "Extraction Method Comparison"
    )
    
    # Test 2: PDF to extracted comparison
    print("\n\n🧪 TEST 2: PDF vs Extracted Text Comparison")
    print("Comparing beginning, middle, and end sections...")
    
    test2_success = run_test(
        "compare_pdf_to_extracted.py",
        "PDF to Extracted Comparison"
    )
    
    # Generate report
    print("\n\n" + "="*80)
    print("📊 TEST REPORT")
    print("="*80)
    
    if test1_success and test2_success:
        print("\n✅ ALL TESTS PASSED")
        print("\nExtraction appears accurate!")
        print("\nNext steps:")
        print("  1. Review output above for any warnings")
        print("  2. Run: python normalize_now.py")
        print("  3. Proceed to Phase 3 (Chunking)")
    elif test1_success:
        print("\n⚠️  Method comparison passed, but manual verification needed")
        print("\nRun interactive comparison:")
        print("  python compare_pdf_to_extracted.py")
    else:
        print("\n❌ TESTS FAILED")
        print("\nTroubleshooting:")
        print("  1. Check if pypdf/pdfplumber/pymupdf installed")
        print("  2. Verify PDF path is correct")
        print("  3. Check extracted text file exists")
        print("  4. Review errors above")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
