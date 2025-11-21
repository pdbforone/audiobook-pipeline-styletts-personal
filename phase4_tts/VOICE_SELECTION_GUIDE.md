# Voice Selection Guide - XTTS & Kokoro

## Overview

Phase 4 now supports **three types of voices**:
1. **XTTS Built-in Voices** (33 voices) - No reference audio needed
2. **Kokoro Built-in Voices** (4 voices) - No reference audio needed
3. **Custom Voice Clones** (30+ voices) - Uses your reference audio files

---

## Quick Start

### List All Available Voices

```bash
# List all voices (built-in + custom)
python phase4_tts/list_voices.py

# List only XTTS voices
python phase4_tts/list_voices.py --engine xtts --built-in-only

# List only Kokoro voices
python phase4_tts/list_voices.py --engine kokoro --built-in-only

# Filter by profile
python phase4_tts/list_voices.py --profile philosophy
```

### Use a Built-in Voice

```bash
# XTTS with built-in voice
python phase4_tts/engine_runner.py \
  --engine xtts \
  --voice "Claribel Dervla" \
  --file_id MyBook \
  --json_path pipeline.json

# Kokoro with built-in voice
python phase4_tts/engine_runner.py \
  --engine kokoro \
  --voice af_sarah \
  --file_id MyBook \
  --json_path pipeline.json
```

### Use a Custom Voice Clone (XTTS only)

```bash
# XTTS with custom voice cloning
python phase4_tts/engine_runner.py \
  --engine xtts \
  --voice bob_neufeld \
  --file_id MyBook \
  --json_path pipeline.json
```

---

## Built-in Voices

### XTTS Voices (33 Total)

**Female Voices:**
- **Claribel Dervla** - British, clear and warm (default)
- **Gracie Wise** - American, mature and authoritative (academic/philosophy)
- **Alison Dietlinde** - British, refined and elegant (classic literature)
- **Daisy Studious** - American, youthful (young adult)
- And 11 more female voices...

**Male Voices:**
- **Royston Min** - British, refined and authoritative (academic/philosophy)
- **Badr Odhiambo** - Deep and resonant (philosophy/theology)
- **Andrew Chipper** - British, cheerful (fiction/humor)
- **Damien Black** - Deep and mysterious (gothic/horror)
- And 17 more male voices...

### Kokoro Voices (4 Total)

- **af_bella** - Female, warm and expressive (fiction/memoir) - Quality: 4.5
- **af_sarah** - Female, clear and professional (academic/technical) - Quality: 4.6
- **am_adam** - Male, deep and authoritative (philosophy/theology) - Quality: 4.5
- **am_michael** - Male, neutral and measured (academic/general) - Quality: 4.4

---

## Voice Selection Logic

### How Voice Selection Works

1. **Explicit voice parameter** (`--voice`) takes highest priority
2. **Phase 3 voice selection** is used if no explicit voice given
3. **Default fallback**: First Kokoro built-in voice (`af_bella`)

### Built-in vs Custom Voices

**Built-in Voice** (XTTS/Kokoro):
- ✓ No reference audio file needed
- ✓ Instant synthesis (no prep time)
- ✓ Consistent quality
- ✓ Passed as `speaker` (XTTS) or `voice` (Kokoro) parameter
- ✗ Cannot customize the voice itself

