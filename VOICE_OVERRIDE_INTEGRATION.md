# Voice Override System - Integration Summary

## ✅ What We've Built

You now have a **complete multi-level voice override system** that spans Phases 3 and 4, with 14 distinct narrator voices from LibriVox covering philosophy, fiction, poetry, theology, and more.

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     VOICE SELECTION FLOW                        │
└─────────────────────────────────────────────────────────────────┘

PHASE 3 (Chunking)                       PHASE 4 (TTS Synthesis)
═══════════════════                      ═══════════════════════

1. User runs Phase 3                     6. Read voice from Phase 3
   --voice CLI flag (optional) ────┐        chunk_metrics.selected_voice
                                    │
2. Load pipeline.json ──────────────┤     7. Prepare voice references
   - voice_overrides (file-level)   │        Download from LibriVox
   - tts_voice (global)             │        Cache in voice_references/
                                    │
3. Select voice (priority cascade) ─┤     8. Map voice → reference WAV
   └→ voice_selection.py            │        landon_elkind → landon_elkind.wav
                                    │
4. Store in chunk_metrics ──────────┤     9. Load Chatterbox TTS model
   chunk_metrics.selected_voice     │        CPU-only mode
                                    │
5. Write to pipeline.json ──────────┘    10. Synthesize with voice clone
                                             audio_prompt_path = ref WAV
```

---

## 🗂️ File Structure

```
audiobook-pipeline-chatterbox/
│
├── configs/
│   └── voices.json                      # 14 narrator definitions
│
├── phase3-chunking/
│   └── src/phase3_chunking/
│       ├── voice_selection.py           # ✨ Enhanced with overrides
│       └── main.py                      # ✨ Integrated voice selection
│
├── phase4_tts/
│   ├── configs/
│   │   └── voice_references.json        # ✨ LibriVox audio sources
│   ├── src/
│   │   ├── utils.py                     # ✨ Multi-voice prep functions
│   │   └── main.py                      # ✨ Integrated voice system
│   └── voice_references/                # ✨ Cached audio samples
│       ├── landon_elkind.wav
│       ├── tom_weiss.wav
│       └── ... (14 total)
│
├── pipeline.json                        # State + voice overrides
├── VOICE_OVERRIDE_USAGE_GUIDE.md        # ✨ User guide
└── VOICE_OVERRIDE_INTEGRATION.md        # ✨ This file
```

---

## 🎯 Available Voices (14 Total)

### Philosophy & Academic (4)
- **landon_elkind** - Measured British RP (Bertrand Russell)
- **pamela_nagami** - Clear authoritative female (Modern Philosophy)
- **hugh_mcguire** - Classical philosophy (Boethius)
- **david_barnes** - BBC English (John Donne poetry)

### Fiction (4)
- **tom_weiss** - Dynamic thriller narrator
- **bella_bolster** - Horror/dark fiction female
- **kara_shallenberg** - Classic fiction/romance (Pride & Prejudice)
- **ruth_golding** - British RP female (Jane Austen)

### Poetry (1)
- **gareth_holmes** - British epic poetry

### Theology (2)
- **wayne_cooke** - Rational theology
- **eric_metzler** - Medieval mysticism

### British Accents (3)
- **cori_samuel** - RP/Estuary English female
- **peter_yearsley** - London male
- *(plus ruth_golding, david_barnes, gareth_holmes above)*

### Default (1)
- **neutral_narrator** - Fallback professional voice

---

## ⚙️ How It Works: Step-by-Step

### Scenario 1: Automatic Voice Selection (No Overrides)

```powershell
# Step 1: Run Phase 3 with auto genre detection
poetry run python -m phase3_chunking.main --file_id meditations
```

**What happens:**
1. Phase 3 detects genre → "philosophy"
2. `voice_selection.py` matches → `landon_elkind` (first philosophy voice)
3. Saves to pipeline.json:
   ```json
   {
     "phase3": {
       "files": {
         "meditations": {
           "chunk_metrics": {
             "selected_voice": "landon_elkind"
           }
         }
       }
     }
   }
   ```

```powershell
# Step 2: Run Phase 4 TTS synthesis
poetry run python src/main.py --file_id meditations --json_path ../pipeline.json
```

**What happens:**
1. Phase 4 runs `prepare_voice_references()` → Downloads all 14 voices (or uses cache)
2. Reads `chunk_metrics.selected_voice` → `"landon_elkind"`
3. Uses `voice_references/landon_elkind.wav` for voice cloning
4. Synthesizes all chunks with Landon Elkind's voice

---

### Scenario 2: CLI Override (Quick Test)

```powershell
# Override just for this run
poetry run python -m phase3_chunking.main `
  --file_id meditations `
  --voice tom_weiss  # Fiction narrator for philosophy book!
