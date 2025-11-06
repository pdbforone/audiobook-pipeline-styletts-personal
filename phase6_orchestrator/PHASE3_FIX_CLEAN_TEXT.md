# Phase 3 Clean Text Fix

## Problem
The `clean_text()` function in Phase 3 is TOO AGGRESSIVE and removing important content:

```python
# Line 111 - TOO AGGRESSIVE!
text = re.sub(r"[^\w\s.,;:!?\-'\"\n]", "", text)
```

This regex removes:
- Section headers (I., II., XII., etc.)
- Roman numerals
- Special characters like р.кв.
- Any non-ASCII characters

**Result**: Only 3.5% similarity between original and chunked text!

---

## Solution

Replace line 111 in `utils.py` with a more lenient approach:

```python
# OPTION 1: Keep more characters (Recommended)
# Only remove truly problematic chars, keep most others
text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)  # Remove control chars only

# OPTION 2: Minimal cleaning
# Just fix encoding and normalize whitespace, don't remove content
# (This is actually better for TTS - let TTS handle pronunciation)
```

Or even better - **SKIP AGGRESSIVE CLEANING ENTIRELY**:

```python
def clean_text(text: str) -> str:
    """Clean and normalize text - MINIMAL PROCESSING."""
    start = time.perf_counter()

    if not text or not text.strip():
        logger.warning("Empty text provided to clean_text")
        return ""

    # Fix encoding issues
    text = ftfy.fix_text(text)

    # Normalize whitespace but preserve sentence boundaries
    text = re.sub(r"[ \t]+", " ", text)  # Collapse spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)  # Limit multiple newlines

    # REMOVED: text = re.sub(r"[^\w\s.,;:!?\-'\"\n]", "", text)
    # ↑ This was removing section headers and special chars!

    elapsed = time.perf_counter() - start
    logger.info(f"Cleaning time: {elapsed:.4f}s")
    return text.strip()
```

---

## Why This Happened

The original intent was probably:
- Remove "noise" from OCR/PDF extraction
- Clean up formatting for TTS

But it went too far and removed structural content that's part of the actual book!

---

## Impact

**Before fix**:
- Similarity: 3.5%
- Missing: 15,676 characters
- Lost: Section headers, Roman numerals, formatting

**After fix**:
- Expected similarity: 99%+
- Missing: ~0 characters (just whitespace normalization)
- Preserved: All original content

---

## How to Apply

1. **Edit file**:
   ```
   C:\Users\myson\Pipeline\audiobook-pipeline\phase3-chunking\src\phase3_chunking\utils.py
   ```

2. **Find line 111**:
   ```python
   text = re.sub(r"[^\w\s.,;:!?\-'\"\n]", "", text)
   ```

3. **Remove it or replace with minimal cleaning**

4. **Re-run Phase 3**:
   ```bash
   cd phase3-chunking
   python -m phase3_chunking.cli --file_id The_Analects_of_Confucius_20240228 --json_path ../pipeline.json
   ```

5. **Verify fix**:
   ```bash
   python test_coverage_manual.py
   # Should show 99%+ similarity
   ```

---

## Alternative: Keep Aggressive Cleaning But Preserve Headers

If you WANT to clean special chars but keep section numbers:

```python
# Keep Roman numerals and periods before removing other special chars
text = re.sub(r"[^\w\s.,;:!?\-'\"\nIVXLCDM]", "", text)
#                                    ^^^^^^^ Added Roman numerals
```

But honestly, **minimal cleaning is better** - TTS models can handle most characters fine!
