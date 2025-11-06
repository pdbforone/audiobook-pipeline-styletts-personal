# Quick Start Testing Guide - Voice Override System

## 🚀 5-Minute Test

This guide helps you verify the voice override system is working correctly.

---

## Prerequisites

1. ✅ Phase 3 and Phase 4 code updated
2. ✅ `configs/voices.json` exists (root directory)
3. ✅ `phase4_tts/configs/voice_references.json` exists
4. ✅ Poetry environments set up

---

## Test 1: List Available Voices

```powershell
cd phase3-chunking
poetry run python -m phase3_chunking.voice_selection --list
```

**Expected Output:**
```
============================================================
Available Voices:
============================================================

🎤 landon_elkind
   Measured, analytical tone for philosophy (Bertrand Russell reader)
   Profiles: philosophy, academic

🎤 tom_weiss
   Engaging male narrator for thrillers and suspense
   Profiles: fiction

... (14 voices total)

Default voice: neutral_narrator
```

✅ **Pass Criteria:** Shows 14 voices with descriptions

---

## Test 2: Voice Details

```powershell
poetry run python -m phase3_chunking.voice_selection --info landon_elkind
```

**Expected Output:**
```
🎤 landon_elkind
============================================================
Description: Measured, analytical tone for philosophy (Bertrand Russell reader)
Narrator: Landon D. C. Elkind
Source: LibriVox - Mysticism and Logic
Profiles: philosophy, academic
TTS Params: {'pitch': -1, 'rate': 0.95, 'emphasis': 'moderate'}
```

✅ **Pass Criteria:** Shows complete voice information

---

## Test 3: Phase 3 Voice Selection (Auto)

```powershell
# Create a test text file first
cd ..
echo "This is a test of the voice selection system. Philosophy and wisdom." > test_philosophy.txt

cd phase3-chunking
poetry run python -m phase3_chunking.main `
  --file_id test_auto `
  --text_path ../test_philosophy.txt `
  --verbose
```

**Look for in logs:**
```
INFO: Voice selection: landon_elkind (Profile match (philosophy → landon_elkind))
```

**Verify in pipeline.json:**
```powershell
cd ..
jq ".phase3.files.test_auto.chunk_metrics.selected_voice" pipeline.json
```

**Expected:** `"landon_elkind"` or another philosophy voice

✅ **Pass Criteria:** Voice automatically selected based on content

---

## Test 4: CLI Voice Override

```powershell
cd phase3-chunking
poetry run python -m phase3_chunking.main `
  --file_id test_cli `
  --text_path ../test_philosophy.txt `
  --voice tom_weiss `
  --verbose
```

**Look for in logs:**
```
INFO: Using CLI voice override: tom_weiss
INFO: Voice selection: tom_weiss (CLI override (--voice tom_weiss))
```

**Verify in pipeline.json:**
```powershell
cd ..
jq ".phase3.files.test_cli.chunk_metrics.selected_voice" pipeline.json
```

**Expected:** `"tom_weiss"`

✅ **Pass Criteria:** CLI override takes priority over auto-detection

---

## Test 5: Set File-Level Override

```powershell
cd phase3-chunking
poetry run python -m phase3_chunking.voice_selection `
  --set-file test_file ruth_golding `
  --pipeline ../pipeline.json
```

**Expected Output:**
```
✅ Set file-level override: test_file → ruth_golding
```

**Verify in pipeline.json:**
```powershell
cd ..
jq ".voice_overrides.test_file" pipeline.json
```

**Expected:** `"ruth_golding"`

✅ **Pass Criteria:** File-level override saved in pipeline.json

---

## Test 6: Use File-Level Override

```powershell
cd phase3-chunking
poetry run python -m phase3_chunking.main `
  --file_id test_file `
  --text_path ../test_philosophy.txt `
  --verbose
```

**Look for in logs:**
```
INFO: Voice selection: ruth_golding (File-level override for test_file)
```

**Verify:**
```powershell
cd ..
jq ".phase3.files.test_file.chunk_metrics.selected_voice" pipeline.json
```

**Expected:** `"ruth_golding"`

✅ **Pass Criteria:** File-level override used automatically

---

## Test 7: Set Global Override

```powershell
cd phase3-chunking
poetry run python -m phase3_chunking.voice_selection `
  --set-global david_barnes `
  --pipeline ../pipeline.json
```

**Expected Output:**
```
✅ Set global voice override: david_barnes
```

**Verify:**
```powershell
cd ..
jq ".tts_voice" pipeline.json
```

**Expected:** `"david_barnes"`

✅ **Pass Criteria:** Global override saved

---

## Test 8: Global Override Works

```powershell
cd phase3-chunking
poetry run python -m phase3_chunking.main `
  --file_id test_global `
  --text_path ../test_philosophy.txt `
  --verbose
```

**Look for in logs:**
```
INFO: Voice selection: david_barnes (Global override (tts_voice))
```

✅ **Pass Criteria:** Global override applies to all files

---

## Test 9: Clear Overrides

```powershell
# Clear global
poetry run python -m phase3_chunking.voice_selection `
  --clear-global `
  --pipeline ../pipeline.json

# Clear file-level
poetry run python -m phase3_chunking.voice_selection `
  --clear-file test_file `
  --pipeline ../pipeline.json
