# Quick Test - Phase 4 Fix

## 1. Check Phase 3 Output (10 seconds)
```bash
cd path\to\audiobook-pipeline-styletts-personal\phase6_orchestrator
python check_phase3_output.py
```

**Expected:** Shows the actual file_id Phase 3 used and chunk count

## 2. Test Phase 4 (varies by chunk count)
```bash
python orchestrator.py "path\to\The Analects of Confucius.pdf" --phases 4
```

**What to Look For:**
```
[INFO] Using Phase 3 key: 'The_Analects_of_Confucius_20240228_converted_with_pdfplumber'
[INFO] Processing 109 chunks for file_id='...'
[INFO]   Chunk 1/109
[INFO]   Chunk 1 OK
```

## 3. If It Works
✅ Phase 4 finds chunks  
✅ Processes with greenman_ref.wav  
✅ Creates audio_chunks/*.wav files  
✅ Updates pipeline.json with Phase 4 results  

## 4. If It Fails
❌ Run diagnostic: `python check_phase3_output.py`  
❌ Check Phase 3 completed: `python orchestrator.py file.pdf --phases 3`  
❌ Verify conda env: `conda env list | findstr phase4_tts`  
❌ Check greenman_ref.wav exists in phase4_tts/  

## Changes Made
1. **Smart file_id matching** - finds Phase 3 output even if key doesn't match exactly
2. **Auto ref_file** - uses greenman_ref.wav automatically
3. **Better logging** - shows exactly what file_id is being used

That's it! Test now with: `python check_phase3_output.py`


