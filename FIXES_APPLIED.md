# TTS Skipping Issue - Fixes Applied (2025-10-03)

## 🚨 Issues Found

### 1. **Off-by-One Error in Chunk Loading**
- **Symptom**: `--chunk_id 441` loaded `chunk_442.txt` instead of `chunk_441.txt`
- **Root Cause**: `chunk_loader.py` used chunk_id as 0-based array index
- **Impact**: Every chunk was offset by +1, causing wrong text to be synthesized

### 2. **Splitting Logic Broken for Short Multi-Sentence Chunks**
- **Symptom**: 2-sentence chunks (285 chars) weren't split, Chatterbox skipped content
- **Root Cause**: `split_text_nltk_chars()` returned early if text < 750 chars
- **Impact**: Chatterbox's internal tokenizer failed on quotes/punctuation, skipping sentences

### 3. **Low MOS Score (0.13 vs target >4.5)**
- **Symptom**: Audio quality metrics catastrophically low
- **Root Cause**: Unknown (may be related to Chatterbox model or reference audio)
- **Impact**: May indicate deeper synthesis issues

---

## ✅ Fixes Applied

### **Fix 1: Chunk Indexing (chunk_loader.py)**
**File**: `phase4_tts/src/phase4_tts/chunk_loader.py`

**Changes**:
```python
# OLD (BROKEN):
chunk_path = chunk_paths[chunk_id]  # Direct array access

# NEW (FIXED):
array_index = chunk_id - 1  # Convert 1-based to 0-based
chunk_path = chunk_paths[array_index]
```

**Effect**: `--chunk_id 441` now correctly loads `chunk_441.txt` (array index 440)

---

### **Fix 2: Force Sentence-Level Splitting (main.py)**
**File**: `phase4_tts/src/phase4_tts/main.py`

**Changes** (in `split_text_nltk_chars` function):
```python
# OLD (BROKEN):
if char_count <= max_chars:
    return [text], split_metadata  # No split for short texts

# NEW (FIXED):
# ALWAYS tokenize into sentences first
sentences = sent_tokenize(text)
if len(sentences) <= 1 or char_count <= max_chars:
    # Return sentences separately even if short
    return [s.strip() for s in sentences], split_metadata
```

**Effect**: 
- Multi-sentence chunks are ALWAYS split into individual sentences
- Prevents Chatterbox from skipping content due to quote/punctuation handling
- Example: chunk_441 (2 sentences, 285 chars) now splits into 2 sub-chunks

---

### **Fix 3: Orchestrator Chunk ID Conversion**
**File**: `phase6_orchestrator/orchestrator.py`

**Changes** (in both progress loops):
```python
# OLD (BROKEN):
for i in range(len(chunks)):
    process_single_chunk(..., i, ...)  # 0-based index

# NEW (FIXED):
for i in range(len(chunks)):
    chunk_id = i + 1  # Convert to 1-based
    process_single_chunk(..., chunk_id, ...)
```

**Effect**: Orchestrator now passes correct 1-based chunk IDs to Phase 4 CLI

---

## 🧪 Testing Instructions

### **Test 1: Verify Correct Chunk Loading**
```bash
cd path\to\audiobook-pipeline-styletts-personal\phase4_tts
conda activate phase4_tts

python src\phase4_tts\main.py --chunk_id 441 --file_id The_Analects_of_Confucius_20240228 --json_path ..\pipeline.json --language en --enable-splitting
```

**Expected Console Output**:
```
[OK] Resolved chunk_id 441 to chunk_paths[440]: ...chunk_441.txt
Loaded text chunk: 301 characters, 59 words
First 100 chars: "
The Master said, "He who puts on an appearance of stern firmness...
Forcing sentence splitting for chunk (chars=301)
[SPLIT] Split into 2 sub-chunks using nltk_single_chunk
  Sub-chunk 1: ~150 chars
  Sub-chunk 2: ~150 chars
  [TTS] Generating sub-chunk 1/2: ...
  [TTS] Generating sub-chunk 2/2: ...
[OK] Concatenated 2 segments (2 audio + 0 silence)
```

**Key Checks**:
- ✅ Loads `chunk_441.txt` (NOT chunk_442.txt)
- ✅ Shows "Split into 2 sub-chunks"
- ✅ Both sub-chunks synthesized successfully
- ✅ No silence insertion (`0 silence`)

---

### **Test 2: Verify Audio Completeness**
```bash
# Play the generated audio
start audio_chunks\chunk_441.wav
```

**Listen for BOTH sentences**:
1. "The Master said, 'He who puts on an appearance of stern firmness, while inwardly he is weak, is like one of the small, mean people; -yea, is he not like the thief who breaks through, or climbs over, a wall?'"
2. "The Master said, 'Your good, careful people of the villages are the thieves of virtue.'"

