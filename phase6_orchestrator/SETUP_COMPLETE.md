# Phase 6 Orchestrator - Setup Complete

## What We Created

A new **Phase 6 Orchestrator** at: `phase6_orchestrator/orchestrator.py`

This is a **simple, single-file orchestrator** that runs phases 1-5 sequentially for ONE input file.

## Key Features

✅ **Simple & Direct**: No complex dependencies, just subprocess calls  
✅ **Phase 4 Conda Support**: Automatically uses `conda run -n phase4_tts`  
✅ **Smart Detection**: Finds phase directories and Python executables automatically  
✅ **Chunk Processing**: Handles Phase 4's per-chunk TTS generation  
✅ **Clear Logging**: Shows exactly what's happening at each step  

## Next Steps to Get It Working

### 1. Test Phase 4 Conda Environment

First, verify your Conda setup:

```bash
cd phase6_orchestrator
python test_conda.py
```

**If it fails**, you need to create the environment:
```bash
cd ../phase4_tts
conda env create -f environment.yml
```

### 2. Test the Orchestrator

Try running it on your test file:

```bash
cd phase6_orchestrator
python orchestrator.py "C:\Users\myson\Pipeline\The Analects of Confucius_20240228.pdf"
```

### 3. Debug Any Issues

The orchestrator will show you exactly where it fails:
- Which phase failed
- The exact command that was run
- The error output

## File Structure

```
phase6_orchestrator/
├── orchestrator.py          ← Main script (USE THIS)
├── test_conda.py            ← Test Conda setup
├── README.md                ← Full documentation
├── config.yaml              ← Configuration (optional)
└── pyproject.toml           ← Poetry config (for future)
```

## How to Use

### Basic Usage
```bash
python orchestrator.py /path/to/book.pdf
```

### Run Specific Phases
```bash
# Test phases 1-3 only (skip TTS)
python orchestrator.py book.pdf --phases 1 2 3

# Test just Phase 4
python orchestrator.py book.pdf --phases 4
```

### Custom pipeline.json Location
```bash
python orchestrator.py book.pdf --pipeline-json /custom/path/pipeline.json
```

## What About the Old phase6_batch?

The old `phase6_batch` directory is actually **Phase 7** (batch processing). 

**Current status**:
- It's locked by Windows (probably `.venv` is in use)
- You can rename it manually later when nothing is using it
- For now, just ignore it and use the new `phase6_orchestrator`

**To rename later**:
1. Close all terminals and VS Code
2. Rename `phase6_batch` → `phase7_batch` in File Explorer
3. Update internal references if needed

## Troubleshooting Guide

### Problem: "Conda environment 'phase4_tts' not found"

**Solution**:
```bash
cd phase4_tts
conda env create -f environment.yml
```

### Problem: "Phase X directory not found"

**Check your structure**:
```
audiobook-pipeline/
├── phase1-validation/
├── phase2-extraction/
├── phase3-chunking/
├── phase4_tts/
├── phase5_enhancement/
└── phase6_orchestrator/  ← New!
```

### Problem: Phase fails with import errors

**Install dependencies**:
```bash
cd phaseX_xxx
poetry install  # For phases 1-3, 5
```

### Problem: Phase 4 specific errors

**Verify Chatterbox is installed**:
```bash
conda activate phase4_tts
python -c "import chatterbox; print('OK')"
```

If it fails:
```bash
conda activate phase4_tts
pip install git+https://github.com/resemble-ai/chatterbox.git
```

## Architecture Alignment

This matches your spec perfectly:

✅ **Phase 6** = Single-file orchestrator (NEW - this!)  
⏸️ **Phase 7** = Batch processor (OLD phase6_batch - rename later)  

Phase 6 is now the **main entry point** for processing one file through the entire pipeline.

## Testing Strategy

1. **Test Conda first**: `python test_conda.py`
2. **Test Phase 1 only**: `python orchestrator.py book.pdf --phases 1`
3. **Test Phases 1-3**: `python orchestrator.py book.pdf --phases 1 2 3`
4. **Test Phase 4 alone**: `python orchestrator.py book.pdf --phases 4` (requires Phase 3 completed)
5. **Full pipeline**: `python orchestrator.py book.pdf`

## What's Different from Old phase6_batch?

| Feature | Old (phase6_batch) | New (phase6_orchestrator) |
|---------|-------------------|---------------------------|
| Purpose | Batch processing (Phase 7) | Single-file orchestration (Phase 6) |
| Complexity | Complex with Trio async | Simple subprocess calls |
| Dependencies | Many (Rich, Trio, etc) | Minimal (stdlib only) |
| Target | Multiple files in parallel | One file at a time |
| Conda Handling | Buggy detection | Clean `conda run` |

## Ready to Test?

Try this now:

```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline\phase6_orchestrator
python test_conda.py
```

This will tell you if Phase 4 is ready. Then you can run the full orchestrator!
