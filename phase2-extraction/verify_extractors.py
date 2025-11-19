#!/usr/bin/env python3
"""
Phase 2 Extractor Verification Script

Quick test to verify all extractors are working correctly.
Run this after installation to ensure dependencies are properly installed.

Usage:
    poetry run python verify_extractors.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("Testing Module Imports")
    print("=" * 60)
    
    tests = []
    
    # Core modules
    try:
        from phase2_extraction import ingest
        print("✓ ingest.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ ingest.py: {e}")
        tests.append(False)
    
    try:
        from phase2_extraction import normalize
        print("✓ normalize.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ normalize.py: {e}")
        tests.append(False)
    
    try:
        from phase2_extraction import utils
        print("✓ utils.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ utils.py: {e}")
        tests.append(False)
    
    # Extractors
    try:
        from phase2_extraction.extractors import pdf
        print("✓ extractors/pdf.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ extractors/pdf.py: {e}")
        tests.append(False)
    
    try:
        from phase2_extraction.extractors import docx
        print("✓ extractors/docx.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ extractors/docx.py: {e}")
        tests.append(False)
    
    try:
        from phase2_extraction.extractors import epub
        print("✓ extractors/epub.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ extractors/epub.py: {e}")
        tests.append(False)
    
    try:
        from phase2_extraction.extractors import html
        print("✓ extractors/html.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ extractors/html.py: {e}")
        tests.append(False)
    
    try:
        from phase2_extraction.extractors import txt
        print("✓ extractors/txt.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ extractors/txt.py: {e}")
        tests.append(False)
    
    try:
        from phase2_extraction.extractors import ocr
        print("✓ extractors/ocr.py")
        tests.append(True)
    except ImportError as e:
        print(f"✗ extractors/ocr.py: {e}")
        tests.append(False)
    
    return all(tests)


def test_dependencies():
    """Test that all required dependencies are available."""
    print("\n" + "=" * 60)
    print("Testing Dependencies")
    print("=" * 60)
    
    tests = []
    
    # Core dependencies
    deps = [
        ('pypdf', 'PyPDF - PDF extraction'),
        ('pdfplumber', 'pdfplumber - PDF extraction'),
        ('fitz', 'PyMuPDF - PDF extraction'),
        ('docx', 'python-docx - DOCX extraction'),
        ('ebooklib', 'ebooklib - EPUB extraction'),
        ('bs4', 'BeautifulSoup4 - HTML parsing'),
        ('lxml', 'lxml - HTML parsing'),
        ('easyocr', 'EasyOCR - OCR for scanned PDFs'),
        ('langdetect', 'langdetect - Language detection'),
    ]
    
    for module, description in deps:
        try:
            __import__(module)
            print(f"✓ {description}")
            tests.append(True)
        except ImportError:
            print(f"✗ {description} - NOT INSTALLED")
            tests.append(False)
    
    # Optional dependencies
    print("\nOptional Dependencies:")
    
    optional_deps = [
        ('magic', 'python-magic - File type detection (optional)'),
        ('readability', 'readability-lxml - HTML content extraction (optional)'),
        ('pdf2image', 'pdf2image - OCR support (optional)'),
    ]
    
    for module, description in optional_deps:
        try:
            __import__(module)
            print(f"✓ {description}")
        except ImportError:
            print(f"○ {description} - Not installed (optional)")
    
    return all(tests)


def test_extractors():
    """Test basic extractor functionality."""
    print("\n" + "=" * 60)
    print("Testing Extractor Functions")
    print("=" * 60)
    
    from phase2_extraction.extractors import pdf, docx, epub, html, txt, ocr
    
    # Test that extract functions exist and have correct signature
    extractors = [
        ('PDF', pdf),
        ('DOCX', docx),
        ('EPUB', epub),
        ('HTML', html),
        ('TXT', txt),
        ('OCR', ocr),
    ]
    
    tests = []
    for name, module in extractors:
        try:
            # Check extract function exists
            assert hasattr(module, 'extract'), f"{name}: Missing extract() function"
            
            # Check function signature (should take Path as first arg)
            import inspect
            sig = inspect.signature(module.extract)
            params = list(sig.parameters.keys())
            assert 'path' in params, f"{name}: extract() should have 'path' parameter"
            
            print(f"✓ {name} extractor")
            tests.append(True)
        except AssertionError as e:
            print(f"✗ {name} extractor: {e}")
            tests.append(False)
        except Exception as e:
            print(f"✗ {name} extractor: Unexpected error: {e}")
            tests.append(False)
    
    return all(tests)


def test_utils():
    """Test utility functions."""
    print("\n" + "=" * 60)
    print("Testing Utility Functions")
    print("=" * 60)
    
    from phase2_extraction import utils
    
    required_functions = [
        'merge_phase_state',
        'with_retry',
        'detect_format',
        'calculate_yield',
    ]
    
    tests = []
    for func_name in required_functions:
        if hasattr(utils, func_name):
            print(f"✓ {func_name}()")
            tests.append(True)
        else:
            print(f"✗ {func_name}() - NOT FOUND")
            tests.append(False)
    
    return all(tests)


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("PHASE 2 EXTRACTOR VERIFICATION")
    print("=" * 60)
    print()
    
    results = []
    
    # Test imports
    results.append(("Module Imports", test_imports()))
    
    # Test dependencies
    results.append(("Dependencies", test_dependencies()))
    
    # Test extractors
    results.append(("Extractor Functions", test_extractors()))
    
    # Test utils
    results.append(("Utility Functions", test_utils()))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED")
        print("\nPhase 2 extractors are ready to use!")
        print("\nNext steps:")
        print("  1. Run a test extraction:")
        print("     poetry run python -m phase2_extraction.ingest --file_id test001 --file /path/to/test.pdf")
        print("  2. Check output in extracted_text/ directory")
        print("  3. Review pipeline.json for metrics")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nMissing dependencies? Install with:")
        print("  poetry add python-docx ebooklib beautifulsoup4 lxml easyocr pdf2image pypdf")
        print("\nOn Windows, also run:")
        print("  poetry add python-magic-bin")
        print("  poetry remove python-magic")
        return 1


if __name__ == "__main__":
    sys.exit(main())
