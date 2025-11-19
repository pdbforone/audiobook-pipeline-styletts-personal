# Phase 3 Chunking Fixes - Analysis & Implementation

## 🔍 Issues Identified

### 1. **Long Chunks Not Enforced (Max 44s > 25s target)**
**Root Cause**: The `split_long_chunk()` function split text once but didn't recursively verify sub-chunks were within limits. If a sub-chunk was still >312 chars or >25s, it was added anyway.

**Location**: `utils.py` lines 130-160 (original `split_long_chunk` function)

**Bug**:
```python
# Old code would stop splitting after first pass
if currentSubLen + wordLen > maxChars:
    if currentSub and currentSubLen >= minChars:
        subChunks.append(currentSub.join(' '))  # ❌ Never checks if THIS is too long!
```

### 2. **Merge Function Creating Oversized Chunks**
**Root Cause**: `merge_short_chunks()` only checked character length, not duration. Merging two 180-char chunks could create a 360-char, 29s chunk that exceeds both limits.

**Location**: `utils.py` lines 163-175

**Bug**:
```python
# Old code
if len(chunk) < minChars and current:
    current += " " + chunk  # ❌ No duration check!
```

### 3. **Low Coherence (0.47 << 0.87 target)**
**Root Cause**: Using `all-MiniLM-L6-v2` model (small, 6 layers). This model has weaker semantic understanding than larger alternatives.

**Location**: `utils.py` line 57

**Issue**:
```python
_model = SentenceTransformer("all-MiniLM-L6-v2")  # ❌ Only 6 layers, 384 dims
```

### 4. **Main Chunking Loop Edge Cases**
**Root Cause**: When current chunk was below MIN_CHARS but adding next sentence exceeded MAX, the code would split the combined text but not recursively verify the results.

**Location**: `utils.py` lines 194-250 (`_chunk_by_char_count_optimized`)

---

## ✅ Fixes Applied

### Fix 1: Recursive Splitting Enforcement
**File**: `utils_FIXED.py` lines 92-144

```python
def split_long_chunk(chunk: str, max_chars: int, max_duration: float) -> List[str]:
    """🔧 FIX: Recursively split until ALL sub-chunks are within limits."""
    
    def recursive_split(text: str) -> List[str]:
        current_duration = predict_duration(text)
        
        # Base case: within limits
        if len(text) <= max_chars and current_duration <= max_duration:
            return [text]
        
        # Recursive case: split and check again
        # ... split logic ...
        results.extend(recursive_split(sub_text))  # ✅ Recursion ensures compliance
        
        return results
    
    return recursive_split(chunk)
```

**Impact**: Guarantees NO chunk can exceed 312 chars or 25s, even after multiple splits.

---

### Fix 2: Duration-Aware Merging
**File**: `utils_FIXED.py` lines 147-188

```python
def merge_short_chunks(chunks, min_chars, max_chars, max_duration):
    """🔧 FIX: Check duration when merging to avoid oversized chunks."""
    
    for chunk in chunks:
        if len(chunk) < min_chars and current:
            test_merged = (current + " " + chunk).strip()
            test_duration = predict_duration(test_merged)  # ✅ Duration check added
            
            if len(test_merged) <= max_chars and test_duration <= max_duration:
                current = test_merged
            else:
                # Can't merge - would exceed limits
                merged.append(current)
                current = chunk
```

**Impact**: Prevents merge operations from creating chunks that violate duration limits.

---

### Fix 3: Better Sentence Embeddings
**File**: `utils_FIXED.py` line 57

```python
def get_sentence_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-mpnet-base-v2")  # ✅ Upgraded model
        logger.info("Loaded sentence model: all-mpnet-base-v2")
    return _model
```

**Comparison**:
- **Old**: all-MiniLM-L6-v2 (6 layers, 384 dimensions, 22M params)
- **New**: all-mpnet-base-v2 (12 layers, 768 dimensions, 110M params)
- **Expected improvement**: Coherence should increase from ~0.47 to 0.70-0.85

---

### Fix 4: Stricter Main Loop Logic
**File**: `utils_FIXED.py` lines 191-331

Key improvements:
1. **Every flush point** now double-checks limits before appending
2. **Edge cases** (chunk too small + sentence exceeds limit) now recursively split
3. **Final chunk** handling improved with merge-back logic
4. **Verification logging** added to catch any chunks that slip through

```python
# Example fix in main loop
if current_chunk and current_char_count >= min_chars:
    chunk_text = " ".join(current_chunk)
    chunk_duration = predict_duration(chunk_text)
    
    # ✅ Double-check before adding
    if len(chunk_text) <= max_chars and chunk_duration <= max_duration:
        chunks.append(chunk_text)
    else:
        # ✅ Recursively split if over limits
        chunks.extend(split_long_chunk(chunk_text, max_chars, max_duration))
```

---

## 📊 Expected Improvements

### Before Fixes:
- ❌ Max chunk duration: 44s (76% over target)
- ❌ Chunks exceeding 25s: Unknown count, but >0
- ❌ Coherence: 0.47 (46% below target)
- ⚠️ Status: "partial" due to warnings

### After Fixes:
- ✅ Max chunk duration: ≤25s (enforced recursively)
- ✅ Chunks exceeding 25s: 0 (guaranteed by recursive checks)
- ✅ Coherence: 0.70-0.85 (expected with better model)
- ✅ Char range: All chunks 200-312 chars or merged/split appropriately
- ✅ Status: "success" (if coherence/readability pass thresholds)

