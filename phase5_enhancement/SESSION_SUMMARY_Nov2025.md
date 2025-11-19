# Session Summary: Meditations Audiobook Phrase Cleaning
**Date**: November 2025  
**Primary Goal**: Remove "You need to add some text for me to talk" phrase from Meditations audiobook  
**Status**: Phase 5 issues identified; Manual Audacity approach recommended

---

## 🎯 Problem Statement

The Meditations audiobook (4h 29m) contains ~100 instances of the TTS artifact phrase:
- "You need to add some text for me to talk"
- "You need to add text for me to talk"

This phrase appears scattered throughout the audiobook and needs removal before YouTube upload.

---

## 📂 Files Created This Session

### **1. Subtitle Validation Script**
**Location**: `phase5_enhancement/validate_subtitles.py`

**Purpose**: Compare generated subtitles against Phase 2 source text to detect:
- Missing content (TTS truncations)
- Extra content (unwanted phrases)
- Overall word accuracy

**Usage**:
```bash
poetry run python validate_subtitles.py \
  --phase2-text "path\to\audiobook-pipeline-styletts-personal\phase2-extraction\extracted_text\the meditations, by Marcus Aurelius.txt" \
  --subtitle-file "processed\meditations_audiobook.srt" \
  --output "validation_report.txt"
```

**Key Metrics**:
- Source words: 44,743
- Subtitle words: 38,884
- Accuracy: 81.09% (target: >98%)
- Unwanted phrases found: 99 instances

---

### **2. Surgical Phrase Remover (Word-Level)**
**Location**: `phase5_enhancement/surgical_phrase_remover.py`

**Purpose**: Remove phrases using word-level Whisper timestamps (vs segment-level)

**Status**: ⚠️ **Not tested** - ran for 86 minutes but found 0 phrases

**Why it didn't work**: The full audiobook transcription with word-level timestamps took too long, and the pattern matching didn't detect the phrases properly.

**Learning**: Word-level Whisper is too slow for 4+ hour audiobooks on CPU.

---

### **3. Diagnostic Whisper Script**
**Location**: `phase5_enhancement/diagnose_whisper.py`

**Purpose**: Extract 30-second sample around known phrase location to debug Whisper transcription

**Key Finding**: Whisper transcribes as "texts" (plural) instead of "text" in some cases:
```
' You need to add some texts for me to talk,'
```

This variance makes pattern matching harder.

---

### **4. Timestamp Extraction Script**
**Location**: `phase5_enhancement/extract_phrase_timestamps.py`

**Purpose**: Generate Audacity-friendly timestamp list for manual removal

**Output**: `phrase_timestamps.txt` with format:
```
[1/99] START: 3:23.700  END: 3:30.900
    Text: You need to add some text for me to talk.
```

**Usage**:
```bash
poetry run python extract_phrase_timestamps.py
```

**Status**: ✅ **Ready to use** - This is the recommended approach.

---

## 🔧 What We Tried (and Results)

### **Approach 1: Segment-Level Phrase Cleaning** ❌
**Script**: `strip_phrases_final.py` (pre-existing)

**Result**: 
- Removed 80 instances
- BUT also removed legitimate content surrounding phrases
- Example loss: "of man is so disposed, you need to add some text for me to talk" → entire segment deleted

**Verdict**: Too destructive; loses Meditations content

---

### **Approach 2: Phase 5 Re-run with Cleaning** ❌
**Config Update**: Changed `input_dir` to `meditations_chunks` (899 files)

**Result**: 
- Phase 5 only processed 36/899 files
- 0 phrases cleaned
- Processing time: 63.95s

**Root Cause**: File pattern matching issue - Phase 5's main.py doesn't properly scan files with naming format:
```
the meditations, by Marcus Aurelius_chunk_001.wav
```

**Verdict**: Phase 5 phrase cleaning integration is broken for this use case

---

### **Approach 3: Surgical Word-Level Removal** ⚠️
**Script**: `surgical_phrase_remover.py` (created this session)

**Result**: Ran for 86 minutes, found 0 phrases

**Root Cause**: Unknown - possibly pattern matching issue with word tokenization

**Verdict**: Too slow and unreliable

---