```

**Expected Output:**
```
✅ Cleared global voice override
✅ Cleared file-level override for test_file
```

**Verify:**
```powershell
cd ..
jq ".tts_voice" pipeline.json
# Expected: null

jq ".voice_overrides.test_file" pipeline.json
# Expected: null
```

✅ **Pass Criteria:** Overrides removed from pipeline.json

---

## Test 10: Phase 4 Voice Reference Preparation

```powershell
cd phase4_tts

# Run Phase 4 (will download voice references on first run)
poetry run python src/main.py `
  --file_id test_auto `
  --json_path ../pipeline.json
```

**First run expected output:**
```
INFO: Preparing voice references...
INFO: Preparing reference for landon_elkind...
INFO: Downloading from: https://archive.org/download/...
✅ Prepared landon_elkind: voice_references/landon_elkind.wav (20.0s)
INFO: Preparing reference for tom_weiss...
... (repeats for all 14 voices - takes 3-5 minutes)
INFO: Prepared 14/14 voice references
INFO: Phase 3 selected voice: landon_elkind
✅ Using voice: landon_elkind (voice_references/landon_elkind.wav)
```

**Subsequent runs:**
```
INFO: Preparing voice references...
INFO: Using existing reference: landon_elkind (20.0s)
INFO: Using existing reference: tom_weiss (18.5s)
... (instant, uses cache)
INFO: Prepared 14/14 voice references
✅ Using voice: landon_elkind (voice_references/landon_elkind.wav)
```

**Verify voice references cached:**
```powershell
ls voice_references/
```

**Expected:** 14 `.wav` files (one per voice)

✅ **Pass Criteria:**
- Downloads complete successfully
- All 14 voices cached
- Correct voice used for synthesis

---

## Test 11: Phase 4 Uses Phase 3 Voice

```powershell
# First, run Phase 3 with specific voice
cd ../phase3-chunking
poetry run python -m phase3_chunking.main `
  --file_id test_integration `
  --text_path ../test_philosophy.txt `
  --voice bella_bolster

# Then run Phase 4
cd ../phase4_tts
poetry run python src/main.py `
  --file_id test_integration `
  --json_path ../pipeline.json
```

**Look for in Phase 4 logs:**
```
INFO: Phase 3 selected voice: bella_bolster
✅ Using voice: bella_bolster (voice_references/bella_bolster.wav)
```

**Verify in pipeline.json:**
```powershell
cd ..
jq ".phase4.files.test_integration" pipeline.json | grep selected_voice
```

**Expected:** `"selected_voice": "bella_bolster"` in Phase 4 output

✅ **Pass Criteria:** Phase 4 reads and uses voice from Phase 3

---

## 🎯 Complete Test Checklist

Run all tests above, then check off:

- [ ] Test 1: List voices works
- [ ] Test 2: Voice details shows info
- [ ] Test 3: Auto voice selection works
- [ ] Test 4: CLI override works
- [ ] Test 5: File-level override sets correctly
- [ ] Test 6: File-level override used automatically
- [ ] Test 7: Global override sets correctly
- [ ] Test 8: Global override applies to all files
- [ ] Test 9: Overrides clear successfully
- [ ] Test 10: Phase 4 downloads and caches 14 voices
- [ ] Test 11: Phase 4 uses voice from Phase 3

**All tests passing?** ✅ Voice override system is fully functional!

---

## 🐛 Common Issues

### Issue: "Invalid voice ID"
```powershell
# List valid voices
poetry run python -m phase3_chunking.voice_selection --list
```

### Issue: ModuleNotFoundError
```powershell
# Reinstall dependencies
cd phase3-chunking
poetry install

cd ../phase4_tts
poetry install
```

### Issue: Voice reference download fails
**Check:**
1. Internet connection
2. LibriVox is accessible
3. URLs in `phase4_tts/configs/voice_references.json` are valid

**Workaround:** Manually download and place in `phase4_tts/voice_references/`

### Issue: Phase 4 doesn't use correct voice
**Debug:**
```powershell
# Check Phase 3 output
jq ".phase3.files.FILE_ID.chunk_metrics.selected_voice" pipeline.json

# Check Phase 4 logs
poetry run python src/main.py --file_id FILE_ID --json_path ../pipeline.json 2>&1 | grep "selected voice"
```

---

## 📝 Quick Command Reference

```powershell
# List voices
poetry run python -m phase3_chunking.voice_selection --list

# Voice info
poetry run python -m phase3_chunking.voice_selection --info VOICE_ID

# Set overrides
poetry run python -m phase3_chunking.voice_selection --set-global VOICE_ID
poetry run python -m phase3_chunking.voice_selection --set-file FILE_ID VOICE_ID

# Clear overrides
poetry run python -m phase3_chunking.voice_selection --clear-global
poetry run python -m phase3_chunking.voice_selection --clear-file FILE_ID

# Run with voice
poetry run python -m phase3_chunking.main --file_id ID --voice VOICE_ID
```

---

## ✅ Success Criteria

**System is working when:**
1. ✅ All 14 voices listed and accessible
2. ✅ Voice selection priority cascade works correctly
3. ✅ Overrides save to and load from pipeline.json
4. ✅ Phase 4 downloads and caches voice references
5. ✅ Phase 4 uses correct voice from Phase 3 selection
6. ✅ Generated audio uses cloned voice successfully

**Ready for production!** 🎉
