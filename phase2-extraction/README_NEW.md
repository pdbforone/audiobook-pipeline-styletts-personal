# Phase 2: Multi-Format Text Extraction & Normalization

**Version 2.0** - Enhanced with modular extractors and genre detection support

## Overview

Phase 2 extracts clean, TTS-ready text from multiple file formats while preserving document structure and maintaining high quality standards.

### Supported Formats

- **PDF** (text-based and scanned with OCR)
- **DOCX** (Microsoft Word documents)
- **EPUB** (ebooks)
- **HTML** (web pages and HTML documents)
- **TXT** (plain text with intelligent line merging)

## Architecture

```
phase2-extraction/
├── src/phase2_extraction/
│   ├── extractors/           # Format-specific extractors
│   │   ├── __init__.py
│   │   ├── pdf.py           # Multi-pass PDF extraction
│   │   ├── docx.py          # Word document extraction
│   │   ├── epub.py          # EPUB ebook extraction
│   │   ├── html.py          # HTML content extraction
│   │   ├── txt.py           # Plain text with smart line merging
│   │   └── ocr.py           # OCR for scanned PDFs
│   ├── normalize.py         # Text normalization pipeline
│   ├── tts_normalizer.py    # TTS-specific cleanup (existing)
│   ├── utils.py             # Helper functions
│   └── ingest.py            # Main entry point
├── extracted_text/          # Output directory
├── tests/                   # Test suite
└── pyproject.toml          # Dependencies
```

## Quick Start

### Installation

```bash
cd phase2-extraction
poetry install
```

**Windows Note**: Use `python-magic-bin` instead of `python-magic`:
```bash
poetry add python-magic-bin
poetry remove python-magic
```

### Basic Usage

```bash
# Extract from file (using Phase 1 classification)
poetry run python -m phase2_extraction.ingest --file_id test001

# Override file path
poetry run python -m phase2_extraction.ingest --file_id test001 --file /path/to/book.pdf

# Force OCR for scanned PDF
poetry run python -m phase2_extraction.ingest --file_id test001 --force-ocr

# Custom output directory
poetry run python -m phase2_extraction.ingest --file_id test001 --extracted_dir ./my_output
```

## Features

### 1. Multi-Pass PDF Extraction

For text-based PDFs, tries multiple extraction methods and selects the best:

- **pypdf**: Pure Python, good for standard PDFs
- **pdfplumber**: Excellent layout preservation
- **PyMuPDF**: Fast and robust fallback

Each method is quality-validated and the best result is selected automatically.

### 2. OCR for Scanned Documents

Uses EasyOCR (CPU-only) with:
- Batch processing to manage memory (default: 10 pages at a time)
- Per-page confidence tracking
- Progress logging for long documents

### 3. Structure Preservation

- **DOCX**: Preserves heading hierarchy with `<HEADING:1>`, `<HEADING:2>`, etc.
- **EPUB**: Maintains chapter structure with `<CHAPTER:id>` markers
- **HTML**: Extracts main content using readability algorithm

### 4. TTS Normalization

Comprehensive text cleanup:
- Removes page numbers, headers, footers
- Extracts and tags footnotes (saved separately)
- Converts curly quotes to straight quotes
- Fixes punctuation spacing
- Collapses multiple spaces
- Normalizes unicode characters

### 5. Quality Validation

Every extraction is validated for:
- **Text yield**: Ratio of extracted text to file size (target: >98% for text, >85% for OCR)
- **Quality score**: Based on character composition, common words, encoding issues
- **Language confidence**: Automatic language detection
- **TTS readiness**: Checks for common TTS issues

## Output Format

### Extracted Text
`extracted_text/{file_id}.txt` - Cleaned, TTS-ready text

### Metadata
`extracted_text/{file_id}_meta.json`:
```json
{
  "title": "The Analects",
  "author": "Confucius",
  "char_count": 124500,
  "quality_score": 0.95,
  "tool_used": "pypdf",
  "detected_format": "pdf",
  "language": "en",
  "language_confidence": 0.9,
  "text_yield": 0.98,
  "preserved_headings": 12,
  "extracted_footnotes": 45
}
```

### Footnotes (if any)
`extracted_text/footnotes/{file_id}_footnotes.json`:
```json
[
  {
    "number": "1",
    "text": "The Master said: This is a footnote."
  }
]
```

### Pipeline.json Entry
```json
{
  "phase2": {
    "status": "success",
    "timestamps": {
      "start": "2025-10-17T14:00:00Z",
      "end": "2025-10-17T14:02:30Z",
      "duration": 150.5
    },
    "metrics": {
      "text_yield": 0.98,
      "quality_score": 0.95,
      "language": "en",
      "language_confidence": 0.9
    },
    "files": {
      "test001": {
        "path": "extracted_text/test001.txt",
        "metadata_path": "extracted_text/test001_meta.json",
        "detected_format": "pdf",
        "word_count": 18500,
        "metadata": {
          "title": "The Analects",
          "author": "Confucius"
        }
      }
    }
  }
}
```

## Quality Targets

| Metric | Target | Description |
|--------|--------|-------------|
| **Text Yield** | >98% (text PDFs) | Extracted chars / file size |
| | >85% (OCR) | Lower for scanned documents |
| **Quality Score** | >0.8 | Based on validation checks |
| **Language Confidence** | >0.9 | Language detection confidence |
| **Processing Time** | <60s per file | Varies by file size |

