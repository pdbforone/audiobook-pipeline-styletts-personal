# XTTS Built-in Speaker Diagnosis - Summary

## 🎯 Problem Statement

XTTS built-in speakers (like "Claribel Dervla") fail during synthesis with error:
```
TypeError: Invalid file: None
```

## 🔍 Diagnostic Process

### 1. Model State Inspection ✅

**All systems nominal:**
- `model.is_multi_speaker = True` ✅
- 58 built-in speakers loaded ✅
- `speaker_manager` exists with all mappings ✅
- `speakers_xtts.pth` file present (7.40 MB) ✅
- File contains `gpt_cond_latent` + `speaker_embedding` for each speaker ✅

### 2. Synthesis Tests

| Mode | Configuration | Result |
|------|--------------|--------|
| A | `speaker="Claribel Dervla"` only | ❌ FAILED - "Invalid file: None" |
| B | `speaker_wav="ref.wav"` only | ✅ SUCCESS |
| C | Both parameters | ❌ FAILED - "Invalid file: None" |

### 3. Root Cause Discovery

**The high-level `model.tts()` API has a design limitation:**

```python
# Current code (FAILS)
engine.model.tts(
    text=text,
    speaker="Claribel Dervla",  # ← Ignored!
    language=language
)
# → XTTS still tries to load speaker_wav=None → Crashes
```

**Why it fails:**
1. Code passes `speaker="Claribel Dervla"` to `model.tts()`
2. XTTS API receives the speaker name but **still expects speaker_wav**
3. Internally calls `load_audio(file_path=None)`
4. Crashes with `TypeError: Invalid file: None`

## ✅ SOLUTION VERIFIED

### The Fix: Use Low-Level Inference API

**Discovery:** The `speakers_xtts.pth` file contains pre-computed latents:

```python
{
  'Claribel Dervla': {
    'gpt_cond_latent': torch.Tensor([1, 32, 1024]),
    'speaker_embedding': torch.Tensor([1, 512, 1])
  },
  # ... 57 more speakers
}
```

**Working approach:**

```python
# Load speakers_xtts.pth during initialization
speakers_data = torch.load('speakers_xtts.pth', map_location='cpu')

# Call low-level inference API directly
speaker_dict = speakers_data[speaker_name]
result = tts_model.inference(
    text=text,
    language=language,
    gpt_cond_latent=speaker_dict['gpt_cond_latent'],
    speaker_embedding=speaker_dict['speaker_embedding'],
    temperature=0.75,
    speed=1.0
)
audio = result['wav']  # Returns dict with 'wav' key
```

### Test Results: 100% Success Rate

All tested speakers work perfectly:

| Speaker | Gender | Duration | Status |
|---------|--------|----------|--------|
| Claribel Dervla | Female | 2.31s | ✅ |
| Daisy Studious | Female | 1.66s | ✅ |
| Andrew Chipper | Male | 1.80s | ✅ |
| Dionisio Schuyler | Male | 2.13s | ✅ |

## 📋 Implementation Checklist

To fix `xtts_engine.py`:

- [ ] Load `speakers_xtts.pth` in `load_model()`
- [ ] Store as `self.builtin_speakers_data`
- [ ] Update `_synthesize_single_segment()`:
  - [ ] When `active_speaker` provided → use `tts_model.inference()` with latents
  - [ ] When `ref_to_use` provided → keep existing `model.tts(speaker_wav=...)`
- [ ] Handle text splitting for low-level API
- [ ] Add error handling for missing speaker names
- [ ] Test with all 58 built-in speakers

## 🔧 Code Changes Required

### Location: `phase4_tts/engines/xtts_engine.py`

1. **In `load_model()` method (after line ~295):**
   ```python
   # Load built-in speaker latents
   speakers_pth_path = Path(default_cache) / 'tts_models--multilingual--multi-dataset--xtts_v2' / 'speakers_xtts.pth'
   self.builtin_speakers_data = torch.load(speakers_pth_path, map_location='cpu')
   ```

2. **In `_synthesize_single_segment()` method (replace lines 536-564):**
   ```python
   # Mode 1: Built-in speaker with pre-computed latents
   if active_speaker:
       if active_speaker not in self.builtin_speakers_data:
           raise ValueError(f"Speaker '{active_speaker}' not found")

       speaker_dict = self.builtin_speakers_data[active_speaker]
       result = self.model.synthesizer.tts_model.inference(
           text=text,
           language=language,
           gpt_cond_latent=speaker_dict['gpt_cond_latent'],
           speaker_embedding=speaker_dict['speaker_embedding'],
           temperature=temperature,
           speed=speed,
       )
       return result['wav']

   # Mode 2: Voice cloning (existing code)
   if ref_to_use and ref_to_use.exists():
       return self.model.tts(...)
   ```

## 📊 Diagnostic Artifacts Generated

1. **[diagnose_xtts.py](diagnose_xtts.py)** - Full diagnostic script
2. **[diagnose_output.log](diagnose_output.log)** - Initial diagnostic output
3. **[inspect_speakers_pth.py](inspect_speakers_pth.py)** - Deep dive into speakers_xtts.pth structure
4. **[inspect_speakers_output.log](inspect_speakers_output.log)** - Speaker inspection results
5. **[test_builtin_speaker_fix.py](test_builtin_speaker_fix.py)** - Proof-of-concept solution
6. **[XTTS_DIAGNOSTIC_REPORT.md](XTTS_DIAGNOSTIC_REPORT.md)** - Detailed technical findings
7. **[DIAGNOSIS_SUMMARY.md](DIAGNOSIS_SUMMARY.md)** - This executive summary

## 🎬 Next Steps

1. Review the proposed code changes
2. Implement the fix in `xtts_engine.py`
3. Test with various built-in speakers
4. Verify voice cloning still works
5. Run full pipeline test

## Key Insight

**The XTTS v2 high-level API (`model.tts()`) is broken for built-in speakers.** It requires `speaker_wav` even when `speaker` is provided. The workaround is to bypass it entirely and use the low-level `tts_model.inference()` API with pre-computed latents from `speakers_xtts.pth`.
