# XTTS Engine Diagnostic Report

## Executive Summary

**Root Cause Found:** The XTTS engine fails when using built-in speakers (`active_speaker="Claribel Dervla"`) because the underlying XTTS model **requires** a reference audio file (`speaker_wav`) parameter even when using built-in multi-speaker voices.

## Diagnostic Findings

### 1. Model State (CONFIRMED WORKING)

✅ **Model is properly configured as multi-speaker:**
- `model.is_multi_speaker = True`
- `model.speakers` contains 58 built-in voices
- `model.synthesizer.tts_model.speaker_manager` EXISTS
- `speaker_manager.name_to_id` contains all 58 speaker mappings
- `speakers_xtts.pth` file EXISTS (7.40 MB)

### 2. API Signature (CONFIRMED)

The `TTS.tts()` method signature:
```python
def tts(
    text: str,
    speaker: str = None,          # ← Built-in speaker name
    language: str = None,
    speaker_wav: str = None,      # ← Reference audio path
    emotion: str = None,
    speed: float = None,
    split_sentences: bool = True,
    **kwargs
)
```

### 3. Synthesis Test Results

| Mode | Parameters | Result | Error |
|------|------------|--------|-------|
| **Mode A** | `speaker="Claribel Dervla"`, `speaker_wav=None` | ❌ FAILED | `TypeError: Invalid file: None` |
| **Mode B** | `speaker=None`, `speaker_wav="audio.wav"` | ✅ SUCCESS | (synthesized successfully) |
| **Mode C** | `speaker="Claribel Dervla"`, `speaker_wav="audio.wav"` | ❌ FAILED | `TypeError: Invalid file: None` |

### 4. Code Path Analysis

**Current implementation ([xtts_engine.py:539-546](xtts_engine.py#L539-L546)):**

```python
# Mode 1: Built-in voice using speaker parameter (PRIORITY)
if active_speaker:
    return self.model.tts(
        text=text,
        speaker=active_speaker,  # Passes "Claribel Dervla"
        language=language,
        speed=speed,
        temperature=temperature,
        # ❌ NO speaker_wav parameter!
    )
```

**What happens at runtime:**
1. Code calls `model.tts(speaker="Claribel Dervla", speaker_wav=None)`
2. XTTS receives the `speaker` parameter
3. XTTS **STILL tries to load a reference audio file** (`ref_audio_path=None`)
4. Traceback shows: `xtts.py:356: audio = load_audio(file_path, load_sr)`
5. This calls `torchaudio.load(None)` which fails with `TypeError: Invalid file: None`

### 5. Critical Discovery

**The XTTS v2 model appears to REQUIRE a reference audio file even when using built-in speakers!**

This is contrary to the documentation which suggests built-in speakers should work standalone.

Possible explanations:
1. **XTTS v2 architecture changed**: Built-in speakers might now be reference-based internally
2. **API behavior**: The `speaker` parameter alone is insufficient; `speaker_wav` is always required
3. **Built-in voices ARE reference files**: The speakers_xtts.pth file contains reference embeddings that need to be loaded as if they were audio files

### 6. Comparison with Pipeline Behavior

**Why voice cloning works but built-in speakers don't:**

- **Voice cloning (Mode B)**: Passes `speaker_wav="reference.wav"` → XTTS loads the file → SUCCESS
- **Built-in speaker (Mode A)**: Passes `speaker="Claribel Dervla"` → XTTS still tries to load a file → Gets `None` → FAILURE
- **Both (Mode C)**: Passes both parameters → XTTS prioritizes speaker_wav → But code logic conflicts → FAILURE

## Hypotheses for Why Built-in Speakers Fail

### Hypothesis 1: Built-in Speakers Need Reference Embedding Extraction
XTTS v2 might require converting the speaker name to a speaker embedding, then loading that embedding as if it were derived from an audio file. The current code doesn't perform this conversion.

### Hypothesis 2: Missing Speaker Manager Integration
The code doesn't use `model.synthesizer.tts_model.speaker_manager` to retrieve speaker embeddings. It relies on the high-level API which may not properly handle speaker names.

### Hypothesis 3: API Design Issue
The TTS API might have a bug or design flaw where it always expects `speaker_wav` regardless of whether `speaker` is provided.

## Recommended Next Steps

1. **Inspect TTS source code** to understand how `speaker` parameter is processed
2. **Check if speaker_manager has a method** to get audio/embedding path for built-in speakers
3. **Test lower-level API**: Try calling `model.synthesizer.tts()` directly with speaker manager embeddings
4. **Consult XTTS documentation**: Verify if built-in speakers are actually supposed to work without speaker_wav
5. **Examine speakers_xtts.pth structure**: Understand how built-in speaker data is stored

## Files Generated

- `diagnose_xtts.py` - Full diagnostic script
- `diagnose_output.log` - Complete diagnostic run output
- `check_xtts_api.py` - API signature inspection
- `XTTS_DIAGNOSTIC_REPORT.md` - This report

## Conclusion

The XTTS engine is properly loaded with all multi-speaker capabilities intact, but the current implementation cannot use built-in speakers because:

1. ✅ Built-in speaker names are passed correctly to the API
2. ❌ XTTS still requires a reference audio file path even for built-in speakers
3. ❌ The code doesn't provide this reference path
4. ❌ No fallback or conversion from speaker name → embedding/audio path

## ✅ SOLUTION FOUND AND VERIFIED

### Root Cause
The **high-level `model.tts()` API cannot use built-in speakers** without a reference audio file. It always tries to load `speaker_wav` even when `speaker` is provided.

### The Fix
Use the **low-level `tts_model.inference()` API** with pre-computed latents from `speakers_xtts.pth`:

```python
# Load speakers_xtts.pth once during initialization
speakers_data = torch.load('speakers_xtts.pth', map_location='cpu')

# When synthesizing with a built-in speaker:
speaker_dict = speakers_data[speaker_name]
result = tts_model.inference(
    text=text,
    language=language,
    gpt_cond_latent=speaker_dict['gpt_cond_latent'],    # From .pth
    speaker_embedding=speaker_dict['speaker_embedding'], # From .pth
    temperature=0.75,
    speed=1.0
)
audio = result['wav']  # Returns dict with 'wav' key
```

### Verified Results
✅ **All 4 tested speakers work perfectly:**
- Claribel Dervla (female) - 2.31s
- Daisy Studious (female) - 1.66s
- Andrew Chipper (male) - 1.80s
- Dionisio Schuyler (male) - 2.13s

### Implementation Plan
Update `xtts_engine.py` to:
1. Load `speakers_xtts.pth` during `load_model()`
2. Store it as `self.builtin_speakers_data`
3. Modify `_synthesize_single_segment()` to:
   - When `active_speaker` is provided:
     - Look up speaker in `self.builtin_speakers_data`
     - Call `self.model.synthesizer.tts_model.inference()` directly
     - Extract audio from result dict
   - When `ref_to_use` is provided:
     - Keep existing `model.tts(speaker_wav=...)` logic
4. Handle text splitting properly for the low-level API
