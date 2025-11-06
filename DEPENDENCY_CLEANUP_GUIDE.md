# Dependency Cleanup Guide

## Purpose
Remove unused dependencies to:
- Reduce installation time
- Avoid version conflicts
- Minimize security surface area
- Clarify actual requirements

## Phase-by-Phase Cleanup

### Phase 1: Validation
**Safe to Remove:**
- `charset-normalizer` — redundant with existing `chardet`

**Commands:**
```bash
cd phase1-validation
poetry remove charset-normalizer
poetry install
```

### Phase 2: Extraction
**Safe to Remove:**
- `charset-normalizer` — not imported anywhere
- `unstructured` — superseded by in-house parsers
- `easyocr` — not imported **and** violates CPU-only constraint (CUDA)

⚠️ **IMPORTANT**: If you need OCR for scanned PDFs, replace easyocr with `pytesseract` (CPU compatible).

**Commands:**
```bash
cd phase2-extraction
poetry remove charset-normalizer unstructured easyocr
poetry install
```

### Phase 3: Chunking
**Safe to Remove:**
- `charset-normalizer` — unused
- `gensim` — legacy experiment, no longer imported

**Commands:**
```bash
cd phase3-chunking
poetry remove charset-normalizer gensim
poetry install
```

### Phase 5: Audio Enhancement
**Safe to Remove:**
- `charset-normalizer` — unused helper
- `python-dateutil` — no date parsing performed
- `requests` — HTTP calls handled elsewhere

**Commands:**
```bash
cd phase5_enhancement
poetry remove charset-normalizer python-dateutil requests
poetry install
```

### Phase 5.5: Subtitle Generation
**Safe to Remove:**
- _None_ (all current dependencies used by Whisper transcription flow)

### Phase 6: Orchestrator
**Safe to Remove:**
- `charset-normalizer` — inherited from early experiments
- `python-docx`, `ebooklib`, `beautifulsoup4`, `lxml`, `readability-lxml`, `pdf2image`, `pypdf`, `python-magic-bin` — document-processing libraries that belong in Phases 1-2, not orchestration

**Commands:**
```bash
cd phase6_orchestrator
poetry remove charset-normalizer python-docx ebooklib beautifulsoup4 lxml readability-lxml pdf2image pypdf python-magic-bin
poetry install
```

### Phase 7: Batch Processing
**Safe to Remove:**
- `charset-normalizer` — unused (batch module only orchestrates other phases)

**Commands:**
```bash
cd phase7_batch
poetry remove charset-normalizer
poetry install
```

### Audio Cleanup Utility
**Safe to Remove:**
- `python-dateutil` — duration math handled via built-ins
- `requests` — no remote downloads performed
- `charset-normalizer` — unused in scripts

**Commands:**
```bash
cd phase_audio_cleanup
poetry remove charset-normalizer python-dateutil requests
poetry install
```

## Special Cases

### GPU-Only Dependencies
The project enforces CPU-only dependencies (≤4 GB RAM). These packages violate that rule:
- `easyocr` (Phase 2) — requires CUDA
- Default `sentence-transformers` models (Phase 3) — may pull GPU-enabled torch wheels

**Recommended Replacements:**
- OCR: Install `pytesseract` (CPU-friendly) if OCR is required.
- Embeddings: Pin `torch==<cpu build>` before installing `sentence-transformers` to ensure CPU-only binaries.

### Phase 6 Orchestrator Bloat
The orchestrator inherited document-processing dependencies from earlier development:
- `python-docx`, `ebooklib`, `beautifulsoup4`, `lxml`, `readability-lxml`, `pdf2image`, `pypdf`, `python-magic-bin`

These belong in Phase 1/2, not the orchestrator. Removing them keeps the orchestrator lean and speeds up deployments.

## Testing After Cleanup

After removing dependencies:
1. Run the phase's test suite: `poetry run pytest tests/ -v`
2. Do a dry run of the orchestrator: `poetry run python orchestrator.py --help`
3. Verify module imports: `poetry run python -c "import <main_module>"`

## Bulk Cleanup Script

For the impatient, here's a script to clean all phases:
```bash
#!/bin/bash
# Run from repo root

set -e

cd phase1-validation && poetry remove charset-normalizer && poetry install && cd ..
cd phase2-extraction && poetry remove charset-normalizer unstructured easyocr && poetry install && cd ..
cd phase3-chunking && poetry remove charset-normalizer gensim && poetry install && cd ..
cd phase5_enhancement && poetry remove charset-normalizer python-dateutil requests && poetry install && cd ..
cd phase6_orchestrator && poetry remove charset-normalizer python-docx ebooklib beautifulsoup4 lxml readability-lxml pdf2image pypdf python-magic-bin && poetry install && cd ..
cd phase7_batch && poetry remove charset-normalizer && poetry install && cd ..
cd phase_audio_cleanup && poetry remove charset-normalizer python-dateutil requests && poetry install && cd ..

echo "✅ Cleanup complete. Run tests to verify."
```

⚠️ **Caution**: Test thoroughly after bulk cleanup!
