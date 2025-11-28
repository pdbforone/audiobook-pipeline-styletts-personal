# Voice Configuration Complete

## Summary

All available built-in voices for XTTS and Kokoro engines have been discovered and configured in the UI.

**Date:** 2025-11-27

---

## Voice Inventory

### XTTS v2 (33 voices)
All 33 built-in XTTS voices are configured and available in the UI dropdown.

**Female voices (15):**
- Claribel Dervla (British)
- Daisy Studious (American)
- Gracie Wise (American)
- Tammie Ema (American)
- Alison Dietlinde (British)
- Ana Florence (American)
- Annmarie Nele (American)
- Asya Anara (European)
- Brenda Stern (American)
- Gitta Nikolina (European)
- Henriette (French)
- Sofia Hellen (neutral)
- Tammy Grit (American)
- Tanja Adelina (European)
- Vjollca Johnnie (Eastern European)

**Male voices (18):**
- Andrew Chipper (British)
- Badr Odhiambo (deep, neutral)
- Dionisio Schuyler (Spanish)
- Royston Min (British)
- Viktor Eka (European)
- Abrahan Mack (American)
- Adde Michal (Scandinavian)
- Baldur Sanjin (strong, commanding)
- Craig Gutsy (American)
- Damien Black (mysterious)
- Gilberto Mathias (Portuguese)
- Ilkin Urbano (Turkish)
- Kazuhiko Atallah (Japanese)
- Ludvig Milivoj (Slavic)
- Suad Qasim (Arabic)
- Torcull Diarmuid (Scottish)
- Wulf Carlevaro (Italian)
- Ervin Hank (American)

### Kokoro 82M v1.0 (54 voices across 9 languages)

**American English (20 voices):**
- Female (11): af_heart, af_alloy, af_aoede, af_bella, af_jessica, af_kore, af_nicole, af_nova, af_river, af_sarah, af_sky
- Male (9): am_adam, am_echo, am_eric, am_fenrir, am_liam, am_michael, am_onyx, am_puck, am_santa

**British English (8 voices):**
- Female (4): bf_alice, bf_emma, bf_isabella, bf_lily
- Male (4): bm_daniel, bm_fable, bm_george, bm_lewis

**Japanese (5 voices):**
- Female (4): jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro
- Male (1): jm_kumo

**Mandarin Chinese (8 voices):**
- Female (4): zf_xiaobei, zf_xiaoni, zf_xiaoxiao, zf_xiaoyi
- Male (4): zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang

**Spanish (3 voices):**
- Female (1): ef_dora
- Male (2): em_alex, em_santa

**French (1 voice):**
- Female (1): ff_siwis

**Hindi (4 voices):**
- Female (2): hf_alpha, hf_beta
- Male (2): hm_omega, hm_psi

**Italian (2 voices):**
- Female (1): if_sara
- Male (1): im_nicola

**Brazilian Portuguese (3 voices):**
- Female (1): pf_dora
- Male (2): pm_alex, pm_santa

### Custom Voice Clones (14 voices)

Custom voice clones created from LibriVox and other sources for specific genres.

---

## Total Configuration

- **XTTS voices:** 33
- **Kokoro voices:** 54
- **Custom voices:** 14
- **Total voices:** 101

All voices are now selectable via the UI dropdown in [ui/app.py](ui/app.py).

---

## Files Modified

### 1. [phase4_tts/configs/voice_references.json](phase4_tts/configs/voice_references.json)

**Changes:**
- Added all 33 XTTS built-in voices (lines 169-534)
- Expanded Kokoro from 4 to 54 voices (lines 536-1048)
- Each voice includes:
  - `engine`: "xtts" or "kokoro"
  - `built_in`: true
  - `description`: Voice characteristics
  - `preferred_profiles`: Recommended genres
  - `gender`: "male" or "female"
  - `accent`: Regional accent
  - `language`: ISO language code (for non-English voices)
  - `quality_score`: Subjective quality rating

### 2. [phase4_tts/engines/kokoro_engine.py](phase4_tts/engines/kokoro_engine.py)

**Changes:**
- Updated `get_available_voices()` method (lines 167-207)
- Expanded from 4 voices to all 54 voices
- Added comments indicating voice counts by language/region

---

## UI Integration

The [ui/services/voice_manager.py](ui/services/voice_manager.py) automatically loads all built-in voices from the configuration file:

1. Reads `voice_references.json`
2. Loads custom voices from `voice_references` section
3. Loads built-in voices from `built_in_voices.xtts` section
4. Loads built-in voices from `built_in_voices.kokoro` section
5. Generates dropdown labels with format: `voice_id: [ENGINE] Narrator Name (profile1, profile2)`

**Example dropdown items:**
- Custom: `george_mckayland: George Mckayland (philosophy, memoir, academic)`
- XTTS: `Claribel Dervla: [XTTS] Claribel Dervla (fiction, memoir, general)`
- Kokoro: `af_sarah: [KOKORO] af_sarah (academic, philosophy, technical)`

---

## Testing Results

### Voice Manager Test
```
Total voices in dropdown: 101
XTTS voices in dropdown: 33
Kokoro voices in dropdown: 54
Custom voices: 14
```

### Kokoro Synthesis Test
Tested voices: `af_sarah`, `am_adam`, `bm_george`
- ✅ All successfully synthesized audio
- Voice length: ~2-3 seconds per test phrase
- Sample rate: 24kHz

---

## Voice Selection in Phase 4

When running Phase 4 TTS:

### For XTTS Engine:
- Built-in voices use the `speaker` parameter
- Custom voices use the `speaker_wav` parameter (voice cloning)

### For Kokoro Engine:
- All voices use the `voice` parameter (no cloning needed)
- Voices work across supported languages

---

## References

### XTTS Documentation:
- Coqui TTS: https://github.com/coqui-ai/TTS
- XTTS v2 model: `tts_models/multilingual/multi-dataset/xtts_v2`

### Kokoro Documentation:
- Kokoro ONNX: https://github.com/thewh1teagle/kokoro-onnx
- Hugging Face model: https://huggingface.co/hexgrad/Kokoro-82M
- Voice list: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md

---

## Next Steps

1. ✅ All voices configured and available in UI
2. ✅ VoiceManager correctly loads all 101 voices
3. ✅ UI dropdown displays all voices sorted by type (custom first, then XTTS, then Kokoro)
4. ⏭️ User can now select any voice from the dropdown for audiobook generation

**Configuration is complete and ready for use!**