**Custom Voice Clone** (XTTS only):
- ✓ Your own voice from reference audio
- ✓ Unique character for your audiobooks
- ✓ Can clone any voice with 10-30s of audio
- ✗ Requires reference audio preparation
- ✗ XTTS only (Kokoro doesn't support cloning)

---

## Adding Custom Voice Clones

### 1. Add to `voice_references.json`

```json
{
  "voice_references": {
    "my_custom_voice": {
      "local_path": "C:/path/to/your/voice_sample.wav",
      "description": "My Custom Voice - Description",
      "narrator_name": "Narrator Name",
      "preferred_profiles": ["philosophy", "fiction"],
      "quality_score": 4.5,
      "notes": "10-30s clean audio sample"
    }
  }
}
```

### 2. Audio Requirements

- **Duration**: 10-30 seconds
- **Quality**: Clean, no background noise
- **Format**: WAV, MP3, or FLAC
- **Sample Rate**: Will be auto-resampled to 24kHz
- **Content**: Natural speech (not singing, shouting, or whisper)

### 3. Use Your Custom Voice

```bash
python phase4_tts/engine_runner.py \
  --engine xtts \
  --voice my_custom_voice \
  --file_id MyBook \
  --json_path pipeline.json
```

---

## Voice Selection by Genre

### Philosophy & Academic
- **XTTS**: Gracie Wise, Royston Min, Badr Odhiambo
- **Kokoro**: af_sarah, am_adam
- **Custom**: bob_neufeld, geoffrey_edwards

### Fiction & Literature
- **XTTS**: Claribel Dervla, Alison Dietlinde, Andrew Chipper
- **Kokoro**: af_bella
- **Custom**: ruth_golding, kara_shallenberg

### Theology & Religious
- **XTTS**: Badr Odhiambo, Royston Min
- **Kokoro**: am_adam
- **Custom**: david_leeson, maryann_spiegel

### Gothic & Horror
- **XTTS**: Damien Black
- **Custom**: vincent_price_01, agnes_moorehead

---

## Technical Details

### Engine Parameters

**XTTS Built-in**:
```python
{
  "speaker": "Claribel Dervla",  # Voice name
  "temperature": 0.7,             # Creativity (0.1-1.0)
  "speed": 1.0                    # Speech rate (0.5-2.0)
}
```

**XTTS Custom Clone**:
```python
{
  "reference_audio": "/path/to/voice.wav",
  "temperature": 0.7,
  "speed": 1.0
}
```

**Kokoro Built-in**:
```python
{
  "voice": "af_sarah",   # Voice ID
  "speed": 1.0,          # Speech rate (0.5-2.0)
  "lang": "en-us"        # Language code
}
```

### Character Limits

- **XTTS**: 10,000 characters (conservative limit; optimal quality ~1000-1500 chars)
- **Kokoro**: 5000 characters (soft limit)

**Note**: XTTS v2 uses a GPT-based architecture with ~400 token context window (~2000-2500 chars).
Phase 3 should target 1000-1500 character chunks for best quality, but longer text will work if needed.

---

## Examples

### Example 1: Philosophy Book with XTTS Built-in

```bash
python phase4_tts/engine_runner.py \
  --engine xtts \
  --voice "Royston Min" \
  --file_id "Marcus_Aurelius_Meditations" \
  --json_path pipeline.json \
  --device cpu
```

### Example 2: Fiction with Kokoro

```bash
python phase4_tts/engine_runner.py \
  --engine kokoro \
  --voice af_bella \
  --file_id "Pride_and_Prejudice" \
  --json_path pipeline.json \
  --device cpu
```

### Example 3: Custom Voice Clone for Theology

```bash
python phase4_tts/engine_runner.py \
  --engine xtts \
  --voice david_leeson \
  --file_id "The_Pursuit_of_God" \
  --json_path pipeline.json \
  --device cpu
```

### Example 4: Full Pipeline with Orchestrator

```bash
# Set engine in config.yaml: tts_engine: "xtts"
cd phase6_orchestrator

python orchestrator.py input/my_book.pdf \
  --voice "Gracie Wise" \
  --phases 1 2 3 4 5
```

---

## Troubleshooting

### "Voice not found" error

**Problem**: Voice name doesn't match exactly

**Solution**:
```bash
# List all voices to see exact names
python phase4_tts/list_voices.py
```

### "No reference audio" error

**Problem**: Trying to use a custom voice but reference file is missing

**Solution**:
1. Check `voice_references.json` for correct `local_path`
2. Verify the audio file exists at that path
3. Or use a built-in voice instead

### Built-in voice sounds wrong

**Problem**: Voice doesn't match expected character

**Solution**:
1. List voices filtered by profile: `python list_voices.py --profile philosophy`
2. Try different built-in voices from the same profile
3. Use custom voice clone for exact match

---

## Best Practices

1. **Preview voices**: Test multiple voices on a short sample before full book
2. **Match voice to content**: Use the profile tags to find appropriate voices
3. **Quality over speed**: Kokoro is faster but XTTS often has better quality
4. **Custom clones for series**: Create custom voice for multi-book series
5. **Built-in for quick tests**: Use built-in voices during development/testing

---

## Configuration Files

- **Voice List**: `phase4_tts/configs/voice_references.json`
- **Engine Config**: `phase4_tts/config.yaml`
- **List Utility**: `phase4_tts/list_voices.py`
- **Orchestrator**: `phase6_orchestrator/config.yaml`

---

**For more information, run:**
```bash
python phase4_tts/list_voices.py --help
```
