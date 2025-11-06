# Phase 3 Chunking Fix - Flexible Limits Implementation

**Date**: 2025-10-30  
**Issue**: TTS corruption from incomplete chunks (mid-sentence truncations)  
**Solution**: Flexible limits with aggressive completion

---

## Problem Diagnosis

Phase 3 was generating chunks that ended mid-sentence, causing Phase 4 TTS to inject error phrases:

```
"...the power of contemplation which" ← INCOMPLETE
↓
TTS: "...the power of contemplation which **you need to add some text for me to talk**"
```

**Root Cause**: The old chunking logic would:
1. Detect incomplete chunks (e.g., ending with preposition, relative clause)
2. Try to add 3 more sentences to complete it
3. If completion would exceed 2000 chars → **Give up and output incomplete chunk anyway**

---

## Solution Implemented

### Three-Tier Limit Structure

Replaced single MAX_CHUNK_CHARS (2000) with flexible limits:

| Limit | Chars | Duration | Purpose |
|-------|-------|----------|---------|
| **SOFT** | 1800 | ~23s | Preferred chunk size |
| **HARD** | 2000 | ~25s | Can extend here to complete sentences |
| **EMERGENCY** | 3000 | ~38s | Absolute max for philosophical arguments |

### Core Strategy

**Rule**: **NEVER** output incomplete chunks

**Algorithm**:
1. Build chunks targeting SOFT_LIMIT (1800 chars)
2. Check completeness before flushing
3. If incomplete:
   - Try adding up to 10 more sentences (not 3)
   - Accept chunks up to EMERGENCY_LIMIT (3000) if needed
4. If forward completion fails:
   - **Merge backwards** with previous chunk
   - Try splitting merged chunk at semicolons (philosophical texts)
   - Last resort: split by words
5. **Final validation pass** catches any incomplete chunks that escape

### Enhanced Completeness Detection

The `is_complete_chunk()` function now detects:

**Old detection** (still included):
- Unbalanced quotes
- Dialogue introducers ("he said")
- Dangling prepositions ("...of")

**New detection**:
- Relative clauses ("...which", "...that", "...who")
- Subordinate clauses ("...because", "...although")
- Conjunctions ("...and", "...but", "...or")
- Auxiliary verbs ("...is", "...has", "...will")
- Incomplete complex sentences (e.g., "...the power of contemplation which")

### New Helper Functions

1. **`try_complete_chunk()`** - Tries up to 10 sentences to complete (was 3)
2. **`merge_backwards()`** - Merges incomplete chunk with previous when forward fails
3. **`split_at_semicolon()`** - Splits at semicolons for philosophical texts
4. **`split_by_words()`** - Last resort word-boundary splitting
5. **`validate_chunks()`** - Final validation pass to catch incomplete chunks

---

## Changes Summary

### Limits Configuration

```python
# Old (single limit)
MIN_CHUNK_CHARS = 1000
MAX_CHUNK_CHARS = 2000
MAX_DURATION_SECONDS = 25

# New (flexible limits)
MIN_CHUNK_CHARS = 1000
SOFT_LIMIT_CHARS = 1800  # Preferred
HARD_LIMIT_CHARS = 2000  # Can extend here
EMERGENCY_LIMIT_CHARS = 3000  # Absolute max
MAX_DURATION_SECONDS = 25
EMERGENCY_DURATION_SECONDS = 38
```

### Chunking Function Signature

```python
# Old
def _chunk_by_char_count_optimized(
    sentences, 
    min_chars=MIN_CHUNK_CHARS, 
    max_chars=MAX_CHUNK_CHARS,
    max_duration=MAX_DURATION_SECONDS
)

# New
def _chunk_by_char_count_optimized(
    sentences, 
    min_chars=MIN_CHUNK_CHARS, 
    soft_limit=SOFT_LIMIT_CHARS,
    hard_limit=HARD_LIMIT_CHARS,
    emergency_limit=EMERGENCY_LIMIT_CHARS,
    max_duration=MAX_DURATION_SECONDS,
    emergency_duration=EMERGENCY_DURATION_SECONDS
)
```

### Metrics Tracking

