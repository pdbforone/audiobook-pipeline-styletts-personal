# 🚀 Quick Start Guide - Phase 3 Fixed

## ⚠️ IMPORTANT: First-Time Setup

Before running Phase 3 for the first time, you MUST install the spaCy language model:

```batch
cd phase6_orchestrator
.\install_spacy_model.bat
```

This downloads a 15MB language model that Phase 3 needs for sentence detection.

---

## Step 1: Complete Setup (First Time Only)

If this is your first time running Phase 3:

```batch
cd phase6_orchestrator
.\setup_and_test_phase3.bat
```

This will:
1. ✅ Install all Python dependencies
2. ✅ Download spaCy language model
3. ✅ Verify everything works
4. ✅ Run a test automatically

**Then skip to "Expected Results" below.**

---

## Step 2: Fix Phase 2 Venv (if needed)

If you see "Venv Python not found" errors:

```batch
cd phase6_orchestrator
.\fix_phase2_venv.bat
```

This will recreate the Phase 2 venv properly.

---

## Step 3: Test Phase 3 Standalone

Test Phase 3 first to confirm everything works:

```batch
cd phase6_orchestrator
.\test_phase3_quick.bat
```

**Expected output**:
```
✓ Phase 3 SUCCESS
Chunking complete: 3 chunks created
Average coherence: 0.89
Average Flesch score: 65.3
```

---

## Step 4: Test Full Orchestrator

Once Phase 3 works, test the full pipeline:

```batch
cd phase6_orchestrator
.\test_simple.bat
```

This runs: Phase 2 → Phase 3 → Phase 4 → Phase 5

**Expected output**:
```
✓ Phase 2 completed successfully
✓ Phase 3 completed successfully
✓ Phase 4 completed successfully (N chunks)
✓ Phase 5 completed successfully
SUCCESS: Pipeline completed!
```

---

## 🚨 Common Issues

### ❌ "Can't find model 'en_core_web_sm'"
**Fix**: You forgot to install the spaCy model!
```batch
cd phase6_orchestrator
.\install_spacy_model.bat
```

### ❌ Phase 2 "Venv Python not found"
**Fix**: Run `fix_phase2_venv.bat` first

### ❌ Phase 3 "No sentences detected"
**Fix**: Check if test_story.txt exists and has content
```batch
cd ..
dir test_story.txt
type test_story.txt
```

### ❌ Any phase shows "poetry not found"
**Fix**: Install Poetry first:
```batch
pip install poetry
```

### ⚠️ Phase 2 status is "partial_success"
**Not a problem**: Phase 3 will use fallback file search automatically

---

## Files Created

After successful run, you'll see:

```
audiobook-pipeline-chatterbox/
├── pipeline.json                  # ✅ Updated with all phase data
├── phase2-extraction/
│   └── extracted_text/
│       └── test_story.txt         # ✅ Extracted text
├── phase3-chunking/
│   ├── .venv/                     # ✅ Python virtual environment
│   └── chunks/
│       ├── test_story_chunk_001.txt   # ✅ Semantic chunks
│       ├── test_story_chunk_002.txt
│       └── test_story_chunk_003.txt
├── phase4_tts/
│   └── audio_chunks/
│       ├── test_story_chunk_001.wav   # ✅ TTS audio
│       ├── test_story_chunk_002.wav
│       └── test_story_chunk_003.wav
└── phase5_enhancement/
    └── output/
        └── audiobook.mp3              # ✅ Final audiobook!
```

---

## What Was Fixed

### Syntax Errors (✅ FIXED)
- ✅ Phase 3 unterminated string literal (line 256)
- ✅ Missing `try_complete_chunk()` function
- ✅ Duplicate functions removed (file was 150KB, now 25KB)
- ✅ Import structure working with both script and module modes

### Dependencies (⚠️ REQUIRES SETUP)
- ⚠️ spaCy language model must be downloaded separately
- ⚠️ Run `install_spacy_model.bat` before first use

---

## Warnings You Can Ignore

These warnings are normal and don't affect functionality:

✅ **Pydantic UserWarning** - Compatibility warning, works fine
✅ **pkg_resources deprecated** - textstat uses old API, works fine  
✅ **Phase 2 partial_success** - Phase 3 uses fallback automatically
✅ **Low coherence with good Jaccard** - Chunks are still valid

---

## Next Steps

After confirming everything works:

1. ✅ Test with a real PDF file
2. ✅ Check quality metrics in pipeline.json
3. ✅ Listen to the final audiobook.mp3
4. ✅ Adjust chunk size/duration in phase3 config.yaml if needed

---

## Need Help?

**Detailed Troubleshooting**: See `TROUBLESHOOTING.md`
**Technical Details**: See `PHASE3_FIX_SUMMARY.md`

**Most Common Issue**: Forgot to install spaCy model
**Quick Fix**: Run `install_spacy_model.bat`

---

## Test Commands Summary

```batch
# First time setup (do this first!)
.\setup_and_test_phase3.bat

# OR manually:
.\install_spacy_model.bat      # Install spaCy model
.\test_phase3_quick.bat         # Test Phase 3
.\test_simple.bat               # Test full pipeline

# If needed:
.\fix_phase2_venv.bat           # Fix Phase 2 venv
```

---

**Last Updated**: 2025-10-11  
**Status**: Phase 3 fixed ✅ - spaCy model required ⚠️
