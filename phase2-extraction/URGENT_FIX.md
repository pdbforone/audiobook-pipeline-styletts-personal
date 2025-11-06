# 🚨 URGENT FIX: Phase 2 Quality Issue

## Problem Discovered
The orchestrator produces **lower quality** extraction than the test script because:

1. **Orchestrator calls:** `src/phase2_extraction/extraction.py`
   - ❌ No TTS normalization
   - ❌ Uses raw pypdf output
   - Result: Multiple spaces, PDF artifacts, poor TTS quality

2. **Test script calls:** `extraction_TTS_READY.py` 
   - ✅ Has TTS normalization
   - ✅ Cleans spacing, unicode, punctuation
   - Result: Clean, TTS-ready text

## File Size Comparison
- **Orchestrator:** `Systematic Theology.txt` - 3.74MB (lower quality, slightly larger due to extra spaces)
- **Test:** `Systematic Theology_TTS_READY.txt` - 3.73MB (higher quality, properly normalized)

## Solution
**Replace extraction.py with TTS-ready version**

### Option 1: Quick Fix (Recommended)
```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction

# Backup original
copy src\phase2_extraction\extraction.py src\phase2_extraction\extraction_BACKUP.py

# Copy TTS normalizer module
copy tts_normalizer.py src\phase2_extraction\tts_normalizer.py

# Update extraction.py to import and use TTS normalizer
```

### Option 2: Manual Update
Add to `extraction.py` after line 11:

```python
# Import TTS normalizer
try:
    from tts_normalizer import TTSNormalizer
    TTS_NORMALIZER_AVAILABLE = True
except ImportError:
    TTS_NORMALIZER_AVAILABLE = False
    logger.warning("TTS normalizer not available - text may have quality issues")
```

Then in the `main()` function, after text extraction (around line 237):

```python
if text.strip():
    # Normalize text for TTS BEFORE quality checks
    if TTS_NORMALIZER_AVAILABLE:
        logger.info("Normalizing text for TTS quality...")
        normalizer = TTSNormalizer()
        original_len = len(text)
        text = normalizer.normalize(text)
        normalized_len = len(text)
        logger.info(f"✓ Normalized: {original_len} -> {normalized_len} chars")
    else:
        logger.warning("Skipping TTS normalization (module not available)")
    
    # Continue with gibberish/perplexity checks...
```

## Why This Matters
Without TTS normalization:
- ❌ "The     Christian" (multiple spaces confuse TTS)
- ❌ Fancy unicode quotes cause pronunciation issues
- ❌ PDF artifacts like "OceanofPDF.com" in final audio
- ❌ Poor punctuation spacing affects prosody

With TTS normalization:
- ✅ Clean single spaces
- ✅ Standard punctuation
- ✅ Removed artifacts
- ✅ Validated TTS-ready

## Verification Steps
After fixing:

1. **Test extraction:**
   ```bash
   cd phase2-extraction
   poetry run python src/phase2_extraction/extraction.py \
     --file_id="Systematic Theology" \
     --file="path/to/Systematic Theology.pdf" \
     --json_path="../pipeline.json"
   ```

2. **Check output:**
   ```bash
   # Should see "Normalizing text for TTS quality..." in logs
   # File should be ~3.73MB (not 3.74MB)
   # No multiple spaces when you open the .txt file
   ```

3. **Compare files:**
   ```bash
   python compare_to_pdf.py --page 100
   # Should match test quality
   ```

## Priority: CRITICAL
This affects **EVERY** audiobook you create with the orchestrator.
Fix this BEFORE running any more full pipelines.

---

**Next Action:** Choose Option 1 (quick fix) and run the commands above.
