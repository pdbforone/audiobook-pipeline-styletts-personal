# Phase 2 Extraction Fix for Font Encoding Issues

## Problem
PDFs with custom fonts (like Systematic Theology) produce gibberish because pdfplumber/PyMuPDF don't handle font mapping correctly.

## Solution
Add `pypdf` library which has better font encoding support.

## Installation
```bash
cd path\to\audiobook-pipeline-styletts-personal\phase2-extraction
poetry add pypdf
```

## Code Changes to `src/phase2_extraction/extraction.py`

### 1. Add pypdf import at top (around line 15):
```python
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    logger.warning("pypdf not available - some PDFs may extract as gibberish")
```

### 2. Add new extraction function after `extract_text_pymupdf`:
```python
def extract_text_pypdf(file_path: str) -> str:
    """
    Extract text using pypdf - often better for custom fonts.
    pypdf has superior font encoding/mapping compared to pdfplumber/pymupdf.
    """
    if not PYPDF_AVAILABLE:
        return ""
    try:
        reader = PdfReader(file_path)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)
    except Exception as e:
        logger.warning(f"pypdf failed: {e}")
        return ""
```

### 3. Update the main extraction logic (around line 170, in the main() function):

Replace this section:
```python
if classification == "text" or classification == "mixed":
    # For text and mixed PDFs, try text extraction first
    text = extract_text_pdfplumber(file_path) or extract_text_pymupdf(file_path)
    tool_used = "pdfplumber or pymupdf"
```

With this (NEW - tries pypdf FIRST):
```python
if classification == "text" or classification == "mixed":
    # Try pypdf first - best font encoding support
    text = extract_text_pypdf(file_path)
    if text.strip():
        tool_used = "pypdf"
    else:
        # Fallback to pdfplumber/pymupdf
        text = extract_text_pdfplumber(file_path) or extract_text_pymupdf(file_path)
        tool_used = "pdfplumber or pymupdf"
```

## Testing
After making changes:
```bash
# Re-run Phase 2 on the problematic file
poetry run python -m phase2_extraction.extraction --file_id "Systematic_Theology" --file "path\to\audiobook-pipeline-styletts-personal\input\Systematic Theology.pdf"
```

## Expected Results
- Gibberish score: < 0.5 (was 1.0)
- Perplexity: > 0.92 (was 0.097)
- Language: "en" with confidence > 0.9 (was "unknown")
- Yield: > 98% (was 2.23%)

## Alternative: If pypdf doesn't work either

Some PDFs are truly problematic. If pypdf also fails, you have two options:

### Option A: Use OCR (slow but accurate)
The PDF might have scanned images or be protection. Use EasyOCR:
```python
# In extraction.py, change classification to "scanned" manually for this file
# Or add a fallback to OCR after all text methods fail
```

### Option B: Extract with Adobe/system tools
```bash
# Use system PDF tools that handle fonts better
# On Windows: Use Adobe Reader's "Save as Text" feature
```

## Verification
After fixing, check the extracted file:
```bash
cd extracted_text
head -c 500 "Systematic Theology.txt"
```

Should see readable English like:
```
Chapter 1: Introduction to Systematic Theology

The study of systematic theology involves...
```

NOT gibberish like:
```
 ▯▯▯▯▯ 1: ▯▯▯▯▯▯▯▯▯▯ to ▯▯▯▯▯▯▯▯ ▯▯▯▯▯▯▯
```


