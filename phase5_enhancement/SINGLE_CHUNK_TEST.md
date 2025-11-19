# Phase 5 Single Chunk Test - FIXED

## ✅ Bug Fixed
The `--chunk_id` parameter now works correctly!

**What was wrong:**
- Phase 5 was looking for `chunk_0.wav` 
- Phase 4 outputs `chunk_0000.wav` (with zero-padding)
- Resume logic was filtering out the single chunk

**What's fixed:**
- Now uses correct zero-padded format: `chunk_{id:04d}.wav`
- Single chunk mode bypasses resume logic
- Better error messages showing where it's looking

---

## 🧪 Test Single Chunk Now

```powershell
cd path\to\audiobook-pipeline-styletts-personal\phase5_enhancement

# Verify config
python verify_fix.py

# Clear old output
Remove-Item -Recurse -Force processed/* -ErrorAction SilentlyContinue

# Test chunk 0 (first chunk)
poetry run python src\phase5_enhancement\main.py --chunk_id 0 --skip_concatenation

# Listen to result
start processed\enhanced_0000.wav
```

---

## 📊 What to Check

### 1. Console Output
You should see:
```
Processing single chunk: ..\phase4_tts\audio_chunks\chunk_0000.wav
Single chunk mode: Processing chunk 0 only
Processing 1 audio chunks in parallel...
Volume normalized chunk 0: RMS X.XXXX → X.XXXX
```

### 2. Audio Quality
Listen for:
- ✅ No sharp pops or clicks
- ✅ Clean, natural speech
- ✅ No distortion
- ✅ Smooth volume

### 3. Log File
```powershell
# Check last few entries
Get-Content audio_enhancement.log -Tail 30
```

Look for:
- Volume normalization applied
- Clipping warnings (should be 0-2 max)
- LUFS around -18.0 dB
- SNR improvement shown

---

## 🎯 Success Criteria

✅ Only 1 file created: `processed\enhanced_0000.wav`  
✅ No errors in console  
✅ Audio sounds clean (no clipping artifacts)  
✅ Processing completes in ~5-10 seconds  

---

## 🔄 Test Different Chunks

```powershell
# Test chunk 1
poetry run python src\phase5_enhancement\main.py --chunk_id 1 --skip_concatenation

# Test chunk 441 (the problematic one from earlier)
poetry run python src\phase5_enhancement\main.py --chunk_id 441 --skip_concatenation

# Listen to each
start processed\enhanced_0001.wav
start processed\enhanced_0441.wav
```

---

## 📝 Next Steps After Single Chunk Success

Once a single chunk sounds good:

### Option 1: Process All Chunks (Recommended)
```powershell
cd ..\phase6_orchestrator
python orchestrator.py "../input/The_Analects_of_Confucius_20240228.pdf" --phases 5 --pipeline-json="../pipeline.json"
```

### Option 2: Process Just Phase 4 + 5 Together
```powershell
# This will run Phase 4 first (with 80-char splitting), then Phase 5
python orchestrator.py "../input/The_Analects_of_Confucius_20240228.pdf" --phases 4 5 --pipeline-json="../pipeline.json"
```

---

## 🚨 Troubleshooting

### "Chunk file not found"
**Check Phase 4 output:**
```powershell
ls ..\phase4_tts\audio_chunks | Select-String "chunk_0000"
```

If no files exist, run Phase 4 first:
```powershell
cd ..\phase6_orchestrator
python orchestrator.py "../input/The_Analects_of_Confucius_20240228.pdf" --phases 4 --pipeline-json="../pipeline.json"
```

### Audio still has clipping
Try even more conservative settings in `config.yaml`:
```yaml
lufs_target: -20.0          # Even quieter
noise_reduction_factor: 0.1 # Almost no noise reduction
volume_norm_headroom: 0.5   # Maximum headroom
```

---

Ready to test! Run the commands above and report back how it sounds! 🎧