### **Approach 4: Manual Audacity Removal** ✅ **RECOMMENDED**
**Script**: `extract_phrase_timestamps.py` (created this session)

**Workflow**:
1. Run script to get 99 timestamps
2. Open `meditations_audiobook.mp3` in Audacity
3. For each timestamp: Select → Delete → Verify
4. Export as `meditations_audiobook_FINAL.mp3`

**Time Estimate**: ~1 hour (99 phrases × 30-40 seconds each)

**Verdict**: Most reliable approach given Phase 5 issues

---

## 📊 Current State

### **Audio Files**
- **Original (with phrases)**: `processed/meditations_audiobook.mp3` (4h 29m, 269.4 min)
- **Segment-cleaned (missing content)**: `processed/meditations_CLEANED.mp3` (4h 22m, 262.0 min)
- **Chunks (source, 899 files)**: `meditations_chunks/`

### **Subtitle Files**
- **Current SRT**: `processed/meditations_audiobook.srt` (5,513 segments)
- **Validation report**: `validation_report.txt`

### **Phase 2 Source Text**
- **Location**: `phase2-extraction/extracted_text/the meditations, by Marcus Aurelius.txt`
- **Word count**: 44,743 words

---

## 🔑 Key Learnings

### **1. Phase 5 Phrase Cleaning Issues**
- Config setting `enable_phrase_cleanup: true` exists but doesn't work properly
- File scanning only finds subset of files (36/899)
- May be related to filename format or glob pattern matching
- **Action Item**: Debug Phase 5's main.py file scanning logic for future projects

### **2. Whisper Transcription Variance**
- "text" vs "texts" (plural/singular inconsistency)
- Punctuation variations ("talk." vs "talk")
- Leading spaces in word tokenization
- **Action Item**: Use fuzzy matching or normalize patterns before matching

### **3. Word-Level vs Segment-Level Trade-offs**
- **Word-level**: More precise but MUCH slower (11+ hours for full audiobook)
- **Segment-level**: Fast but removes surrounding content
- **Action Item**: For future, consider hybrid approach (segment detection → word-level trimming)

### **4. Validation is Critical**
- The `validate_subtitles.py` script revealed 81% accuracy (should be 98%+)
- 8,462 words missing from source text
- This caught issues that would have made YouTube video incomplete
- **Action Item**: Always validate subtitles against Phase 2 source text before upload

---

## 📋 Recommended Next Steps

### **Immediate (This Project)**
1. ✅ Run `extract_phrase_timestamps.py` to get timestamp list
2. ⏳ Use Audacity to manually remove 99 phrases (~1 hour)
3. ⏳ Export cleaned audio as `meditations_audiobook_FINAL.mp3`
4. ⏳ Regenerate subtitles from FINAL.mp3:
   ```bash
   poetry run python generate_subtitles.py --input processed/meditations_audiobook_FINAL.mp3
   ```
5. ⏳ Re-validate subtitles:
   ```bash
   poetry run python validate_subtitles.py \
     --phase2-text "..." \
     --subtitle-file "processed/meditations_audiobook_FINAL.srt"
   ```
6. ⏳ Expect validation to show:
   - Accuracy: >95% (ideally 98%+)
   - Unwanted phrases: 0
   - Missing words: <2,000

### **Future Improvements (Pipeline)**
1. **Fix Phase 5 file scanning** - Debug why only 36/899 files detected
2. **Improve phrase detection** - Add fuzzy matching for "text"/"texts" variants
3. **Add pre-TTS phrase filtering** - Prevent phrases from being synthesized in Phase 4
4. **Integrate validation into Phase 6** - Auto-validate subtitles as part of orchestrator
5. **Document Phase 5 phrase cleaning** - Add examples and troubleshooting to README

---

## 🗂️ File Reference Map

