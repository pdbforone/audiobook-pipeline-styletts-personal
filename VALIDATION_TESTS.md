# Quick Validation Guide - Test All Fixes

Run these commands to verify all bug fixes are working:

## 🧪 **Test 1: Phase 4 MOS Score (Fix #2)**
```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline\phase4_tts
conda activate phase4_tts

# Re-run chunk_441 with fixed MOS calculation
python src\phase4_tts\main.py --chunk_id 441 --file_id The_Analects_of_Confucius_20240228 --json_path ..\pipeline.json --language en --enable-splitting
```

**Look for in output:**
```
MOS Score: 3.5-4.5  ← Should be in this range now (not 0.13!)
(RMS=0.xxx, Centroid=XXXXHz, ZCR=0.xxx)  ← Detailed metrics
```

**Verify in pipeline.json:**
```bash
python -c "import json; p=json.load(open('../pipeline.json')); print('MOS:', p['phase4']['files']['The_Analects_of_Confucius_20240228']['metrics']['avg_mos'])"
```

---

## 🧪 **Test 2: Phase 5 Enhanced Audio (Fix #1 - CRITICAL)**
```bash
cd ..\phase5_enhancement

# Test on single chunk first
poetry run python src\phase5_enhancement\main.py --chunk_id 441 --skip_concatenation
```

**Check files created:**
```bash
dir processed\enhanced_0441.wav
```

**Listen to both versions:**
```bash
# Original from Phase 4
start ..\phase4_tts\audio_chunks\chunk_441.wav

# Enhanced from Phase 5 (should sound cleaner!)
start processed\enhanced_0441.wav
```

**What to listen for:**
- ✅ Enhanced version has less background noise
- ✅ Volume is more consistent
- ✅ Both sentences are present (no skips from Phase 4 fix)
- ✅ No distortion or artifacts

---

## 🧪 **Test 3: Full Phase 5 Pipeline**
```bash
# Run full Phase 5 (all ~500 chunks)
cd ..\phase6_orchestrator

python orchestrator.py ..\input\The_Analects_of_Confucius_20240228.pdf --phases 5 --pipeline-json ..\pipeline.json
```

**Expected runtime:** ~25-40 minutes

**Monitor progress:**
Open another terminal:
```bash
cd ..\phase5_enhancement
Get-Content audio_enhancement.log -Wait -Tail 20
```

**Expected output:**
```
Processing 500 audio chunks in parallel...
Volume normalized chunk 0: RMS 0.0234 → 0.1234
Saved enhanced chunk: processed/enhanced_0000.wav
...
Creating final audiobook...
Final audiobook created: processed/audiobook.mp3
Duration: 3600.5 seconds
Enhancement complete: 500 successful, 0 failed
```

---

## 🧪 **Test 4: Final Audiobook**
```bash
cd ..\phase5_enhancement

# Play the final audiobook!
start processed\audiobook.mp3
```

**Quality checklist:**
- ✅ Smooth transitions between chunks (no pops/clicks)
- ✅ Consistent volume throughout
- ✅ Reduced background noise
- ✅ All content present (no missing sentences)
- ✅ Natural speech rhythm

**Check file size:**
```bash
Get-Item processed\audiobook.mp3 | Select-Object Length, LastWriteTime
```

**Expected size:** 50-150 MB (depends on book length)

---

## 🧪 **Test 5: Verify Metadata**
```bash
# Check Phase 5 results in pipeline.json
python -c "import json; p=json.load(open('../pipeline.json')); phase5=p.get('phase5',{}); print(f\"Status: {phase5.get('status')}\"); print(f\"Successful: {phase5.get('metrics',{}).get('successful')}\"); print(f\"Failed: {phase5.get('metrics',{}).get('failed')}\"); print(f\"SNR Improvement: {phase5.get('metrics',{}).get('avg_snr_improvement',0):.1f} dB\")"
```

**Expected output:**
```
Status: success
Successful: 500  (or close to it)
Failed: 0  (or very few)
SNR Improvement: 2.5-8.0 dB  (positive number = noise reduced!)
```

---

## ✅ **SUCCESS CRITERIA**

All fixes are working if:

1. **MOS Scores**: 3.5-4.8 (not 0.13)
2. **Enhanced Audio**: Noticeably cleaner than Phase 4 originals
3. **File Size**: Chunks are ~24kHz (not unnecessarily upsampled to 48kHz)
4. **Final Audiobook**: Sounds professional with smooth transitions
5. **No Errors**: Pipeline.json shows `"status": "success"` for Phase 5

---

## ❌ **IF SOMETHING FAILS**

### **Error: "Enhanced audio sounds identical to original"**
**Possible Cause**: Old Phase 5 code still cached  
**Fix**:
```bash
cd phase5_enhancement
poetry install --no-root  # Reinstall dependencies
```

### **Error: "MOS score still 0.13"**
**Possible Cause**: Old Phase 4 code cached  
**Fix**:
```bash
cd phase4_tts
conda activate phase4_tts
# Restart Conda shell and try again
```

### **Error: "ImportError: cannot import name 'Image'"**
**Possible Cause**: PIL not installed in Phase 2 environment  
**Fix**:
```bash
cd phase2-extraction
poetry add pillow
poetry install --no-root
```

---

## 📊 **BEFORE/AFTER COMPARISON**

### **Phase 4 MOS Score**
- **Before Fix**: 0.13 (broken formula)
- **After Fix**: 3.5-4.5 (accurate acoustic analysis)

### **Phase 5 Enhancement**
- **Before Fix**: Copies Phase 4 audio (no enhancement)
- **After Fix**: Actually applies noise reduction + LUFS normalization

### **Phase 5 File Size**
- **Before Fix**: 2x larger (48kHz upsampling)
- **After Fix**: Correct size (24kHz, matches Phase 4)

### **EasyOCR (Scanned PDFs)**
- **Before Fix**: Crashes or returns garbage
- **After Fix**: Correctly extracts text from images

---

## 🎯 **RECOMMENDED WORKFLOW**

1. **Run Test 1** (Phase 4 MOS) → Verify score is ~4.0
2. **Run Test 2** (Single chunk Phase 5) → Listen and compare
3. **If Tests 1-2 pass**: Run Test 3 (Full Phase 5)
4. **Listen to final audiobook** (Test 4)
5. **Check metrics** (Test 5)

Total time: ~45 minutes (including Phase 5 full run)

---

**Ready to test! Start with Test 1 and report back with results.**
