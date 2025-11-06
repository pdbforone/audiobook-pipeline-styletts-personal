# 🔧 Troubleshooting Guide - Phase 3

## Issue: spaCy Model Not Found

### ❌ Error Message:
```
OSError: [E050] Can't find model 'en_core_web_lg'. It doesn't seem to be a Python package or a valid path to a data directory.
OSError: [E050] Can't find model 'en_core_web_sm'. It doesn't seem to be a Python package or a valid path to a data directory.
```

### ✅ Solution:

**Quick Fix (Recommended):**
```batch
cd phase6_orchestrator
.\install_spacy_model.bat
```

This installs the **small model** (en_core_web_sm - 15MB) which is fast and sufficient for chunking.

---

**Complete Setup (First Time):**
```batch
cd phase6_orchestrator
.\setup_and_test_phase3.bat
```

This does:
1. Installs all dependencies
2. Downloads spaCy model
3. Verifies everything works
4. Runs a test

---

**Manual Fix:**
```batch
cd phase3-chunking
poetry run python -m spacy download en_core_web_sm
```

Then verify:
```batch
poetry run python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('SUCCESS!')"
```

---

## Why Does This Happen?

spaCy models are **separate downloads**, not installed automatically with `poetry install`. 

**Models available:**
- `en_core_web_sm` - 15MB, fast, good accuracy (✅ recommended)
- `en_core_web_md` - 50MB, better accuracy
- `en_core_web_lg` - 800MB, best accuracy (overkill for chunking)

---

## Other Common Issues

### 1. Phase 2 Status Not Success
**Error**: `Phase 2 status is not 'success': partial_success`

**What it means**: Phase 2 ran but had warnings/issues

**Fix**: This is OK - Phase 3 uses fallback file search and finds the text file automatically

**If you want to fix Phase 2**:
```batch
cd phase6_orchestrator
.\fix_phase2_venv.bat
```

---

### 2. No Chunks Created
**Error**: `No valid chunks for embedding calculation`

**Possible causes**:
- Text file too short (< 200 characters)
- Text is all gibberish/special characters
- Sentence detection failed

**Fix**: Check your input file has actual readable text:
```batch
cd ..
type test_story.txt
```

---

### 3. Low Coherence Warning
**Warning**: `Low coherence (0.XX), checking Jaccard fallback`

**What it means**: Chunks don't flow well together

**Is it a problem?**: No, if Jaccard similarity > 0.4

**Why it happens**: 
- Text has abrupt topic changes
- Short story with scene breaks
- Technical content with lists

**Fix**: This is informational - chunks are still created

---

### 4. Chunks Exceed Duration
**Warning**: `Chunk N duration (XX.Xs) exceeds target (25s)`

**What it means**: Some chunks are predicted to take > 25s to read

**Is it a problem?**: Potentially - Phase 4 TTS might truncate at 40s

**Fix**: Adjust config.yaml:
```yaml
max_chunk_chars: 300  # Reduce from 350
max_chunk_duration: 20.0  # Reduce from 45.0
```

---

### 5. Import Error
**Error**: `ImportError: attempted relative import with no known parent package`

**Cause**: Running main.py directly as a script

**Fix**: Always use module syntax:
```batch
poetry run python -m phase3_chunking.main --file_id=test_story
```

**Not**:
```batch
poetry run python src/phase3_chunking/main.py  # ❌ Wrong
```

---

### 6. Pydantic Warning
**Warning**: `pydantic...UserWarning: <built-in function any> is not a Python type`

**What it means**: Pydantic compatibility issue with Python 3.12

**Is it a problem?**: No - just a warning, functionality works fine

**Fix**: Ignore it, or suppress with:
```python
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
```

---

### 7. pkg_resources Deprecated Warning
**Warning**: `pkg_resources is deprecated as an API`

**What it means**: textstat uses old setuptools API

**Is it a problem?**: No - just a warning, works until 2025-11-30

**Fix**: Ignore it - textstat will update eventually

---

## Verification Steps

### 1. Check Python Version
```batch
cd phase3-chunking
poetry run python --version
```
**Expected**: Python 3.12.x

### 2. Check Dependencies Installed
```batch
poetry show | findstr "spacy sentence-transformers"
```
**Expected**: 
```
spacy             3.8.4
sentence-transformers 5.1.0
```

### 3. Check spaCy Model
```batch
poetry run python -m spacy validate
```
**Expected**: Shows installed models

### 4. Test Import
```batch
poetry run python -c "from phase3_chunking.utils import *; print('OK')"
```
**Expected**: `OK`

---

## Files to Check

### 1. Config File
**Location**: `phase3-chunking/config.yaml`

**Key settings**:
```yaml
min_chunk_chars: 200
max_chunk_chars: 350
max_chunk_duration: 45.0
coherence_threshold: 0.4
flesch_threshold: 60.0
```

### 2. Test File
**Location**: `phase2-extraction/extracted_text/test_story.txt`

**Should contain**: Real text content (not empty)

### 3. Output Directory
**Location**: `phase3-chunking/chunks/`

**After success**: Contains `test_story_chunk_001.txt`, etc.

### 4. Pipeline JSON
**Location**: `pipeline.json` (root)

**After success**: Contains phase3 entry with status "success"

---

## Full Test Sequence

Run these in order to verify everything:

```batch
# 1. Install spaCy model
cd phase6_orchestrator
.\install_spacy_model.bat

# 2. Test Phase 3 alone
.\test_phase3_quick.bat

# 3. If that works, test full pipeline
.\test_simple.bat
```

---

## Still Not Working?

### Check Logs
Look at the error messages carefully - they're detailed and actionable.

### Verify File Paths
Make sure you're in the correct directory:
```batch
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator
```

### Check Disk Space
spaCy models need space:
- en_core_web_sm: 15MB
- en_core_web_lg: 800MB

### Reinstall Dependencies
```batch
cd ..\phase3-chunking
poetry env remove python
poetry install --no-root
poetry run python -m spacy download en_core_web_sm
```

---

## Contact/Debug Info

If you need to report an issue, include:

1. Full error message from terminal
2. Python version: `poetry run python --version`
3. Poetry version: `poetry --version`
4. OS: `systeminfo | findstr OS`
5. Contents of `config.yaml`
6. Size of input file: `dir test_story.txt`

---

**Last Updated**: 2025-10-11
**Most Common Issue**: spaCy model not downloaded (run install_spacy_model.bat)