---

## 🧪 Testing Strategy

### 1. Test on Sample Text (first 2000 chars)
```bash
# Extract sample
head -c 2000 "path\to\audiobook-pipeline-styletts-personal\phase2-extraction\extracted_text\The_Analects_of_Confucius_20240228.txt" > test_sample.txt

# Run with fixed code
python -m phase3_chunking.main --file_id "test_sample" --text_path "test_sample.txt" --chunks_dir "test_chunks" --config "phase3-chunking/config.yaml"
```

### 2. Verify No Long Chunks
```python
# Check in pipeline.json
import json
data = json.load(open('pipeline.json'))
durations = data['phase3']['files']['test_sample']['chunk_metrics']['chunk_durations']
max_dur = max(durations)
print(f"Max duration: {max_dur:.1f}s - {'✅ PASS' if max_dur <= 25 else '❌ FAIL'}")
```

### 3. Full Re-run
```bash
# After testing, replace utils.py and re-run
mv phase3-chunking/src/phase3_chunking/utils.py phase3-chunking/src/phase3_chunking/utils_OLD.py
mv phase3-chunking/src/phase3_chunking/utils_FIXED.py phase3-chunking/src/phase3_chunking/utils.py

# Re-run Phase 3
python -m phase3_chunking.main --file_id "The_Analects_of_Confucius_20240228" --json_path "pipeline.json" --chunks_dir "chunks" --config "phase3-chunking/config.yaml" -v
```

---

## 📝 Configuration Mismatch Note

**Found**: `config.yaml` has different values than `utils.py` constants:
- config.yaml: `chunk_min_chars: 300`, `chunk_max_chars: 400`
- utils.py: `MIN_CHUNK_CHARS = 200`, `MAX_CHUNK_CHARS = 312`

**Resolution**: The code in `main.py` passes config values to `form_semantic_chunks()`, which overrides the utils.py defaults. **However**, for consistency:

1. **Option A (Recommended)**: Update `config.yaml` to match the tuned values:
   ```yaml
   chunk_min_chars: 200
   chunk_max_chars: 312
   max_chunk_duration: 25.0
   ```

2. **Option B**: Keep config.yaml values and adjust MAX_DURATION_SECONDS calculation:
   ```python
   # For 400 chars at 750 cpm:
   MAX_DURATION_SECONDS = (400 / 750) * 60  # = 32s
   ```

**Recommendation**: Use Option A (200-312 chars) for safety margin below Chatterbox's 40s cutoff.

---

## 🚀 Re-Run Command

```bash
# 1. Backup original
cp phase3-chunking/src/phase3_chunking/utils.py phase3-chunking/src/phase3_chunking/utils_BACKUP.py

# 2. Replace with fixed version
cp phase3-chunking/src/phase3_chunking/utils_FIXED.py phase3-chunking/src/phase3_chunking/utils.py

# 3. Update config (optional but recommended)
# Edit config.yaml to set chunk_min_chars: 200, chunk_max_chars: 312

# 4. Re-run Phase 3 with verbose logging
python -m phase3_chunking.main \
    --file_id "The_Analects_of_Confucius_20240228" \
    --json_path "pipeline.json" \
    --chunks_dir "chunks" \
    --config "phase3-chunking/config.yaml" \
    --verbose

# 5. Check results
grep "chunks_exceeding_duration" pipeline.json
# Should show: "chunks_exceeding_duration": 0
```

---

## 🎯 Success Criteria

- [ ] Max chunk duration ≤ 25s
- [ ] All chunks within 200-312 chars (or merged/split appropriately)
- [ ] 0 chunks exceeding duration limit
- [ ] Coherence ≥ 0.70 (improved from 0.47)
- [ ] Status = "success" (not "partial")
- [ ] No "❌ TOO LONG" warnings in logs

---

## 📌 Key Code Changes Summary

| Function | Lines | Change | Impact |
|----------|-------|--------|--------|
| `split_long_chunk` | 92-144 | Added recursive splitting | Guarantees no chunks >312 chars or >25s |
| `merge_short_chunks` | 147-188 | Added duration checks | Prevents merges from creating oversized chunks |
| `get_sentence_model` | 56-61 | Upgraded to all-mpnet-base-v2 | Expected +50% coherence improvement |
| `_chunk_by_char_count_optimized` | 191-331 | Added double-checks at every flush | Catches edge cases that slip through |
| `form_semantic_chunks` | 334-420 | Added verification logging | Confirms all chunks comply with limits |

---

## ⚠️ Important Notes

1. **First run will be slower**: `all-mpnet-base-v2` is ~5x larger than `all-MiniLM-L6-v2`. First-time download may take 1-2 minutes. Subsequent runs cache the model.

2. **Coherence may still be <0.87**: The Analects has short, disconnected sayings. Target 0.70-0.80 is realistic for this text type.

3. **Monitor logs carefully**: Look for "✅ SUCCESS: All X chunks are <= 25s" message. If you see "❌ CRITICAL", report immediately.

4. **Config values**: Decide whether to use 200-312 (safer) or 300-400 (config values). Don't mix both.

---

Generated: 2025-10-04
Author: Claude (Sonnet 4.5)


