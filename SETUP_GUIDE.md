# Phase Setup Guide

## Quick Setup (Recommended)

### 1. Run Setup Script
```powershell
# From project root
.\setup_all_phases.ps1
```

This will:
- Install dependencies for all Poetry-managed phases (1, 2, 3, 5, 6, 7)
- Download spaCy language model for Phase 3 (en_core_web_sm)
- Show Python version for each phase
- Report any installation failures

**Takes:** 5-10 minutes (downloads dependencies + ~40MB spaCy model)

### 2. Verify Installation
```powershell
.\verify_setup.ps1
```

This will:
- Check each phase's virtualenv exists
- Verify key packages are installed
- Test imports work correctly
- Check Phase 4's Conda environment

**Takes:** ~30 seconds

### 3. Run Pipeline
```powershell
cd phase6_orchestrator
poetry run python orchestrator.py --pipeline ../pipeline.json <input_file>
```

---

## Manual Setup (If Scripts Fail)

### Poetry Phases (1, 2, 3, 5, 6, 7)

For each phase directory:

```powershell
cd phase1-validation

# Remove old virtualenv (if needed)
poetry env remove --all

# Create virtualenv with correct Python
poetry env use "path\to\Python312\python.exe"

# Install dependencies
poetry install --sync

# Verify
poetry run python -c "import ftfy; print('OK')"
```

Repeat for:
- `phase2-extraction` (test: `import pdfplumber`)
- `phase3-chunking` (test: `import spacy` - see note below)
- `phase5_enhancement` (test: `import librosa`)
- `phase6_orchestrator` (test: `import rich`)
- `phase7_batch` (test: `import typer`)

#### Phase 3 Special Requirement: spaCy Language Model

Phase 3 requires an additional step to download the spaCy language model:

```powershell
cd phase3-chunking
poetry install --sync

# Download spaCy language model (required!)
poetry run python -m spacy download en_core_web_sm

# Verify both spaCy and the model
poetry run python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('OK')"
```

**Why?** The spaCy model is a ~40MB data file, not a Python package. It must be downloaded separately after installing spaCy.

### Phase 4 (Conda)

```powershell
cd phase4_tts

# Create Conda environment
conda env create -f environment.yml

# Activate and verify
conda activate phase4_tts
python -c "import torch; print('OK')"
```

---

## Troubleshooting

### Issue: "No module named 'ftfy'" (or similar)

**Cause:** Dependencies not installed in phase's virtualenv

**Fix:**
```powershell
cd <phase_directory>
poetry install --sync
```

### Issue: "Can't find model 'en_core_web_sm'" (Phase 3)

**Cause:** spaCy language model not downloaded

**Fix:**
```powershell
cd phase3-chunking
poetry run python -m spacy download en_core_web_sm
```

**Why this happens:** The spaCy model is a large data file (~40MB) that must be downloaded separately. It's not installed automatically with `poetry install`.

### Issue: "Python version (3.11.9) is not allowed"

**Cause:** Phase virtualenv using wrong Python version

**Fix:**
```powershell
cd <phase_directory>
poetry env remove --all
poetry env use "C:\path\to\Python312\python.exe"
poetry install
```

### Issue: "poetry: command not found"

**Cause:** Poetry not installed

**Fix:**
```powershell
pip install poetry
```

### Issue: Scripts won't run ("execution of scripts is disabled")

**Cause:** PowerShell execution policy

**Fix (run as Administrator):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then run scripts normally.

### Issue: Poetry cache is corrupted

**Cause:** Stale package cache

**Fix:**
```powershell
poetry cache clear pypi --all
poetry install --sync
```

---

## Python Version Requirements

| Phase | Required Python | Reason |
|-------|----------------|--------|
| 1 | ≥3.12 | Type hints, newer features |
| 2 | ^3.11 | PDF processing libraries |
| 3 | ~3.12 | Semantic models |
| 4 | Conda | Torch compatibility |
| 5 | ^3.11 | Audio processing |
| 6 | ^3.10+ | Orchestration |
| 7 | ^3.10+ | Batch processing |

**Note:** All phases work with Python 3.12 or 3.13.

---

## Expected Output

### Setup Script Success:
```
=== Setting up phase1-validation ===
  Checking virtualenv...
  Installing dependencies...
  [OK] Python 3.12.0

...

========================================
Setup Summary
========================================
  Successful: 7
  Failed:     0

✅ All phases ready!
```

### Verify Script Success:
```
=== phase1-validation ===
  Python: 3.12.0
  Package 'ftfy': Installed ✓
  Installed packages: 15

...

========================================
✅ All phases verified successfully!

You're ready to run the pipeline.
```

---

## Post-Setup

Once all phases are installed:

```powershell
# Process a book
cd phase6_orchestrator
poetry run python orchestrator.py --pipeline ../pipeline.json book.pdf

# Or with subtitles
poetry run python orchestrator.py --pipeline ../pipeline.json --enable-subtitles book.pdf

# Batch processing
cd phase7_batch
poetry run python src/phase7_batch/main.py --input-dir ../input --pipeline ../pipeline.json
```

---

## Directory Structure After Setup

```
audiobook-pipeline-styletts-personal/
├── phase1-validation/
│   └── .venv/              # Python 3.12+ virtualenv
├── phase2-extraction/
│   └── .venv/              # Python 3.11+ virtualenv
├── phase3-chunking/
│   └── .venv/              # Python 3.12+ virtualenv
├── phase4_tts/
│   # No .venv (uses Conda: phase4_tts)
├── phase5_enhancement/
│   └── .venv/              # Python 3.11+ virtualenv
├── phase6_orchestrator/
│   └── .venv/              # Python 3.10+ virtualenv
└── phase7_batch/
    └── .venv/              # Python 3.10+ virtualenv
```

Each `.venv` is isolated and contains phase-specific dependencies.

---

## Getting Help

If setup still fails after running scripts:

1. **Check Python installations:**
   ```powershell
   python --version
   where.exe python
   ```

2. **Check Poetry:**
   ```powershell
   poetry --version
   poetry config --list
   ```

3. **Check Conda (for Phase 4):**
   ```powershell
   conda --version
   conda env list
   ```

4. **Share error output** from scripts for diagnosis.