```

**What happens:**
1. CLI override takes priority
2. Phase 3 uses `tom_weiss` instead of auto-detected `landon_elkind`
3. Saves to pipeline.json: `"selected_voice": "tom_weiss"`
4. Phase 4 uses Tom Weiss's voice for TTS

---

### Scenario 3: File-Level Override (Permanent)

```powershell
# Step 1: Set permanent override for this book
python -m phase3_chunking.voice_selection `
  --set-file meditations landon_elkind `
  --pipeline pipeline.json
```

**Updates pipeline.json:**
```json
{
  "voice_overrides": {
    "meditations": "landon_elkind"
  }
}
```

```powershell
# Step 2: Run Phase 3 (uses override automatically)
poetry run python -m phase3_chunking.main --file_id meditations
```

**What happens:**
1. Phase 3 checks `voice_overrides.meditations` → `"landon_elkind"`
2. Uses that voice (ignores auto-detection)
3. Every future run uses `landon_elkind` until override is cleared

---

### Scenario 4: Global Override (All Books)

```powershell
# Set one voice for everything
python -m phase3_chunking.voice_selection `
  --set-global ruth_golding `
  --pipeline pipeline.json
```

**Updates pipeline.json:**
```json
{
  "tts_voice": "ruth_golding"
}
```

```powershell
# All books now use Ruth Golding
poetry run python -m phase3_chunking.main --file_id book1
poetry run python -m phase3_chunking.main --file_id book2
poetry run python -m phase3_chunking.main --file_id book3
```

---

## 🔄 Voice Selection Priority Cascade

Phase 3 checks in this order:

```
1. --voice CLI flag                    (Highest - temporary)
2. voice_overrides.{file_id}           (Per-book permanent)
3. tts_voice                           (Global permanent)
4. Genre profile match                 (Automatic)
5. default_voice (neutral_narrator)    (Lowest - fallback)
```

**Example:**
```powershell
# If you have:
# - Global: tts_voice = "ruth_golding"
# - File-level: voice_overrides.meditations = "landon_elkind"
# - CLI: --voice tom_weiss

poetry run python -m phase3_chunking.main `
  --file_id meditations `
  --voice tom_weiss

# Result: Uses tom_weiss (CLI wins)
```

---

## 🛠️ Management Commands

### List Voices
```powershell
# All voices
python -m phase3_chunking.voice_selection --list

# Filter by genre
python -m phase3_chunking.voice_selection --list --profile philosophy
python -m phase3_chunking.voice_selection --list --profile fiction
```

### Voice Details
```powershell
python -m phase3_chunking.voice_selection --info landon_elkind
```

**Output:**
```
🎤 landon_elkind
============================================================
Description: Measured, analytical tone for philosophy
Narrator: Landon D. C. Elkind
Source: Mysticism and Logic by Bertrand Russell
Profiles: philosophy, academic
TTS Params: {'pitch': -1, 'rate': 0.95}
```

### Set Overrides
```powershell
# Global
python -m phase3_chunking.voice_selection `
  --set-global VOICE_ID

# Per-file
python -m phase3_chunking.voice_selection `
  --set-file FILE_ID VOICE_ID
```

### Clear Overrides
```powershell
# Clear global
python -m phase3_chunking.voice_selection --clear-global

# Clear file-level
python -m phase3_chunking.voice_selection --clear-file FILE_ID
```

---

## 📦 Phase 4 Voice Reference Caching

### First Run
```powershell
poetry run python src/main.py --file_id test --json_path ../pipeline.json
```

**What happens:**
1. Downloads 14 voice samples from LibriVox (~3-5 minutes)
2. Trims to 10-30 seconds each
3. Normalizes and resamples to 24kHz
4. Caches in `voice_references/` directory

**Output:**
```
INFO: Preparing voice references...
INFO: Preparing reference for landon_elkind...
INFO: Downloading from: https://archive.org/download/...
✅ Prepared landon_elkind: voice_references/landon_elkind.wav (20.0s)
INFO: Preparing reference for tom_weiss...
... (repeats for all 14 voices)
INFO: Prepared 14/14 voice references
```

### Subsequent Runs
```
INFO: Preparing voice references...
INFO: Using existing reference: landon_elkind (20.0s)
INFO: Using existing reference: tom_weiss (18.5s)
... (instant, uses cache)
INFO: Prepared 14/14 voice references
✅ Using voice: landon_elkind (voice_references/landon_elkind.wav)
```

---

## 🔍 Verification & Testing

### 1. Test Voice Selection in Phase 3
```powershell
# Auto-detection
poetry run python -m phase3_chunking.main `
  --file_id test `
  --text_path "C:\path\to\test.txt" `
  --verbose

# Check logs for:
# "Voice selection: landon_elkind (Profile match (philosophy → landon_elkind))"
```

### 2. Test CLI Override
```powershell
poetry run python -m phase3_chunking.main `
  --file_id test `
  --text_path "C:\path\to\test.txt" `
  --voice tom_weiss `
  --verbose

# Check logs for:
# "Using CLI voice override: tom_weiss"
# "Voice selection: tom_weiss (CLI override (--voice tom_weiss))"
```