```
audiobook-pipeline-styletts-personal/
├── phase2-extraction/
│   └── extracted_text/
│       └── the meditations, by Marcus Aurelius.txt  ← Source text (44,743 words)
│
├── phase5_enhancement/
│   ├── meditations_chunks/                          ← 899 TTS chunks (input)
│   │   └── the meditations, by Marcus Aurelius_chunk_001.wav ... 899.wav
│   │
│   ├── processed/
│   │   ├── meditations_audiobook.mp3                ← Current (with 99 phrases)
│   │   ├── meditations_audiobook.srt                ← Current subtitles (5,513 segments)
│   │   └── meditations_CLEANED.mp3                  ← Segment-cleaned (missing content)
│   │
│   ├── config.yaml                                  ← Phase 5 config (updated input_dir)
│   │
│   ├── validate_subtitles.py                        ← NEW: Subtitle validation
│   ├── surgical_phrase_remover.py                   ← NEW: Word-level cleaner (untested)
│   ├── diagnose_whisper.py                          ← NEW: Whisper diagnostic
│   ├── extract_phrase_timestamps.py                 ← NEW: Timestamp extractor
│   │
│   ├── strip_phrases_final.py                       ← Pre-existing segment cleaner
│   ├── generate_subtitles.py                        ← Pre-existing subtitle generator
│   │
│   └── validation_report.txt                        ← Latest validation (81% accuracy)
│
└── [Future: meditations_audiobook_FINAL.mp3]        ← After Audacity cleaning
```

---

## 💡 Quick Commands Reference

### **Validate Subtitles**
```bash
cd path\to\audiobook-pipeline-styletts-personal\phase5_enhancement
poetry run python validate_subtitles.py \
  --phase2-text "path\to\audiobook-pipeline-styletts-personal\phase2-extraction\extracted_text\the meditations, by Marcus Aurelius.txt" \
  --subtitle-file "processed\meditations_audiobook.srt"
```

### **Extract Timestamps for Audacity**
```bash
poetry run python extract_phrase_timestamps.py
# Output: phrase_timestamps.txt
```

### **Generate Subtitles**
```bash
poetry run python generate_subtitles.py --input processed/meditations_audiobook.mp3
# Output: processed/meditations_audiobook.srt
# Time: ~3-4 hours for 4.5 hour audiobook
```

### **Run Phase 5 Enhancement**
```bash
poetry run python -m phase5_enhancement.main
# Note: Currently only processes 36/899 files (bug)
```

---

## 🐛 Known Issues

### **Issue #1: Phase 5 File Scanning**
**Symptom**: Only processes 36/899 files  
**Impact**: Phrase cleaning doesn't run on all chunks  
**Workaround**: Manual Audacity removal  
**Fix Needed**: Debug main.py's file glob pattern

### **Issue #2: Low Subtitle Accuracy**
**Symptom**: 81% accuracy vs 98% target  
**Impact**: 8,462 words missing from subtitles  
**Root Cause**: Unknown - possibly TTS truncations or Whisper errors  
**Action**: Investigate Phase 4 TTS logs for truncations

### **Issue #3: Whisper Transcription Variance**
**Symptom**: "text" vs "texts", punctuation inconsistency  
**Impact**: Pattern matching fails to detect all phrases  
**Workaround**: Use fuzzy matching or multiple patterns  
**Fix Needed**: Normalize text before pattern matching

---

## 📝 Notes for Future Claude

When picking up this project:

1. **Check validation report first** - Run `validate_subtitles.py` to see current state
2. **Don't rely on Phase 5 phrase cleaning** - It's broken for this project
3. **Audacity manual removal works** - Use `extract_phrase_timestamps.py` output
4. **Always validate after changes** - Subtitle validation catches silent failures
5. **Watch for missing content** - 8,462 words missing suggests upstream issues

### **If Starting Fresh:**
1. Re-read this document
2. Check `validation_report.txt` for latest metrics
3. Look for `meditations_audiobook_FINAL.mp3` - if exists, Audacity cleaning is done
4. Run validation on FINAL version before proceeding to YouTube upload

---

## ✅ Success Criteria (Before YouTube Upload)

- [ ] Unwanted phrase count: **0** (currently 99)
- [ ] Subtitle accuracy: **>98%** (currently 81%)
- [ ] Missing words: **<1,000** (currently 8,462)
- [ ] Audio duration: **~267 minutes** (accounting for phrase removal)
- [ ] Subtitles sync with audio: **Verified**

---

**Last Updated**: November 3, 2025  
**Session Duration**: ~3 hours  
**Primary Achievement**: Identified Phase 5 issues and created manual workaround tools


