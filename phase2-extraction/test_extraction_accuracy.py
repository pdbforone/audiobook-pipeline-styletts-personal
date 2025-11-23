#!/usr/bin/env python3
"""
Test multiple extraction methods on same PDF pages for accuracy comparison.

Extracts same pages with different methods and compares:
- Which method produces most text
- Which method has best quality
- Which method is most accurate

This helps choose the best extraction method for TTS.
"""
import sys
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from pypdf import PdfReader

    PYPDF = True
except ImportError:
    PYPDF = False

try:
    import pdfplumber

    PDFPLUMBER = True
except ImportError:
    PDFPLUMBER = False

try:
    import pymupdf as fitz

    PYMUPDF = True
except ImportError:
    PYMUPDF = False


def extract_page_pypdf(pdf_path, page_num):
    """Extract with pypdf."""
    if not PYPDF:
        return None
    try:
        reader = PdfReader(pdf_path)
        if page_num < len(reader.pages):
            return reader.pages[page_num].extract_text()
    except Exception as e:
        return f"ERROR: {e}"
    return None


def extract_page_pdfplumber(pdf_path, page_num):
    """Extract with pdfplumber."""
    if not PDFPLUMBER:
        return None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < len(pdf.pages):
                return pdf.pages[page_num].extract_text()
    except Exception as e:
        return f"ERROR: {e}"
    return None


def extract_page_pymupdf(pdf_path, page_num):
    """Extract with PyMuPDF."""
    if not PYMUPDF:
        return None
    try:
        doc = fitz.open(pdf_path)
        if page_num < len(doc):
            text = doc[page_num].get_text()
            doc.close()
            return text
    except Exception as e:
        return f"ERROR: {e}"
    return None


def score_quality(text):
    """Quick quality score for extracted text."""
    if not text or text.startswith("ERROR"):
        return 0.0

    score = 1.0

    # Check for replacement characters
    if "�" in text:
        score -= 0.5

    # Check alphabetic ratio
    alpha_ratio = (
        sum(1 for c in text if c.isalpha()) / len(text) if text else 0
    )
    if alpha_ratio < 0.6:
        score -= 0.3

    # Check for common words
    text_lower = text.lower()
    common = sum(
        1 for w in ["the", "and", "of", "to", "a"] if f" {w} " in text_lower
    )
    if common < 3:
        score -= 0.2

    # Check for multi-spaces
    multi_spaces = len(re.findall(r"  +", text))
    if multi_spaces > 20:
        score -= 0.2

    return max(0.0, score)