### 3. Verify pipeline.json
```powershell
# Check Phase 3 output
jq ".phase3.files.test.chunk_metrics.selected_voice" pipeline.json
# Expected: "tom_weiss"
```

### 4. Test Phase 4 Integration
```powershell
poetry run python src/main.py `
  --file_id test `
  --json_path ../pipeline.json `
  --verbose

# Check logs for:
# "Phase 3 selected voice: tom_weiss"
# "✅ Using voice: tom_weiss (voice_references/tom_weiss.wav)"
```

---

## 🐛 Troubleshooting

### Issue: "Invalid voice ID"
```
ERROR: Invalid voice ID: unknown_voice
```

**Fix:**
```powershell
# List valid voices
python -m phase3_chunking.voice_selection --list
```

### Issue: Voice reference download fails
```
ERROR: Download failed for landon_elkind: HTTPError 404
```

**Fix:**
1. Check internet connection
2. Verify LibriVox URLs in `voice_references.json`
3. Manually download and place in `voice_references/landon_elkind.wav`

### Issue: Phase 4 uses wrong voice
```
WARNING: Voice 'custom_voice' not found, using neutral_narrator
```

**Fix:**
1. Check Phase 3 output: `jq ".phase3.files.FILE_ID.chunk_metrics.selected_voice" pipeline.json`
2. Verify voice exists: `ls voice_references/`
3. Re-run Phase 3 with correct voice

---

## 🚀 Next Steps

### Add Custom Voice

1. **Record/find 10-30 seconds of clean narration**

2. **Add to `configs/voices.json`:**
```json
{
  "voices": {
    "my_narrator": {
      "description": "Custom voice description",
      "narrator_name": "Narrator Name",
      "preferred_profiles": ["fiction"],
      "tts_engine_params": {}
    }
  }
}
```

3. **Add to `phase4_tts/configs/voice_references.json`:**
```json
{
  "voice_references": {
    "my_narrator": {
      "source_url": "https://yoursite.com/audio.mp3",
      "trim_start": 0,
      "trim_end": 20,
      "preferred_profiles": ["fiction"]
    }
  }
}
```

4. **Test:**
```powershell
python -m phase3_chunking.main --file_id test --voice my_narrator
```

---

## 📝 Complete Workflow Example

```powershell
# 1. List available voices
python -m phase3_chunking.voice_selection --list --profile philosophy

# 2. Set file-level override for "Meditations"
python -m phase3_chunking.voice_selection `
  --set-file meditations landon_elkind

# 3. Run Phase 3 (uses landon_elkind automatically)
poetry run python -m phase3_chunking.main --file_id meditations

# 4. Verify voice selection
jq ".phase3.files.meditations.chunk_metrics.selected_voice" pipeline.json

# 5. Run Phase 4 (downloads voice ref if first time, then uses cache)
cd phase4_tts
poetry run python src/main.py `
  --file_id meditations `
  --json_path ../pipeline.json

# 6. Check Phase 4 used correct voice
jq ".phase4.files.meditations" pipeline.json | grep selected_voice

# 7. Try different voice quickly
cd ..
poetry run python -m phase3_chunking.main `
  --file_id meditations `
  --voice tom_weiss  # Override with thriller narrator

# 8. Re-run Phase 4 to hear the difference
cd phase4_tts
poetry run python src/main.py --file_id meditations --json_path ../pipeline.json
```

---

## 📊 Summary

**What You Can Do Now:**
- ✅ 14 distinct narrator voices available
- ✅ Auto-select voice based on genre
- ✅ Override per-book permanently
- ✅ Override globally for all books
- ✅ Override temporarily with CLI flag
- ✅ Add custom voices easily
- ✅ Automatic LibriVox audio download & caching
- ✅ Seamless Phase 3 → Phase 4 integration

**Files Modified:**
1. ✨ `phase3-chunking/src/phase3_chunking/voice_selection.py` - Enhanced
2. ✨ `phase3-chunking/src/phase3_chunking/main.py` - Integrated voice selection
3. ✨ `phase4_tts/src/utils.py` - Added multi-voice functions
4. ✨ `phase4_tts/src/main.py` - Integrated voice system

**Files Created:**
1. ✨ `configs/voices.json` - Already existed, validated
2. ✨ `phase4_tts/configs/voice_references.json` - LibriVox sources
3. ✨ `VOICE_OVERRIDE_USAGE_GUIDE.md` - User documentation
4. ✨ `VOICE_OVERRIDE_INTEGRATION.md` - This file

---

## 🎉 You're All Set!

Start processing audiobooks with genre-appropriate, overridable voice selection!

For detailed usage examples, see: **VOICE_OVERRIDE_USAGE_GUIDE.md**
