#!/usr/bin/env python3
"""
Compare PDF source to extracted text - Side-by-side verification

This lets you verify extraction accuracy by comparing:
1. Specific pages from PDF
2. Beginning, middle, end sections
3. Random samples
4. Search for specific text

Critical for TTS: We need to ensure we're extracting exactly what's in the PDF.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("⚠️  pypdf not available - install with: poetry add pypdf")

try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("⚠️  pymupdf not available - some features limited")


def read_pdf_page(pdf_path, page_num):
    """Read a specific page from PDF."""
    if PYPDF_AVAILABLE:
        reader = PdfReader(pdf_path)
        if page_num < len(reader.pages):
            return reader.pages[page_num].extract_text()
    elif PYMUPDF_AVAILABLE:
        doc = fitz.open(pdf_path)
        if page_num < len(doc):
            text = doc[page_num].get_text()
            doc.close()
            return text
    return None


def get_pdf_info(pdf_path):
    """Get PDF page count and metadata."""
    if PYMUPDF_AVAILABLE:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        metadata = doc.metadata
        doc.close()
        return page_count, metadata
    elif PYPDF_AVAILABLE:
        reader = PdfReader(pdf_path)
        return len(reader.pages), reader.metadata
    return 0, {}


def read_extracted_section(txt_path, char_start, char_length=2000):
    """Read a section of extracted text."""
    with open(txt_path, 'r', encoding='utf-8') as f:
        f.seek(char_start)
        return f.read(char_length)


def compare_page_to_extracted(pdf_path, txt_path, page_num):
    """Compare a PDF page to the extracted text at corresponding position."""
    print("=" * 80)
    print(f"COMPARISON: PDF Page {page_num + 1}")
    print("=" * 80)
    
    # Read PDF page
    pdf_text = read_pdf_page(pdf_path, page_num)
    if not pdf_text:
        print(f"❌ Could not read page {page_num + 1}")
        return
    
    print(f"\n📄 PDF PAGE {page_num + 1} (first 1000 chars):")
    print("-" * 80)
    print(pdf_text[:1000])
    print("-" * 80)
    print(f"Total length: {len(pdf_text)} chars")
    
    # Estimate position in extracted text (rough)
    # Assuming each page is roughly the same size
    with open(txt_path, 'r', encoding='utf-8') as f:
        f.seek(0, 2)  # End
        total_size = f.tell()
    
    page_count, _ = get_pdf_info(pdf_path)
    estimated_pos = int((page_num / page_count) * total_size)
    
    # Read corresponding section from extracted text
    extracted_section = read_extracted_section(txt_path, estimated_pos, 1000)
    
    print(f"\n📝 EXTRACTED TEXT (around char {estimated_pos:,}):")
    print("-" * 80)
    print(extracted_section)
    print("-" * 80)
    
    # Compare
    print(f"\n🔍 ANALYSIS:")
    
    # Check if some words from PDF appear in extracted
    pdf_words = set(pdf_text[:500].split())
    extracted_words = set(extracted_section.split())
    overlap = len(pdf_words & extracted_words)
    
    print(f"   Word overlap: {overlap} words in common")
    print(f"   PDF page length: {len(pdf_text)} chars")
    print(f"   Extracted section length: {len(extracted_section)} chars")
    
    if overlap > 10:
        print(f"   ✅ Good overlap - extraction seems accurate")
    else:
        print(f"   ⚠️  Low overlap - may not be same section")


def search_in_both(pdf_path, txt_path, search_term):
    """Search for a term in both PDF and extracted text."""
    print("=" * 80)
    print(f"SEARCH: '{search_term}'")
    print("=" * 80)
    
    # Search in extracted text
    with open(txt_path, 'r', encoding='utf-8') as f:
        extracted_text = f.read()
    
    if search_term.lower() in extracted_text.lower():
        # Find context around the term
        idx = extracted_text.lower().find(search_term.lower())
        context_start = max(0, idx - 200)
        context_end = min(len(extracted_text), idx + len(search_term) + 200)
        context = extracted_text[context_start:context_end]
        
        print(f"\n✅ Found in EXTRACTED text at position {idx:,}:")
        print("-" * 80)
        print(f"...{context}...")
        print("-" * 80)
    else:
        print(f"\n❌ NOT found in extracted text")
    
    # Search in PDF (page by page)
    page_count, _ = get_pdf_info(pdf_path)
    print(f"\n🔍 Searching {page_count} pages in PDF...")
    
    found_pages = []
    for page_num in range(min(page_count, 100)):  # Limit search to first 100 pages
        page_text = read_pdf_page(pdf_path, page_num)
        if page_text and search_term.lower() in page_text.lower():
            found_pages.append(page_num + 1)
    
    if found_pages:
        print(f"✅ Found in PDF on pages: {', '.join(map(str, found_pages[:10]))}")
        if len(found_pages) > 10:
            print(f"   (and {len(found_pages) - 10} more pages)")
    else:
        print(f"❌ NOT found in PDF (searched first 100 pages)")


def show_beginning_comparison(pdf_path, txt_path):
    """Compare the beginning of PDF vs extracted."""
    print("\n" + "=" * 80)
    print("BEGINNING COMPARISON")
    print("=" * 80)
    
    # First page of PDF
    pdf_text = read_pdf_page(pdf_path, 0)
    
    # First 2000 chars of extracted
    with open(txt_path, 'r', encoding='utf-8') as f:
        extracted_text = f.read(2000)
    
    print(f"\n📄 PDF Page 1 (first 1000 chars):")
    print("-" * 80)
    print(pdf_text[:1000] if pdf_text else "Could not read")
    print("-" * 80)
    
    print(f"\n📝 EXTRACTED (first 1000 chars):")
    print("-" * 80)
    print(extracted_text[:1000])
    print("-" * 80)
    
    # Manual verification prompt
    print(f"\n👁️  VISUAL VERIFICATION:")
    print("   Compare the two texts above.")
    print("   Are they extracting the same content?")
    print("   Are words spelled correctly?")
    print("   Is spacing correct?")


def show_middle_comparison(pdf_path, txt_path):
    """Compare middle section."""
    page_count, _ = get_pdf_info(pdf_path)
    middle_page = page_count // 2
    
    print("\n" + "=" * 80)
    print(f"MIDDLE COMPARISON (Page {middle_page + 1} of {page_count})")
    print("=" * 80)
    
    pdf_text = read_pdf_page(pdf_path, middle_page)
    
    # Middle of extracted text
    with open(txt_path, 'r', encoding='utf-8') as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(size // 2)
        f.read(100)  # Skip partial line
        extracted_text = f.read(2000)
    
    print(f"\n📄 PDF Page {middle_page + 1} (first 1000 chars):")
    print("-" * 80)
    print(pdf_text[:1000] if pdf_text else "Could not read")
    print("-" * 80)
    
    print(f"\n📝 EXTRACTED Middle (1000 chars):")
    print("-" * 80)
    print(extracted_text[:1000])
    print("-" * 80)


def show_end_comparison(pdf_path, txt_path):
    """Compare end section."""
    page_count, _ = get_pdf_info(pdf_path)
    last_page = page_count - 1
    
    print("\n" + "=" * 80)
    print(f"END COMPARISON (Page {page_count})")
    print("=" * 80)
    
    pdf_text = read_pdf_page(pdf_path, last_page)
    
    # End of extracted text
    with open(txt_path, 'r', encoding='utf-8') as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 2000))
        extracted_text = f.read()
    
    print(f"\n📄 PDF Last Page (last 1000 chars):")
    print("-" * 80)
    print(pdf_text[-1000:] if pdf_text else "Could not read")
    print("-" * 80)
    
    print(f"\n📝 EXTRACTED End (last 1000 chars):")
    print("-" * 80)
    print(extracted_text[-1000:])
    print("-" * 80)


def interactive_comparison(pdf_path, txt_path):
    """Interactive comparison menu."""
    page_count, metadata = get_pdf_info(pdf_path)
    
    print("=" * 80)
    print("PDF TO EXTRACTED TEXT COMPARISON")
    print("=" * 80)
    print(f"\nPDF: {Path(pdf_path).name}")
    print(f"  Pages: {page_count}")
    print(f"  Title: {metadata.get('title', 'N/A')}")
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        f.seek(0, 2)
        txt_size = f.tell()
    print(f"\nExtracted: {Path(txt_path).name}")
    print(f"  Size: {txt_size:,} bytes")
    
    while True:
        print("\n" + "=" * 80)
        print("COMPARISON OPTIONS")
        print("=" * 80)
        print("1. Compare Beginning (Page 1)")
        print("2. Compare Middle")
        print("3. Compare End (Last Page)")
        print("4. Compare Specific Page")
        print("5. Search for Text in Both")
        print("6. Quick Overview (All Sections)")
        print("7. Exit")
        
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == '1':
            show_beginning_comparison(pdf_path, txt_path)
        elif choice == '2':
            show_middle_comparison(pdf_path, txt_path)
        elif choice == '3':
            show_end_comparison(pdf_path, txt_path)
        elif choice == '4':
            page_str = input(f"Enter page number (1-{page_count}): ").strip()
            try:
                page_num = int(page_str) - 1
                if 0 <= page_num < page_count:
                    compare_page_to_extracted(pdf_path, txt_path, page_num)
                else:
                    print(f"❌ Page must be between 1 and {page_count}")
            except ValueError:
                print("❌ Invalid page number")
        elif choice == '5':
            search_term = input("Enter text to search for: ").strip()
            if search_term:
                search_in_both(pdf_path, txt_path, search_term)
        elif choice == '6':
            show_beginning_comparison(pdf_path, txt_path)
            show_middle_comparison(pdf_path, txt_path)
            show_end_comparison(pdf_path, txt_path)
        elif choice == '7':
            print("\n✅ Comparison complete")
            break
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    pdf_path = PROJECT_ROOT / "input" / "Systematic Theology.pdf"
    
    # Ask which extracted file to compare
    print("Which extracted file to compare?")
    print("1. Existing extraction (Systematic Theology.txt)")
    print("2. Multi-pass extraction (Systematic_Theology_multipass.txt)")
    print("3. Custom path")
    
    choice = input("\nSelect (1-3): ").strip()
    
    if choice == '1':
        txt_path = PROJECT_ROOT / "phase2-extraction" / "extracted_text" / "Systematic Theology.txt"
    elif choice == '2':
        txt_path = PROJECT_ROOT / "phase2-extraction" / "Systematic_Theology_multipass.txt"
    elif choice == '3':
        txt_path = Path(input("Enter path to extracted text file: ").strip())
    else:
        print("❌ Invalid choice")
        sys.exit(1)
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    if not txt_path.exists():
        print(f"❌ Extracted text not found: {txt_path}")
        sys.exit(1)
    
    if not PYPDF_AVAILABLE and not PYMUPDF_AVAILABLE:
        print("❌ No PDF reader available. Install pypdf or pymupdf:")
        print("   poetry add pypdf")
        sys.exit(1)
    
    # Run interactive comparison
    interactive_comparison(str(pdf_path), str(txt_path))
