# Quick Test Commands - Phase 5 Clipping Fix

## Verify Configuration
```powershell
cd C:\Users\myson\Pipeline\audiobook-pipeline\phase5_enhancement
python verify_fix.py
```

Expected output: ✅ ALL CHECKS PASSED

---

## Test Single Chunk (Recommended First)
```powershell
# Clear old output
Remove-Item -Recurse -Force processed/* -ErrorAction SilentlyContinue

# Run enhancement on chunk 0
poetry run python src\phase5_enhancement\main.py --chunk_id 0 --skip_concatenation

# Listen to result
start processed\enhanced_0000.wav
```

**What to check:**
- No sharp pops or clicks
- Natural, smooth audio
- No distortion
- Even volume

---

## Check Logs for Clipping Warnings
```powershell
# View recent log entries
Get-Content audio_enhancement.log -Tail 50 | Select-String "Clipping|warning|error"
```

**Good result:** Few or no "Clipping detected" warnings

---

## Run Full Phase 5 Pipeline
```powershell
cd ..\phase6_orchestrator

# Process all Phase 4 chunks
python orchestrator.py `
  "../input/The_Analects_of_Confucius_20240228.pdf" `
  --phases 5 `
  --pipeline-json="../pipeline.json"
```

---

## Inspect Final Output
```powershell
# Play the final audiobook
start ..\phase5_enhancement\processed\audiobook.mp3

# Check file info
ffprobe -i ..\phase5_enhancement\processed\audiobook.mp3
```

---

## Compare Before/After

### Before Fix (if you saved old output):
```powershell
start ..\phase5_enhancement\processed_old\enhanced_0000.wav
```

### After Fix:
```powershell
start ..\phase5_enhancement\processed\enhanced_0000.wav
```

Listen for reduction in clipping/distortion.

---

## Troubleshooting

### If clipping persists:
```powershell
# Option 1: Lower LUFS target further
# Edit config.yaml: lufs_target: -20.0

# Option 2: Disable volume normalization
# Edit config.yaml: enable_volume_normalization: false

# Option 3: Reduce noise reduction more
# Edit config.yaml: noise_reduction_factor: 0.1
```

### Check Phase 4 output quality:
```powershell
# Listen to Phase 4 raw output
start ..\phase4_tts\audio_chunks\chunk_0000.wav

# If this has clipping, need to fix Phase 4, not Phase 5
```

---

## Success Criteria

✅ No clipping warnings in logs  
✅ Audio sounds clean and natural  
✅ Volume is consistent across chunks  
✅ No distortion or harshness  
✅ LUFS around -18.0 dB (±2dB)  
✅ Final audiobook.mp3 plays smoothly  

---

Ready to test? Start with the **Verify Configuration** step!
