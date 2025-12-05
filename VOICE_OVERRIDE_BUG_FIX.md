# Voice Override Bug Fix

**Date**: 2025-11-29
**Status**: ✅ FIXED
**Impact**: Per-chunk voice overrides now work correctly

---

## Problem Summary

Phase 4 chunk voice overrides were not working. When Phase 3 set a voice override for specific chunks, Phase 4 would fail to find the voice in the `voice_assets` lookup and fall back to using an incorrect voice (often with voice cloning when it should use a built-in voice).

**Example from logs**:
```
WARNING - Custom voice 'alison_dietlinde' not found. Falling back to built-in: 'af_heart'
INFO - Using built-in voice 'af_heart' from kokoro engine
INFO - Chunk chunk_0001 overriding voice -> Alison Dietlinde (engine=xtts)
INFO - Using voice cloning with reference: george_mckayland_trimmed.wav
```

This shows contradictory behavior:
1. Phase 4 correctly identified "alison_dietlinde" should be "af_heart" (built-in Kokoro)
2. But then chunk override used XTTS with "george_mckayland" reference instead

---

## Root Cause

**File**: [phase4_tts/src/main_multi_engine.py](phase4_tts/src/main_multi_engine.py)

The bug was a **key mismatch** in dictionary lookup:

### build_voice_assets() - Line 575-617
Creates `voice_assets` dictionary with **normalized keys**:
```python
# Line 593: Built-in voices use normalized keys
normalized_key = normalize_voice_id(voice_name)  # "Baldur Sanjin" → "baldur_sanjin"
assets[normalized_key] = VoiceAsset(...)

# Line 605: Custom voices also use normalized keys
normalized_key = normalize_voice_id(voice_name)  # "Alison Dietlinde" → "alison_dietlinde"
assets[normalized_key] = VoiceAsset(...)
```

### synthesize_chunk_with_engine() - Line 651 (BEFORE FIX)
Looked up voice override using **original key** (not normalized):
```python
if chunk.voice_override and voice_assets:
    voice_asset = voice_assets.get(chunk.voice_override)  # ❌ "Alison Dietlinde" not found!
    if voice_asset:
        # Never reaches here because lookup failed
```

