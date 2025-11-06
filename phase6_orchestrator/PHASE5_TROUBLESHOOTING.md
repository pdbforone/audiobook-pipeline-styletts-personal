# Phase 5 Troubleshooting Guide

## Quick Check: Did Phase 5 Work?

Run this first to see what actually happened:

```powershell
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator
poetry run python check_phase5_results.py
```

This will tell you:
- ✅ How many chunks were processed
- ✅ Whether audiobook.mp3 was created
- ✅ If any chunks are missing

## Two Ways to Run Phase 5

### Option 1: Normal Mode (via Orchestrator)

**When to use:** Pipeline is working correctly, you want proper state tracking.

```powershell
.\test_phase5_fix.bat
```

**What it does:**
- Clears old Phase 5 data from pipeline.json
- Disables resume_on_failure
- Processes all chunks
- Updates pipeline.json with results

**Pros:**
- Proper state tracking
- Integrates with full pipeline
- Good for debugging

**Cons:**
- More complex
- Relies on pipeline.json being correct

### Option 2: Direct Mode (Bypass Pipeline)

**When to use:** Pipeline.json is causing issues, you just want the audiobook NOW.

```powershell
.\run_phase5_direct.bat
```

**What it does:**
- **Ignores pipeline.json completely**
- Scans phase4_tts/audio_chunks/ for ALL .wav files
- Processes every file found (no skipping!)
- Creates audiobook.mp3

**Pros:**
- Simple and reliable
- No pipeline.json dependencies
- Always processes ALL audio files
- Can't be confused by old state

**Cons:**
- Doesn't update pipeline.json
- Bypasses quality checks (processes everything)

## Decision Tree

```
Did Phase 5 complete successfully?
├─ YES → Run check_phase5_results.py to verify
│   ├─ All 637 chunks processed? → ✅ Done! Listen to audiobook.mp3
│   └─ Some chunks missing? → Use Direct Mode
│
└─ NO → Use Direct Mode
```

## Common Issues

### Issue: Phase 5 skips chunks

**Symptom:** Only processes ~300 chunks instead of 637

**Cause:** Old data in pipeline.json causing resume logic to skip "completed" chunks

**Solution:** Run `test_phase5_fix.bat` (already includes the fix!)

### Issue: Pipeline.json corruption

**Symptom:** Weird errors about JSON parsing or missing keys

**Cause:** pipeline.json is malformed or has conflicting data

**Solution:** Use Direct Mode - it doesn't use pipeline.json at all!

### Issue: "Audio file not found" errors

**Symptom:** Phase 5 can't find audio files even though they exist

**Cause:** Path mismatch between pipeline.json and actual file locations

**Solution:** Use Direct Mode - it scans the actual directory!

## File Locations

After Phase 5 runs successfully:

```
phase5_enhancement/
├── processed/
│   ├── enhanced_0000.wav
│   ├── enhanced_0001.wav
│   ├── ...
│   └── enhanced_0636.wav      ← Should have 637 files total
│
└── output/
    └── audiobook.mp3           ← Final audiobook
```

## Verification

To verify Phase 5 worked correctly:

1. **Check chunk count:**
   ```powershell
   cd ..\phase5_enhancement\processed
   (Get-ChildItem enhanced_*.wav).Count
   ```
   Should output: `637`

2. **Check audiobook exists:**
   ```powershell
   cd ..\output
   Test-Path audiobook.mp3
   ```
   Should output: `True`

3. **Check audiobook size:**
   ```powershell
   (Get-Item audiobook.mp3).Length / 1MB
   ```
   Should output: ~50-100 MB (depends on bitrate)

## What's the Difference?

| Feature | Normal Mode | Direct Mode |
|---------|------------|-------------|
| Uses pipeline.json | ✅ Yes | ❌ No |
| Resume capability | ✅ Yes (if enabled) | ❌ Always fresh |
| Quality filtering | ✅ Yes (if enabled) | ❌ Processes everything |
| State tracking | ✅ Updates JSON | ❌ No tracking |
| Reliability | ⚠️ Depends on JSON | ✅ Very reliable |
| Speed | ⚠️ Same | ⚠️ Same |
| Use case | Production pipeline | Quick workaround |

## Recommendation

1. **First time:** Try Normal Mode (`test_phase5_fix.bat`)
2. **If it fails:** Use Direct Mode (`run_phase5_direct.bat`)
3. **For production:** Fix the pipeline, use Normal Mode
4. **For one-offs:** Direct Mode is fine

## Future Pipeline Runs

The orchestrator fixes have been applied, so **future pipeline runs should work correctly**. The Direct Mode is a safety net for this specific run if needed.

When you run the full pipeline next time:

```powershell
poetry run python orchestrator.py "..\input\your_book.pdf"
```

Phase 5 will automatically:
- Clear old data
- Disable resume
- Process all chunks

So you shouldn't need Direct Mode anymore!
