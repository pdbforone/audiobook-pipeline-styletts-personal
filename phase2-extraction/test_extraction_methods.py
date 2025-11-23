#!/usr/bin/env python3
"""
Test different PDF extraction methods for Systematic Theology.

Pytest imports every ``test_*.py`` module, and this utility script previously
terminated the test session when it could not find the personal PDF path.
Wrapping the logic inside ``main`` keeps the CLI UX intact while making pytest
collection safe.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF_PATH = PROJECT_ROOT / "input" / "Systematic Theology.pdf"


def main(pdf_path: Path = DEFAULT_PDF_PATH) -> int:
    # Try importing all extraction libraries lazily so pytest imports stay quiet.
    try:
        import pdfplumber  # type: ignore

        print("✓ pdfplumber available")
    except ImportError:
        print("✗ pdfplumber not available")
        pdfplumber = None
    try:
        import pymupdf as fitz  # type: ignore

        print("✓ PyMuPDF (fitz) available")
    except ImportError:
        print("✗ PyMuPDF not available")
        fitz = None
    try:
        from pypdf import PdfReader  # type: ignore

        print("✓ pypdf available")
    except ImportError:
        print("✗ pypdf not available - try: pip install pypdf")
        PdfReader = None
    try:
        from unstructured.partition.auto import partition  # type: ignore

        print("✓ unstructured available")
    except ImportError:
        print("✗ unstructured not available")
        partition = None

    if not pdf_path.exists():
        print(f"\n❌ ERROR: PDF not found at {pdf_path}")
        return 1

    print(f"\n📖 Testing extraction from: {pdf_path.name}")
    print("=" * 80)

    results = {}

    # Method 1: pdfplumber
    if "pdfplumber" in locals() and pdfplumber:
        print("\n🔧 METHOD 1: pdfplumber")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for i, page in enumerate(pdf.pages[:2]):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            results["pdfplumber"] = text
            sample = text[:500]
            print(f"   Length: {len(text)} chars")
            print(f"   First 500 chars:\n{sample}")
            print(
                f"   Looks readable: {'✓' if any(word in sample.lower() for word in ['the', 'and', 'of', 'to', 'a']) else '✗'}"
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["pdfplumber"] = None

    # Method 2: PyMuPDF basic
    if "fitz" in locals() and fitz:
        print("\n🔧 METHOD 2: PyMuPDF (basic get_text)")
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page_num in range(min(2, len(doc))):
                text += doc[page_num].get_text()
            doc.close()
            results["pymupdf_basic"] = text
            sample = text[:500]
            print(f"   Length: {len(text)} chars")
            print(f"   First 500 chars:\n{sample}")
            print(
                f"   Looks readable: {'✓' if any(word in sample.lower() for word in ['the', 'and', 'of', 'to', 'a']) else '✗'}"
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["pymupdf_basic"] = None

    # Method 3: PyMuPDF with layout preservation
    if "fitz" in locals() and fitz:
        print("\n🔧 METHOD 3: PyMuPDF (with layout='blocks')")
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page_num in range(min(2, len(doc))):
                text += doc[page_num].get_text("blocks")
                blocks = doc[page_num].get_text("blocks")
                for block in blocks:
                    if len(block) >= 5:
                        text += block[4]
            doc.close()
            results["pymupdf_blocks"] = text
            sample = text[:500]
            print(f"   Length: {len(text)} chars")
            print(f"   First 500 chars:\n{sample}")
            print(
                f"   Looks readable: {'✓' if any(word in sample.lower() for word in ['the', 'and', 'of', 'to', 'a']) else '✗'}"
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["pymupdf_blocks"] = None

    # Method 4: PyMuPDF with text extraction dict
    if "fitz" in locals() and fitz:
        print("\n🔧 METHOD 4: PyMuPDF (with rawdict for font info)")
        try:
            doc = fitz.open(pdf_path)
            text = ""
            page = doc[0]
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text += span.get("text", "") + " "
                    text += "\n"
            doc.close()
            results["pymupdf_dict"] = text
            sample = text[:500]
            print(f"   Length: {len(text)} chars")
            print(f"   First 500 chars:\n{sample}")
            print(
                f"   Looks readable: {'✓' if any(word in sample.lower() for word in ['the', 'and', 'of', 'to', 'a']) else '✗'}"
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["pymupdf_dict"] = None

    # Method 5: pypdf
    if "PdfReader" in locals() and PdfReader:
        print("\n🔧 METHOD 5: pypdf (PyPDF2 successor)")
        try:
            reader = PdfReader(str(pdf_path))
            text = ""
            for page_num in range(min(2, len(reader.pages))):
                text += reader.pages[page_num].extract_text()
            results["pypdf"] = text
            sample = text[:500]
            print(f"   Length: {len(text)} chars")
            print(f"   First 500 chars:\n{sample}")
            print(
                f"   Looks readable: {'✓' if any(word in sample.lower() for word in ['the', 'and', 'of', 'to', 'a']) else '✗'}"
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["pypdf"] = None

    # Method 6: unstructured
    if "partition" in locals() and partition:
        print("\n🔧 METHOD 6: unstructured")
        try:
            elements = partition(filename=str(pdf_path), strategy="fast")
            text = "\n".join(str(el) for el in elements[:10])
            results["unstructured"] = text
            sample = text[:500]
            print(f"   Length: {len(text)} chars")
            print(f"   First 500 chars:\n{sample}")
            print(
                f"   Looks readable: {'✓' if any(word in sample.lower() for word in ['the', 'and', 'of', 'to', 'a']) else '✗'}"
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["unstructured"] = None

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    for method, text in results.items():
        if text and len(text) > 100:
            words = text[:1000].lower().split()
            common_words = sum(
                word
                in [
                    "the",
                    "and",
                    "of",
                    "to",
                    "a",
                    "in",
                    "is",
                    "that",
                    "for",
                    "it",
                ]
                for word in words
            )
            readable = "✓ READABLE" if common_words > 5 else "✗ GIBBERISH"
            print(f"   {method:20s}: {len(text):>8,} chars | {readable}")
        elif text:
            print(f"   {method:20s}: {len(text):>8,} chars | ⚠️  TOO SHORT")
        else:
            print(f"   {method:20s}:    FAILED")

    print("\n💡 RECOMMENDATION:")
    readable_methods = [
        m
        for m, t in results.items()
        if t
        and len(t) > 100
        and sum(
            w in ["the", "and", "of", "to", "a"]
            for w in t[:1000].lower().split()
        )
        > 5
    ]
    if readable_methods:
        print(f"   Use: {readable_methods[0]}")
        print("   This method produced readable English text.")
    else:
        print("   ⚠️  None of the methods produced readable text!")
        print("   This PDF may have:")
        print("      - Custom font encoding that requires font mapping")
        print("      - Encryption or DRM protection")
        print("      - Scanned images instead of text (needs OCR)")
        print("\n   Next steps:")
        print(
            "      1. Try opening PDF in Adobe Reader and check Document Properties → Security"
        )
        print("      2. Check if text is selectable in PDF viewer")
        print("      3. May need to use OCR (EasyOCR/Tesseract) as fallback")

    return 0


if __name__ == "__main__":
    sys.exit(main())