## Troubleshooting

### Common Issues

#### 1. "No text extracted" from PDF

**Cause**: PDF is scanned/image-based

**Solution**: Use `--force-ocr` flag
```bash
poetry run python -m phase2_extraction.ingest --file_id test001 --force-ocr
```

#### 2. ImportError: No module named 'docx'

**Cause**: Missing dependency

**Solution**: Install required packages
```bash
poetry add python-docx ebooklib beautifulsoup4 lxml
```

#### 3. Low quality score

**Causes**:
- Scanned PDF without OCR
- Corrupted file
- Unusual encoding

**Solutions**:
- Try `--force-ocr` for scanned PDFs
- Run Phase 1 validation first
- Check source file quality

#### 4. Windows: "magic" library error

**Cause**: python-magic requires libmagic binary

**Solution**: Use python-magic-bin instead
```bash
poetry add python-magic-bin
poetry remove python-magic
```

#### 5. Memory issues with large PDFs

**Cause**: OCR processing large files

**Solution**: Already handled via batch processing (10 pages at a time). For very large files, reduce batch size in `ocr.py`:
```python
text, metadata = ocr.extract(path, batch_size=5)  # Smaller batches
```

### Checking Output Quality

```bash
# View extracted text
cat extracted_text/test001.txt | head -n 50

# Check metadata
cat extracted_text/test001_meta.json

# View pipeline status
jq '.phase2' pipeline.json

# Check for errors
jq '.phase2.errors' pipeline.json
```

## Testing

### Run All Tests
```bash
poetry run pytest tests/ -v
```

### Test Specific Format
```bash
poetry run pytest tests/test_extractors.py::test_pdf_extraction -v
```

### Coverage Report
```bash
poetry run pytest tests/ --cov=phase2_extraction --cov-report=html
# Open htmlcov/index.html
```

## Migration from Phase 2 v1

The new modular structure is **backward compatible**. Your existing pipeline.json and orchestrator will continue to work.

### What Changed

1. **Code Organization**: Extraction logic moved to `extractors/` modules
2. **New Formats**: Added DOCX, EPUB, HTML, TXT support
3. **Enhanced Normalization**: More comprehensive cleanup
4. **Better Metadata**: Richer metadata in output files

### What Stayed the Same

1. CLI interface (same arguments)
2. Output paths (`extracted_text/` directory)
3. Pipeline.json structure
4. Integration with Phase 3+

### Gradual Migration

You can run the new Phase 2 alongside the old one:
```bash
# Old Phase 2 (if still available)
poetry run python -m phase2_extraction.extraction --file_id test001

# New Phase 2 (modular)
poetry run python -m phase2_extraction.ingest --file_id test001
```

Both produce compatible output for Phase 3.

## Performance Notes

### Speed Benchmarks (approximate)

- **Text PDF** (200 pages): ~5-15 seconds
- **DOCX** (50 pages): ~1-3 seconds
- **EPUB** (300 pages): ~10-20 seconds
- **OCR** (100 pages): ~500-1000 seconds (5-10s per page)

### Memory Usage

- **Text extraction**: <500 MB
- **OCR**: <4 GB (with batch processing)
- **Large files**: Automatically batched to stay within limits

## Advanced Usage

### Custom Extractor Method

Force a specific PDF extraction method:
```python
from phase2_extraction.extractors import pdf
text, metadata = pdf.extract(path, force_method='pdfplumber')
```

### Custom Normalization

Skip TTS normalization (not recommended):
```python
from phase2_extraction.normalize import normalize_text
text, metrics = normalize_text(raw_text, file_id, skip_tts=True)
```

### Programmatic Usage

```python
from pathlib import Path
from phase2_extraction.ingest import main

main(
    file_id='my_book',
    json_path=Path('pipeline.json'),
    file_override=Path('/path/to/book.pdf'),
    force_ocr=False
)
```

## Error Handling

All errors are logged to `pipeline.json` with actionable fixes:

```json
{
  "error": "missing_dependency",
  "fix": "Run: poetry add python-docx",
  "phase": "phase2",
  "severity": "blocking",
  "timestamp": "2025-10-17T14:00:00Z"
}
```

Check errors:
```bash
jq '.phase2.errors' pipeline.json
```

## Integration with Other Phases

### Phase 1 → Phase 2
Phase 2 reads file classification from Phase 1:
- `text`: Uses text extraction
- `scanned`: Uses OCR
- `mixed`: Tries text, falls back to OCR if quality is low

### Phase 2 → Phase 3
Phase 3 reads from Phase 2 outputs:
- Text file: `extracted_text/{file_id}.txt`
- Metadata: `extracted_text/{file_id}_meta.json`
- Uses metadata for genre detection and voice selection

## Contributing

When adding new extractors:

1. Create `extractors/new_format.py`
2. Implement `extract(path: Path) -> Tuple[str, Dict]`
3. Return cleaned text + metadata with `quality_score`
4. Add format detection to `utils.detect_format()`
5. Add tests in `tests/test_extractors.py`
6. Update this README

## License

Part of the audiobook-pipeline project. See main repository for license.

## Support

For issues or questions:
1. Check this README's troubleshooting section
2. Review logs in console output
3. Check `pipeline.json` for error details
4. See main project documentation

---

**Next Steps**: After Phase 2 completes successfully, proceed to Phase 3 for genre-aware chunking.
