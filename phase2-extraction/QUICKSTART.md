# Phase 2 Enhancement - Quick Start Guide

**Time to complete**: 10-15 minutes

---

## Step 1: Install Dependencies (5 min)

```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction

# Install all new dependencies
poetry add python-docx ebooklib beautifulsoup4 lxml readability-lxml pdf2image pypdf

# Windows-specific: Use python-magic-bin
poetry add python-magic-bin
# If you had python-magic installed before:
# poetry remove python-magic

# Verify installation
poetry install
```

---

## Step 2: Verify Installation (2 min)

```bash
poetry run python verify_extractors.py
```

**Expected**: All checks should show ✓ (green checkmarks)

**If any fail**: Check the error message and install missing dependencies

---

## Step 3: Test with Your PDF (3 min)

```bash
# Use your existing Analects PDF
poetry run python -m phase2_extraction.ingest \
  --file_id analects_test \
  --file "The Analects of Confucius.pdf"
```

**Expected output**:
```
================================================================================
PHASE 2 COMPLETE
================================================================================
Status: success
Duration: 5-15 seconds
Output: extracted_text/analects_test.txt
Quality: >0.80
Yield: >0.95
```

---

## Step 4: Verify Output (2 min)

```bash
# Check the extracted text
type extracted_text\analects_test.txt | more

# Check metadata
type extracted_text\analects_test_meta.json

# Check pipeline.json entry
jq .phase2.files.analects_test pipeline.json
```

**Look for**:
- Text is readable and complete
- No weird characters or formatting issues
- Metadata shows good quality_score (>0.8)

---

## Step 5: Test Other Formats (Optional)

If you have other format files:

```bash
# DOCX
poetry run python -m phase2_extraction.ingest --file_id test_docx --file /path/to/document.docx

# EPUB
poetry run python -m phase2_extraction.ingest --file_id test_epub --file /path/to/ebook.epub

# HTML
poetry run python -m phase2_extraction.ingest --file_id test_html --file /path/to/page.html
```

---

## Troubleshooting

### ❌ "No module named 'docx'"
```bash
poetry add python-docx
```

### ❌ "magic" library error (Windows)
```bash
poetry add python-magic-bin
poetry remove python-magic
```

### ❌ Low quality score
- Is it a scanned PDF? Try: `--force-ocr`
- Check source file quality

### ❌ No text extracted
- Scanned PDF? Use: `--force-ocr`
- Corrupted file? Run Phase 1 validation first

---

## What's Next?

After Phase 2 works:

### Option A: Continue with New Phase 3 Implementation
Follow the Phase 2 & 3 Deep Dive attachment to implement Phase 3 enhancements

### Option B: Test Current Phase 3
```bash
cd ..\phase3-chunking
poetry run python -m phase3_chunking.chunker \
  --input ..\phase2-extraction\extracted_text\analects_test.txt \
  --file-id analects_test
```

### Option C: Run Full Pipeline
```bash
cd ..\phase6_orchestrator
poetry run python orchestrator.py --file_id full_test --input path\to\file.pdf
```

---

## Key Files Created

- `src/phase2_extraction/extractors/` - All format extractors
- `src/phase2_extraction/ingest.py` - Main entry point
- `src/phase2_extraction/normalize.py` - Text normalization
- `src/phase2_extraction/utils.py` - Helper functions
- `verify_extractors.py` - Verification script
- `README_NEW.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - Detailed summary

---

## Success Checklist

- [ ] Dependencies installed without errors
- [ ] `verify_extractors.py` passes all tests
- [ ] Can extract text from your PDF
- [ ] Output quality score >0.8
- [ ] Text is readable and complete
- [ ] pipeline.json updated correctly

---

## Get Help

1. **Check logs** - Console shows detailed progress
2. **Check pipeline.json** - `jq '.phase2.errors' pipeline.json`
3. **Read docs** - `README_NEW.md` has comprehensive info
4. **Check summary** - `IMPLEMENTATION_SUMMARY.md` has troubleshooting

---

**Ready? Start with Step 1!** 🚀