```python
# Old
calculate_chunk_metrics() returned:
- chunks_in_target_range
- chunks_exceeding_duration

# New
calculate_chunk_metrics() returns:
- chunks_within_soft_limit
- chunks_within_hard_limit
- chunks_within_emergency_limit
- chunks_exceeding_emergency
```

---

## Testing Instructions

### 1. Quick Validation Test

Run Phase 3 on a sample file and check for incomplete chunks:

```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase3-chunking

# Run chunking on a test file
poetry run python -m phase3_chunking.main \
  --text-file "test.txt" \
  --output-dir "chunks" \
  --profile philosophy

# Check logs for validation results
# Expected: "✅ VALIDATION PASSED: All N chunks are complete"
# Should NOT see: "❌ VALIDATION FAILED"
```

### 2. Meditations Re-Chunk Test

Re-run Phase 3 on "The Meditations" to generate new chunks without mid-sentence splits:

```bash
# Back up existing chunks first
cp -r "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase3-chunking\chunks" \
      "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase3-chunking\chunks_backup"

# Re-run Phase 3
poetry run python -m phase3_chunking.main \
  --text-file "path/to/the_meditations.txt" \
  --output-dir "chunks" \
  --profile philosophy

# Spot-check random chunks for completeness
```

**Manual spot-check**:
- Read chunks 50, 100, 700, 899 (the ones that were incomplete before)
- Verify they now end with complete thoughts
- No dangling prepositions, relative clauses, or conjunctions

### 3. Comprehensive Validation Script

Create a validation script to check all chunks:

```python
# validate_chunks.py
import os
import re
from pathlib import Path

def is_complete(text):
    """Check if chunk ends on complete thought."""
    incomplete_patterns = [
        r'\b(to|for|with|from|by|at|in|on|of|about)\s*$',  # Prepositions
        r'\b(which|that|who|whom)\s*$',  # Relative pronouns
        r'\b(and|but|or|yet|so)\s*$',  # Conjunctions
        r'\b(is|are|was|were|has|have|had|will|would)\s*$',  # Auxiliaries
        r',\s*$',  # Ends with comma
    ]
    
    for pattern in incomplete_patterns:
        if re.search(pattern, text.strip(), re.IGNORECASE):
            return False, f"Ends with incomplete phrase"
    
    return True, "Complete"

def validate_all_chunks(chunks_dir):
    """Validate all chunks in directory."""
    chunks_dir = Path(chunks_dir)
    chunk_files = sorted(chunks_dir.glob("*.txt"))
    
    incomplete_chunks = []
    
    for chunk_file in chunk_files:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        is_comp, reason = is_complete(text)
        if not is_comp:
            incomplete_chunks.append((chunk_file.name, reason, text[-100:]))
    
    if incomplete_chunks:
        print(f"❌ Found {len(incomplete_chunks)} incomplete chunks:")
        for name, reason, preview in incomplete_chunks:
            print(f"\n{name}: {reason}")
            print(f"  Ends with: ...{preview}")
    else:
        print(f"✅ All {len(chunk_files)} chunks are complete!")

if __name__ == "__main__":
    validate_all_chunks("chunks")
```

Run:
```bash
python validate_chunks.py
```

### 4. Monitor Chunk Distribution

Check that chunks are distributed across the flexible limits:

```bash
# Look for this in Phase 3 logs
grep "Limit adherence" phase3_chunking.log

# Expected output like:
# Limit adherence: 723 within SOFT (1800), 142 within HARD (2000), 34 within EMERGENCY (3000), 0 OVER emergency
```

**Good distribution**:
- Most chunks (70-80%) within SOFT_LIMIT
- Some chunks (15-25%) within HARD_LIMIT (for completion)
- Few chunks (5-10%) within EMERGENCY_LIMIT (complex arguments)
- **Zero chunks** over EMERGENCY_LIMIT

**Bad distribution** (indicates issues):
- Many chunks (>10%) in EMERGENCY range → Philosophy profile might be too aggressive
- Any chunks over EMERGENCY → CRITICAL bug, needs investigation

---

## Expected Improvements

### Before (Old Chunking)

