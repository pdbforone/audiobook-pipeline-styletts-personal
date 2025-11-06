# Voice Override System - Complete Guide

## Overview

The audiobook pipeline now supports **multi-level voice selection** across Phases 3 and 4, allowing you to override voice choices at different levels of granularity.

## Voice Selection Priority (Highest to Lowest)

1. **CLI Override** (`--voice` flag) - Highest priority
2. **File-level Override** (per-book in pipeline.json)
3. **Global Override** (all files in pipeline.json)
4. **Genre Profile Match** (automatic based on detected genre)
5. **Default Voice** (fallback) - Lowest priority

---

## Available Voices

All voices are defined in `configs/voices.json`. Run this to see the full list:

```bash
# List all available voices
python -m phase3_chunking.voice_selection --list

# Filter by genre profile
python -m phase3_chunking.voice_selection --list --profile philosophy
python -m phase3_chunking.voice_selection --list --profile fiction
```

### Example Output:
```
🎤 landon_elkind
   Measured, scholarly British RP for philosophy/academic works
   Narrator: Landon D. C. Elkind
   Profiles: philosophy, academic

🎤 tom_weiss
   Dynamic thriller narrator with clear pacing
   Narrator: Tom Weiss
   Profiles: fiction, thriller

🎤 neutral_narrator
   Clear, impartial for technical/general content
   Narrator: Current default (Mark Twain sample)
   Profiles: technical, auto
```

---

## Usage Examples

### 1. CLI Override (Quick, One-Time Use)

Override voice for a single Phase 3 run:

```powershell
# Use Landon Elkind for this specific file
poetry run python -m phase3_chunking.main `
  --file_id The_Analects `
  --voice landon_elkind

# Use female narrator for fiction
poetry run python -m phase3_chunking.main `
  --file_id Pride_and_Prejudice `
  --voice female_calm
```

**When to use:** Quick experiments, testing different voices, one-off processing.

---

### 2. File-Level Override (Per-Book Settings)

Set a specific voice for a particular book permanently:

```powershell
# Set Landon Elkind for "Meditations"
python -m phase3_chunking.voice_selection `
  --set-file file_meditations landon_elkind `
  --pipeline pipeline.json

# Set Tom Weiss for "The Girl with the Dragon Tattoo"
python -m phase3_chunking.voice_selection `
  --set-file file_dragon_tattoo tom_weiss `
  --pipeline pipeline.json
```

**Result in pipeline.json:**
```json
{
  "voice_overrides": {
    "file_meditations": "landon_elkind",
    "file_dragon_tattoo": "tom_weiss"
  }
}
```

**When to use:** You have multiple books and want each to use a specific, consistent voice across re-runs.

---

### 3. Global Override (All Files Use Same Voice)

Set one voice for ALL files:

```powershell
# Use British narrator for everything
python -m phase3_chunking.voice_selection `
  --set-global ruth_golding `
  --pipeline pipeline.json
```

**Result in pipeline.json:**
```json
{
  "tts_voice": "ruth_golding"
}
```

**When to use:** You prefer one narrator's style for your entire library, or you want consistency across all audiobooks.

---

### 4. Automatic Genre Matching (Default Behavior)

If no override is set, the system automatically selects a voice based on the detected genre:

```powershell
# No --voice flag = auto-detection
poetry run python -m phase3_chunking.main `
  --file_id The_Analects
```

**How it works:**
1. Phase 3 detects genre (e.g., "philosophy")
2. Looks up voices with `preferred_profiles: ["philosophy"]`
3. Selects first match (e.g., "landon_elkind")

**Genre → Voice Mapping:**
- **Philosophy/Academic** → `landon_elkind`, `pamela_nagami`
- **Fiction/Thriller** → `tom_weiss`, `bella_bolster`
- **Poetry/British** → `gareth_holmes`, `ruth_golding`
- **Technical/Auto** → `neutral_narrator`

---

## Clearing Overrides

### Clear File-Level Override

```powershell
# Remove override for specific file
python -m phase3_chunking.voice_selection `
  --clear-file file_meditations `
  --pipeline pipeline.json
```

### Clear Global Override

```powershell
# Remove global voice setting
python -m phase3_chunking.voice_selection `
  --clear-global `
  --pipeline pipeline.json
```

After clearing, the system falls back to **automatic genre matching**.

---

## Complete Workflow Examples

### Example 1: Philosophy Book with Custom Voice

```powershell
# Step 1: Set file-level override
python -m phase3_chunking.voice_selection `
  --set-file analects landon_elkind `
  --pipeline pipeline.json