def compare_extraction_methods(pdf_path, page_nums):
    """Compare all methods on specific pages."""

    print("=" * 80)
    print("EXTRACTION METHOD COMPARISON")
    print("=" * 80)
    print(f"\nPDF: {Path(pdf_path).name}")
    print(f"Testing pages: {', '.join(str(p+1) for p in page_nums)}")

    methods = {
        "pypdf": extract_page_pypdf,
        "pdfplumber": extract_page_pdfplumber,
        "pymupdf": extract_page_pymupdf,
    }

    available_methods = [
        name
        for name, func in methods.items()
        if (name == "pypdf" and PYPDF)
        or (name == "pdfplumber" and PDFPLUMBER)
        or (name == "pymupdf" and PYMUPDF)
    ]

    if not available_methods:
        print("\n❌ No extraction methods available!")
        print("Install at least one: poetry add pypdf pdfplumber pymupdf")
        return

    print(f"Available methods: {', '.join(available_methods)}\n")

    results = {method: {} for method in available_methods}

    for page_num in page_nums:
        print(f"\n{'='*80}")
        print(f"PAGE {page_num + 1}")
        print(f"{'='*80}")

        for method_name in available_methods:
            print(f"\nExtracting with {method_name}...")
            text = methods[method_name](pdf_path, page_num)

            if text and not text.startswith("ERROR"):
                length = len(text)
                quality = score_quality(text)
                results[method_name][page_num] = {
                    "text": text,
                    "length": length,
                    "quality": quality,
                }

                print(f"  Length: {length:,} chars")
                print(f"  Quality: {quality:.2f}")
                print(f"  Preview: {text[:150]}...")
            else:
                print(f"  ❌ Failed: {text if text else 'No text'}")
                results[method_name][page_num] = None

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    for method_name in available_methods:
        successful = sum(
            1 for v in results[method_name].values() if v is not None
        )
        if successful > 0:
            avg_length = (
                sum(v["length"] for v in results[method_name].values() if v)
                / successful
            )
            avg_quality = (
                sum(v["quality"] for v in results[method_name].values() if v)
                / successful
            )

            print(f"\n{method_name}:")
            print(f"  Success rate: {successful}/{len(page_nums)}")
            print(f"  Avg length: {avg_length:,.0f} chars")
            print(f"  Avg quality: {avg_quality:.2f}")

    # Recommendation
    print(f"\n{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}")

    best_quality = max(
        available_methods,
        key=lambda m: sum(v["quality"] for v in results[m].values() if v)
        / max(1, sum(1 for v in results[m].values() if v)),
    )

    best_length = max(
        available_methods,
        key=lambda m: sum(v["length"] for v in results[m].values() if v)
        / max(1, sum(1 for v in results[m].values() if v)),
    )

    print(f"\nBest quality: {best_quality}")
    print(f"Best length: {best_length}")

    if best_quality == best_length:
        print(f"\n✅ RECOMMENDED: {best_quality} (best quality & length)")
    else:
        print("\n⚠️  Trade-off detected:")
        print(f"   - Use {best_quality} for quality")
        print(f"   - Use {best_length} for completeness")


def test_full_document(pdf_path):
    """Quick test on beginning, middle, end pages."""
    try:
        if PYMUPDF:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
        elif PYPDF:
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
        else:
            print("❌ Cannot determine page count")
            return

        # Test beginning, middle, end
        test_pages = [
            0,  # First page
            page_count // 2,  # Middle page
            page_count - 1,  # Last page
        ]

        print(f"\nTesting {page_count} page document")
        print(f"Sample pages: 1, {page_count//2 + 1}, {page_count}")

        compare_extraction_methods(pdf_path, test_pages)

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    pdf_path = PROJECT_ROOT / "input" / "Systematic Theology.pdf"

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    print("=" * 80)
    print("EXTRACTION ACCURACY TEST")
    print("=" * 80)
    print("\nThis will test different extraction methods on sample pages")
    print("and show which produces the most accurate results.\n")

    # Check available methods
    print("Available extraction methods:")
    if PYPDF:
        print("  ✓ pypdf")
    else:
        print("  ✗ pypdf (install: poetry add pypdf)")

    if PDFPLUMBER:
        print("  ✓ pdfplumber")
    else:
        print("  ✗ pdfplumber (install: poetry add pdfplumber)")

    if PYMUPDF:
        print("  ✓ pymupdf")
    else:
        print("  ✗ pymupdf (install: poetry add pymupdf)")

    if not (PYPDF or PDFPLUMBER or PYMUPDF):
        print("\n❌ No extraction methods available!")
        print("Install at least one with poetry")
        sys.exit(1)

    print("\nTest options:")
    print("1. Quick test (beginning, middle, end)")
    print("2. Custom page numbers")
    print("3. First 10 pages")

    choice = input("\nSelect option (1-3): ").strip()

    if choice == "1":
        test_full_document(str(pdf_path))
    elif choice == "2":
        pages_str = input(
            "Enter page numbers (comma-separated, e.g. 1,5,10): "
        ).strip()
        try:
            page_nums = [int(p.strip()) - 1 for p in pages_str.split(",")]
            compare_extraction_methods(str(pdf_path), page_nums)
        except ValueError:
            print("❌ Invalid page numbers")
    elif choice == "3":
        compare_extraction_methods(str(pdf_path), list(range(10)))
    else:
        print("❌ Invalid option")