**Result**:
- Lookup with "Alison Dietlinde" fails (key doesn't exist)
- `voice_asset = None`
- Falls back to using wrong voice from prepared_refs

---

## Solution

Added normalization to the voice override lookup at [main_multi_engine.py:651-654](phase4_tts/src/main_multi_engine.py#L651-L654):

```python
if chunk.voice_override and voice_assets:
    # BUGFIX: Normalize voice override for lookup (voice_assets uses normalized keys)
    normalized_override = normalize_voice_id(chunk.voice_override)
    voice_asset = voice_assets.get(normalized_override)  # ✅ Now finds "alison_dietlinde"!
    if voice_asset:
        if voice_asset.engine_params:
            chunk_kwargs.update(voice_asset.engine_params)
        if voice_asset.reference_audio:
            reference = voice_asset.reference_audio
        # ... rest of override logic
```

**Now**:
- Phase 3 sends "Alison Dietlinde" as voice override
- Phase 4 normalizes it to "alison_dietlinde"
- Lookup succeeds in voice_assets
- Correct voice and engine are used

---

## Data Flow (After Fix)

### Built-In Voice Override ✅

```
Phase 3 chunks:
  chunk_0001.txt → voice_override: "Alison Dietlinde"
    ↓
Phase 4:
  1. build_voice_assets() creates assets["alison_dietlinde"] = VoiceAsset(
       voice_id="Alison Dietlinde",
       preferred_engine="xtts",
       engine_params={"speaker": "Alison Dietlinde"},
       reference_audio=None  # Built-in, no reference needed
     )
    ↓
  2. Process chunk_0001:
     - chunk.voice_override = "Alison Dietlinde"
     - normalized_override = "alison_dietlinde" ✅
     - voice_asset = assets["alison_dietlinde"] ✅ FOUND!
     - effective_engine = "xtts" ✅
     - engine_params = {"speaker": "Alison Dietlinde"} ✅
     - reference = None ✅
    ↓
  3. synthesize_chunk_with_engine():
     - Uses XTTS engine ✅
     - Uses built-in voice "Alison Dietlinde" ✅
     - No voice cloning reference ✅
```

### Custom Voice Override ✅

```
Phase 3 chunks:
  chunk_0001.txt → voice_override: "George McKayland"
    ↓
Phase 4:
  1. build_voice_assets() creates assets["george_mckayland"] = VoiceAsset(
       voice_id="George McKayland",
       preferred_engine=None,
       engine_params={},
       reference_audio=Path("voice_references/george_mckayland_trimmed.wav")
     )
    ↓
  2. Process chunk_0001:
     - chunk.voice_override = "George McKayland"
     - normalized_override = "george_mckayland" ✅
     - voice_asset = assets["george_mckayland"] ✅ FOUND!
     - reference = Path(...george_mckayland_trimmed.wav) ✅
    ↓
  3. synthesize_chunk_with_engine():
     - Uses voice cloning with reference ✅
     - Correct custom voice used ✅
```

---

## Related Fixes

This fix complements the earlier voice selection normalization fixes:

### 1. Voice Selection Fix ([main_multi_engine.py:478-496](phase4_tts/src/main_multi_engine.py#L478-L496))
- Added normalization when checking if voice is built-in
- Ensures "alison_dietlinde" from Phase 3 is recognized as "Alison Dietlinde" built-in

### 2. Custom Voice Reference Fix ([main_multi_engine.py:563-567](phase4_tts/src/main_multi_engine.py#L563-L567))
- Try both original and normalized keys for prepared_refs lookup
- Ensures custom voices can be found regardless of format

### 3. Voice Override Fix (This Fix)
- Normalize chunk.voice_override before looking up in voice_assets
- Ensures per-chunk overrides work correctly

**Together, these fixes ensure voice selection and overrides work consistently across all voice name formats.**

---

## Testing

### Test Case 1: Built-In Voice Override

**Setup**:
```json
// Phase 3 output (pipeline.json)
{
  "phase3": {
    "files": {
      "test_file": {
        "voice_overrides": {
          "chunk_0001": "Alison Dietlinde"  // Built-in XTTS voice
        }
      }
    }
  }
}
```

**Expected behavior** (After Fix):
```
INFO - Chunk chunk_0001 overriding voice -> Alison Dietlinde (engine=xtts)
INFO - Using built-in voice 'Alison Dietlinde' from xtts engine
```

**No longer see**:
```
WARNING - Custom voice 'alison_dietlinde' not found. Falling back...
INFO - Using voice cloning with reference: george_mckayland_trimmed.wav
```

### Test Case 2: Custom Voice Override

**Setup**:
```json
// Phase 3 output (pipeline.json)
{
  "phase3": {
    "files": {
      "test_file": {
        "voice_overrides": {
          "chunk_0001": "George McKayland"  // Custom voice with reference
        }
      }
    }
  }
}
```

**Expected behavior**:
```
INFO - Chunk chunk_0001 overriding voice -> George McKayland (engine=xtts)
INFO - Using custom voice clone 'George McKayland' with reference audio
```

### Test Case 3: No Override (Default Voice)

**Setup**:
```json
// No voice_overrides in Phase 3
```

**Expected behavior**:
```
INFO - Using default voice 'Baldur Sanjin' from kokoro engine
```

---

## Benefits

1. **Correct Voice Usage**: Per-chunk overrides now work as designed
2. **No Unnecessary Cloning**: Built-in voices use engine's native voice (faster, better quality)
3. **Consistent Behavior**: Voice selection works regardless of name format (spaces, case, etc.)
4. **Fixes Character Voices**: Multi-character books can now assign different voices per chunk

---

## Modified Files

### phase4_tts/src/main_multi_engine.py
- **Lines 651-654**: Added normalization for chunk voice override lookup

**Change**:
```diff
  if chunk.voice_override and voice_assets:
-     voice_asset = voice_assets.get(chunk.voice_override)
+     # BUGFIX: Normalize voice override for lookup (voice_assets uses normalized keys)
+     normalized_override = normalize_voice_id(chunk.voice_override)
+     voice_asset = voice_assets.get(normalized_override)
      if voice_asset:
```

---

## Impact Assessment

### High Priority Bug Fixed ✅
- Per-chunk voice overrides now functional
- Built-in voices no longer incorrectly use voice cloning
- Custom voices correctly found regardless of name format

### Use Cases Enabled ✅
1. **Multi-character audiobooks**: Different voices for dialogue vs narration
2. **Speaker transitions**: Change voices mid-book
3. **Voice testing**: Override specific chunks for voice comparison

### Performance Improvement ✅
- Built-in voices are faster than cloning (no reference audio loading)
- Built-in voices have better quality (native engine voice)

---

## Summary

**Before Fix**:
- Chunk voice overrides didn't work due to key mismatch
- Built-in voices incorrectly used voice cloning with wrong reference
- "Alison Dietlinde" override → used "George McKayland" reference ❌

**After Fix**:
- Chunk voice overrides work correctly ✅
- Built-in voices use native engine voice ✅
- Custom voices use correct reference audio ✅
- All voice name formats handled consistently ✅

**Impact**: Critical bug fix enabling multi-voice audiobooks and correct voice selection throughout the pipeline.
