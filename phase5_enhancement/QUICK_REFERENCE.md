# Phase 5 Enhancement - Quick Reference & Known Issues

**Last Updated**: November 3, 2025

---

## 🚨 Known Issues

### **Phrase Cleaning Not Working (Critical)**
**Problem**: `enable_phrase_cleanup: true` in config.yaml doesn't work  
**Symptom**: Phase 5 only processes 36/899 files, 0 phrases removed  
**Root Cause**: File scanning pattern mismatch  
**Status**: ⚠️ **BROKEN** - Use manual workaround

**Workaround**:
1. Run `extract_phrase_timestamps.py` to get Audacity timestamps
2. Manually remove phrases in Audacity (~1 hour for 99 instances)
3. Export cleaned audio

---

## 📁 New Tools Created (Nov 2025)

### **1. Subtitle Validation**
**File**: `validate_subtitles.py`  
**Purpose**: Compare subtitles vs Phase 2 source text  
**Usage**:
```bash
poetry run python validate_subtitles.py \
  --phase2-text "[path-to-phase2-text]" \
  --subtitle-file "processed/audiobook.srt"
```
**Output**: Accuracy %, missing words, unwanted phrases count

---

### **2. Phrase Timestamp Extractor**
**File**: `extract_phrase_timestamps.py`  
**Purpose**: Generate Audacity-ready timestamp list  
**Usage**: `poetry run python extract_phrase_timestamps.py`  
**Output**: `phrase_timestamps.txt` with format:
```
[1/99] START: 3:23.700  END: 3:30.900
```

---

### **3. Surgical Phrase Remover** ⚠️ Untested
**File**: `surgical_phrase_remover.py`  
**Purpose**: Word-level phrase removal using Whisper  
**Status**: Slow, unreliable (86min runtime, 0 phrases found)  
**Not Recommended**: Use Audacity approach instead

---

## 📊 Meditations Project Status

### **Current State**
- Audio: `processed/meditations_audiobook.mp3` (4h 29m)
- Subtitles: `processed/meditations_audiobook.srt` (5,513 segments)
- Phrase count: **99 instances** still present
- Accuracy: **81.09%** (target: >98%)
- Missing content: **8,462 words** from source

### **Phase 2 Source**
- Location: `phase2-extraction/extracted_text/the meditations, by Marcus Aurelius.txt`
- Word count: 44,743 words

### **Audio Chunks**
- Location: `meditations_chunks/` 
- Count: 899 WAV files
- Format: `the meditations, by Marcus Aurelius_chunk_XXX.wav`

---

## 🔧 Recommended Workflow

### **For Meditations Audiobook Completion:**

1. **Extract timestamps**:
   ```bash
   poetry run python extract_phrase_timestamps.py
   ```

2. **Manual Audacity removal** (~1 hour):
   - Open `meditations_audiobook.mp3`
   - Use `phrase_timestamps.txt` as guide
   - Delete each of 99 phrases
   - Export as `meditations_audiobook_FINAL.mp3`

3. **Regenerate subtitles**:
   ```bash
   poetry run python generate_subtitles.py --input processed/meditations_audiobook_FINAL.mp3
   ```

4. **Validate results**:
   ```bash
   poetry run python validate_subtitles.py \
     --phase2-text "[phase2-path]" \
     --subtitle-file "processed/meditations_audiobook_FINAL.srt"
   ```

5. **Expected results**:
   - Accuracy: >95%
   - Phrases: 0
   - Ready for YouTube upload

---

## 🐛 Debugging Phase 5

### **If phrase cleaning still doesn't work:**

1. **Check file scanning**:
   ```python
   # In main.py, add logging
   print(f"Found {len(audio_files)} files in {input_dir}")
   ```

2. **Verify pattern matching**:
   - Check glob pattern in main.py
   - Ensure it matches: `*.wav` or specific naming format

3. **Test with small batch**:
   - Copy 5 chunks to test directory
   - Run Phase 5 on test dir
   - Verify phrase detection works

---

## 📝 For Future Sessions

**Before starting work**:
1. Read `SESSION_SUMMARY_Nov2025.md` for full context
2. Check `validation_report.txt` for current metrics
3. Verify `meditations_audiobook_FINAL.mp3` doesn't already exist

**After phrase removal**:
1. Update this document with new status
2. Run validation and record results
3. Delete intermediate files if cleanup desired

---

## 🔗 Related Files

- **Session summary**: `SESSION_SUMMARY_Nov2025.md` (comprehensive details)
- **Validation report**: `validation_report.txt` (latest metrics)
- **Timestamp list**: `phrase_timestamps.txt` (Audacity guide)
- **Phase 5 config**: `config.yaml` (updated input_dir)

---

## ✅ Success Checklist (Before YouTube)

- [ ] Phrase count: 0 (currently 99)
- [ ] Accuracy: >98% (currently 81%)
- [ ] Missing words: <1,000 (currently 8,462)
- [ ] Final audio: `meditations_audiobook_FINAL.mp3` exists
- [ ] Final subtitles: Validated and accurate
- [ ] Audio/subtitle sync: Verified

---

**Quick Links**:
- Phase 2 source: `phase2-extraction/extracted_text/the meditations, by Marcus Aurelius.txt`
- Audio chunks: `meditations_chunks/` (899 files)
- Current audio: `processed/meditations_audiobook.mp3`
- Current subtitles: `processed/meditations_audiobook.srt`