# Step 2: Run Phase 3 (uses landon_elkind automatically)
poetry run python -m phase3_chunking.main `
  --file_id analects

# Step 3: Run Phase 4 (uses voice from Phase 3 output)
poetry run python src/main.py `
  --file_id analects `
  --json_path ../pipeline.json
```

### Example 2: Quick Test with CLI Override

```powershell
# Test different voices quickly without modifying pipeline.json
poetry run python -m phase3_chunking.main `
  --file_id test_book `
  --voice tom_weiss

# Try another voice
poetry run python -m phase3_chunking.main `
  --file_id test_book `
  --voice landon_elkind
```

### Example 3: Batch Processing with Global Voice

```powershell
# Set global voice for entire batch
python -m phase3_chunking.voice_selection `
  --set-global ruth_golding `
  --pipeline pipeline.json

# Process multiple books - all use ruth_golding
poetry run python -m phase3_chunking.main --file_id book1
poetry run python -m phase3_chunking.main --file_id book2
poetry run python -m phase3_chunking.main --file_id book3
```

---

## Voice Information

### Get Details for Specific Voice

```powershell
python -m phase3_chunking.voice_selection --info landon_elkind
```

**Output:**
```
🎤 landon_elkind
============================================================
Description: Measured, scholarly British RP for philosophy/academic works
Narrator: Landon D. C. Elkind
Source: Mysticism and Logic by Bertrand Russell
Profiles: philosophy, academic
TTS Params: {'pitch': -1, 'rate': 0.95}
```

---

## Integration with Phase 4

Phase 4 automatically reads the voice selection from Phase 3's output:

```python
# Phase 3 saves selected voice in chunk_metrics
{
  "phase3": {
    "files": {
      "analects": {
        "chunk_metrics": {
          "selected_voice": "landon_elkind"
        }
      }
    }
  }
}
```

Phase 4 then:
1. Reads `selected_voice` from pipeline.json
2. Maps it to the appropriate voice reference file (e.g., `voice_references/landon_elkind.wav`)
3. Uses that reference for voice cloning

---

## Troubleshooting

### Invalid Voice ID Error

```
ERROR: Invalid voice ID: unknown_voice
Run 'python -m phase3_chunking.voice_selection --list' to see available voices
```

**Solution:** Run `--list` to see valid voice IDs, then use one of those.

### Voice Not Found in Registry

```
WARNING: Voice 'old_voice' not found in registry, ignoring
```

**Solution:** Update `configs/voices.json` or use a different voice.

### Override Not Taking Effect

Check override priority:
1. Is there a CLI `--voice` flag overriding your setting?
2. Is there a file-level override taking precedence over global?
3. Verify `pipeline.json` contains your override setting

---

## Advanced: Creating Custom Voices

To add a new voice to the registry:

1. **Edit `configs/voices.json`:**

```json
{
  "voices": {
    "my_custom_voice": {
      "description": "Custom narrator description",
      "narrator_name": "Narrator Name",
      "source": "Source audiobook",
      "preferred_profiles": ["genre1", "genre2"],
      "tts_engine_params": {
        "pitch": 0,
        "rate": 1.0
      }
    }
  }
}
```

2. **Create voice reference in Phase 4:**

Add entry to `phase4_tts/configs/voice_references.json`:

```json
{
  "my_custom_voice": {
    "source_url": "https://archive.org/download/your_audio.mp3",
    "description": "Description",
    "trim_start": 10,
    "trim_end": 30,
    "preferred_profiles": ["genre1"]
  }
}
```

3. **Test the new voice:**

```powershell
python -m phase3_chunking.voice_selection --list
python -m phase3_chunking.main --file_id test --voice my_custom_voice
```

---

## Quick Reference Commands

```powershell
# List voices
python -m phase3_chunking.voice_selection --list
python -m phase3_chunking.voice_selection --list --profile philosophy

# Voice details
python -m phase3_chunking.voice_selection --info landon_elkind

# Set overrides
python -m phase3_chunking.voice_selection --set-global VOICE_ID
python -m phase3_chunking.voice_selection --set-file FILE_ID VOICE_ID

# Clear overrides
python -m phase3_chunking.voice_selection --clear-global
python -m phase3_chunking.voice_selection --clear-file FILE_ID

# Use in Phase 3
poetry run python -m phase3_chunking.main --file_id FILE_ID --voice VOICE_ID
```

---

## Summary

The voice override system gives you complete control:
- **Quick experiments** → Use CLI `--voice`
- **Permanent per-book settings** → Use `--set-file`
- **Consistent across all books** → Use `--set-global`
- **Automatic intelligent selection** → Use no override (default)

Start with automatic detection, then override when needed!
