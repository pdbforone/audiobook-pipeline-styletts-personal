# Voice System Audit

## Executive Summary

The voice system had a critical configuration split between Phase 3 and Phase 4, causing voice mismatches during synthesis. This has been **fixed** by unifying both phases to use the same configuration file.

## Issues Found and Fixed

### Issue 1: Split Configuration (FIXED)
**Problem**: Phase 3 read from `configs/voices.json`, Phase 4 read from `phase4_tts/configs/voice_references.json`

**Impact**:
- Phase 3 could select voices that Phase 4 couldn't use
- Only 2 voices overlapped between configs (neutral_narrator, george_mckayland)
- Silent fallback to random voice during synthesis

**Fix**: Phase 3 now reads from `phase4_tts/configs/voice_references.json` (same as Phase 4)

### Issue 2: No Audio Files for Custom Voices (DOCUMENTED)
**Problem**: Custom voices in `voice_references` have `local_path` but audio files don't exist

**Current State**:
```
voice_references/           # Directory exists but empty
voice_samples/processed/    # Referenced but doesn't exist
```

**Impact**: Any custom voice selection falls back to built-in

**Mitigation**: Added `get_voice_availability()` function that:
- Returns `(True, "built_in", None)` for XTTS/Kokoro voices (always available)
- Checks if audio file exists for custom voices
- Returns clear reason if unavailable

### Issue 3: Silent Fallback (FIXED)
**Problem**: When a voice wasn't available, fallback happened silently

**Fix**: Added explicit "VOICE FALLBACK:" log messages that show:
- What voice was requested
- Why it's not available
- What voice is being used instead

Example log:
```
VOICE FALLBACK: 'george_mckayland' is not available (Audio file not found for 'george_mckayland': voice_references/george_mckayland_trimmed.wav). Using built-in 'am_adam' instead.
```

### Issue 4: Random Fallback Selection (FIXED)
**Problem**: Fallback used `next(iter(voices))` - whatever came first

**Fix**: Prefer high-quality Kokoro voices in order:
1. am_adam (male, authoritative)
2. af_sarah (female, professional)
3. bm_daniel (British male)
4. bf_emma (British female)

## Voice Flow (After Fix)

```
User Request
     │
     ▼
┌─────────────────────────────────────────────────┐
│  Phase 3: voice_selection.py                    │
│  ┌─────────────────────────────────────────┐   │
│  │ 1. CLI override (--voice)               │   │
│  │ 2. File-level override                  │   │
│  │ 3. Global override (tts_voice)          │   │
│  │ 4. Genre profile match (prefer built-in)│   │
│  │ 5. Default voice                        │   │
│  └─────────────────────────────────────────┘   │
│                      │                          │
│                      ▼                          │
│  ┌─────────────────────────────────────────┐   │
│  │ Availability Check                      │   │
│  │ - Built-in? Always available            │   │
│  │ - Custom? Check audio file exists       │   │
│  │ - Fallback if unavailable               │   │
│  └─────────────────────────────────────────┘   │
│                      │                          │
│                      ▼                          │
│         suggested_voice → pipeline.json         │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  Phase 4: main_multi_engine.py                  │
│  ┌─────────────────────────────────────────┐   │
│  │ Read suggested_voice from Phase 3       │   │
│  │ OR use --voice CLI override             │   │
│  └─────────────────────────────────────────┘   │
│                      │                          │
│                      ▼                          │
│  ┌─────────────────────────────────────────┐   │
│  │ Is it a built-in voice?                 │   │
│  │ YES → Use directly (no audio needed)    │   │
│  │ NO  → Check prepared_refs               │   │
│  │       └─ Missing? VOICE FALLBACK        │   │
│  └─────────────────────────────────────────┘   │
│                      │                          │
│                      ▼                          │
│              TTS Synthesis                      │
└─────────────────────────────────────────────────┘
```

## Configuration Reference

### Unified Config Location
```
phase4_tts/configs/voice_references.json
```

### Structure
```json
{
  "voice_references": {
    "custom_voice_id": {
      "local_path": "voice_references/filename.wav",
      "description": "...",
      "narrator_name": "...",
      "preferred_profiles": ["philosophy", "academic"]
    }
  },
  "built_in_voices": {
    "xtts": {
      "Claribel Dervla": { "engine": "xtts", "built_in": true, ... }
    },
    "kokoro": {
      "am_adam": { "engine": "kokoro", "built_in": true, ... }
    }
  }
}
```

### Voice Counts
- **Custom voices**: 14 defined (most missing audio files)
- **XTTS built-in**: 33 voices (always available)
- **Kokoro built-in**: 54 voices (always available)
- **Total**: 101 voices

## Recommendations

### Immediate (Working Now)
1. Use built-in voices for reliable synthesis
2. Prefer Kokoro voices (am_adam, af_sarah) for quality

### To Enable Custom Voices
1. Add audio files to `phase4_tts/voice_references/`
2. Ensure `local_path` in config matches actual filename
3. Audio requirements: 10-30 seconds, clear speech, minimal background noise

### Future Improvements
1. Add voice preparation wizard in UI
2. Validate audio files on upload
3. Preview voice before full synthesis

## Files Changed

| File | Change |
|------|--------|
| `phase3-chunking/src/phase3_chunking/voice_selection.py` | Major rewrite - unified config, availability checking |
| `phase4_tts/src/main_multi_engine.py` | Improved fallback logic and messaging |

## Testing

To verify voice system:
```bash
# List all voices with availability status
python -m phase3_chunking.voice_selection --list

# Check specific voice
python -m phase3_chunking.voice_selection --info am_adam
```

---

*Last Updated: 2024-12-04*