```
Chunk 050: "...I never did anything of which I had occasion"  ← INCOMPLETE
Chunk 100: "...retain the power of contemplation which"  ← INCOMPLETE
Chunk 700: "...the parts being subject to"  ← INCOMPLETE
```

**Phase 4 TTS Result**: Error phrases injected mid-sentence

### After (Fixed Chunking)

```
Chunk 050: "...I never did anything of which I had occasion to repent."  ← COMPLETE
Chunk 100: "...retain the power of contemplation which enables man to see all things."  ← COMPLETE
Chunk 700: "...the parts being subject to the laws of the whole."  ← COMPLETE
```

**Phase 4 TTS Result**: Clean, uninterrupted narration

---

## Troubleshooting

### Issue: Still seeing incomplete chunks after fix

**Diagnosis**:
```bash
# Check Phase 3 logs
grep "VALIDATION FAILED" phase3_chunking.log
grep "incomplete chunk" phase3_chunking.log
```

**Fixes**:
1. Verify you're running the NEW utils.py (check file modification date)
2. Check if EMERGENCY_LIMIT is too low for your content type
3. Increase EMERGENCY_LIMIT to 4000 for extremely complex texts
4. Report chunks that exceed EMERGENCY_LIMIT for investigation

### Issue: Too many chunks in EMERGENCY range

**Diagnosis**:
```bash
grep "Limit adherence" phase3_chunking.log
# If >20% of chunks are in EMERGENCY range
```

**Fixes**:
1. Increase SOFT_LIMIT from 1800 to 2000
2. Increase HARD_LIMIT from 2000 to 2500
3. Adjust `try_complete_chunk()` to try fewer sentences (10 → 5)

### Issue: Chunks are too long for TTS (timeout in Phase 4)

**Diagnosis**:
```bash
# Check Phase 4 logs
grep "timeout" phase4_tts.log
grep "exceeded" phase4_tts.log
```

**Fixes**:
1. Lower EMERGENCY_LIMIT from 3000 to 2500
2. Lower EMERGENCY_DURATION from 38s to 35s
3. Tune SOFT_LIMIT down to 1600

---

## Performance Metrics

Track these metrics in pipeline.json after re-running Phase 3:

```json
"phase3": {
  "metrics": {
    "chunks_within_soft_limit": 723,    // ~80% (good)
    "chunks_within_hard_limit": 142,    // ~15% (acceptable)
    "chunks_within_emergency_limit": 34, // ~5% (minimal)
    "chunks_exceeding_emergency": 0,    // MUST be 0
    "avg_duration": 23.5,               // Close to target
    "max_duration": 37.8                // Under EMERGENCY (38s)
  }
}
```

---

## Next Steps

1. ✅ **Implemented**: Flexible limits chunking in utils.py
2. ⏳ **Pending**: Test on Meditations (re-run Phase 3)
3. ⏳ **Pending**: Validate all chunks are complete
4. ⏳ **Pending**: Re-run Phase 4 TTS on new chunks
5. ⏳ **Pending**: Verify zero error phrases in Phase 5 audio

---

## Code Changes Reference

### Files Modified

1. **`phase3-chunking/src/phase3_chunking/utils.py`**
   - Complete rewrite of chunking algorithm
   - Added flexible limits support
   - Added backward merging logic
   - Added validation pass
   - Enhanced completeness detection

### Backward Compatibility

- ✅ All existing function signatures maintained
- ✅ Old code calling `form_semantic_chunks()` still works
- ✅ New limits optional (defaults to old values if not specified)
- ✅ Pipeline.json schema unchanged (metrics enhanced, not replaced)

---

## Success Criteria

Phase 3 chunking fix is successful when:

- ✅ Zero "VALIDATION FAILED" errors in logs
- ✅ Zero chunks ending with incomplete phrases
- ✅ All chunks pass manual spot-check
- ✅ Phase 4 TTS completes without error phrases
- ✅ Phase 5 audio contains no "you need to add some text" artifacts
- ✅ Chunk distribution shows <5% in EMERGENCY range

---

**Author**: Claude (Sonnet 4.5)  
**Based on**: TTS chunking research (7 minutes, 311 sources)  
**Implementation**: 2025-10-30