**Success Criteria**:
- ✅ Both sentences fully spoken (no skips)
- ✅ Audio duration ~8-12 seconds (not truncated)
- ✅ Clear pronunciation (no garbling)

---

### **Test 3: Check pipeline.json Metadata**
```bash
python -c "import json; p=json.load(open('../pipeline.json')); chunk=p.get('phase4',{}).get('files',{}).get('The_Analects_of_Confucius_20240228',{}).get('chunks',{}).get('441',{}); print('Metrics:', json.dumps(chunk.get('metrics',{}), indent=2)); print('\nErrors:', chunk.get('errors',[]))"
```

**Expected Output**:
```json
Metrics: {
  "splits_performed": true,
  "num_sub_chunks": 2,
  "sub_chunk_char_lengths": [145, 156],
  "method": "nltk_single_chunk",
  "truncated_sentences": 0,
  "silence_inserted_count": 0
}

Errors: []
```

**Success Criteria**:
- ✅ `"splits_performed": true`
- ✅ `"num_sub_chunks": 2`
- ✅ `"silence_inserted_count": 0` (no failures)
- ✅ `"errors": []` (no sub-chunk errors)

---

## 🚀 Next Steps

### **If Test 1-3 Pass**:
1. **Run full Phase 4 via orchestrator**:
   ```bash
   cd ..\phase6_orchestrator
   python orchestrator.py ..\input\The_Analects_of_Confucius_20240228.pdf --phases 4 --pipeline-json ..\pipeline.json
   ```
   - Expected runtime: ~30-60 minutes for ~500 chunks
   - Monitor console for warnings

2. **Spot-check random chunks**:
   ```bash
   # Play chunk_085.wav, chunk_100.wav, chunk_200.wav
   start ..\phase4_tts\audio_chunks\chunk_085.wav
   ```

3. **Proceed to Phase 5** (audio enhancement) once Phase 4 completes

### **If Tests Still Fail**:

**Scenario A: Audio still skips sentences**
- Check if Chatterbox is actually being used (vs Piper fallback)
- Test Piper-only mode by commenting out Chatterbox code
- File issue with Chatterbox maintainers: https://github.com/resemble-ai/chatterbox/issues

**Scenario B: MOS score still <4.5**
- Review reference audio quality (`greenman_ref.wav`)
- Try different reference audio with `--ref_url` or `--ref_file`
- Check for corruption in generated audio files

**Scenario C: Different chunks fail**
- Increase `sub_chunk_retries` in `config.yaml` (current: 2)
- Increase timeout in orchestrator (current: 20min/chunk)
- Review `chunk_{id}_error.log` files for specific failures

---

## 📝 Files Modified

1. **phase4_tts/src/phase4_tts/chunk_loader.py**
   - Lines 85-92: Added 1-based to 0-based conversion

2. **phase4_tts/src/phase4_tts/main.py**
   - Lines 278-310: Rewrote `split_text_nltk_chars` early-return logic
   - Forces sentence-level splitting for all multi-sentence texts

3. **phase6_orchestrator/orchestrator.py**
   - Lines 450, 465: Added `chunk_id = i + 1` conversion in both loops
   - Lines 457, 471: Updated `failed_chunks.append()` to use chunk_id

---

## 🔄 Rollback Instructions (If Needed)

If these fixes cause new issues, revert changes:

```bash
cd path\to\audiobook-pipeline-styletts-personal

# Revert chunk_loader.py
git checkout phase4_tts/src/phase4_tts/chunk_loader.py

# Revert main.py
git checkout phase4_tts/src/phase4_tts/main.py

# Revert orchestrator
git checkout phase6_orchestrator/orchestrator.py
```

Or manually restore from backups if not using git.

---

## 📊 Success Metrics

| Metric | Before | Target | After Testing |
|--------|--------|--------|---------------|
| Chunk Loading | Off by +1 | Correct | TBD |
| Sentence Splitting | Skipped for <750 chars | Always applied | TBD |
| Audio Completeness | Missing sentences | 100% | TBD |
| MOS Score | 0.13 | >4.5 | TBD |
| Failed Chunks | Unknown | <5% | TBD |

---

## 🐛 Known Issues

1. **Low MOS Score**: The 0.13 MOS proxy is extremely low and needs investigation
   - Possible causes: poor reference audio, model issues, CPU vs GPU mismatch
   - May not directly correlate with audio quality (needs manual listening test)

2. **Chatterbox Token Repetition**: Log shows warning about token repetition
   - Chatterbox auto-detected and forced EOS (End of Sequence)
   - May indicate model instability on certain text patterns
   - Monitor for consistency across chunks

3. **Orchestrator Resume**: If a chunk fails midway, resume logic may need testing
   - Verify `--no-resume` flag behavior
   - Check if partial runs properly update pipeline.json

---

**Generated**: 2025-10-03 20:55 (after applying all fixes)
**Next Update**: After running Test 1-3 above


