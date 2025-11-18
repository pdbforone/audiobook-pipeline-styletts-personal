# Voice Selection & Override Guide

**Version**: 2.0 | **Last Updated**: October 2025  
**For**: Audiobook Pipeline Phases 3 & 4

---

## Table of Contents

1. [Overview](#overview)
2. [Available Voices](#available-voices)
3. [Override Priority System](#override-priority-system)
4. [Usage Examples](#usage-examples)
5. [Chunk-Level Overrides](#chunk-level-overrides)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The audiobook pipeline now supports **15+ narrator voices** across multiple genres. You can override voice selection at multiple levels:

> **Private-use reminder:** These LibriVox-sourced references and synthetic voices are curated for the Personal Audiobook Studio you run locally. Keep the resulting audiobooks for personal study/listening unless you independently confirm each narrator's license for distribution.

- **Level 1**: CLI argument (highest priority)
- **Level 2**: pipeline.json `tts_voice` field
- **Level 3**: Phase 3 genre-based suggestion
- **Level 4**: Default voice (fallback)

---

## Available Voices

### Philosophy & Academic Voices

| Voice ID | Narrator | Description | Best For |
|----------|----------|-------------|----------|
| `jim_locke` | Landon D. C. Elkind | Deep, measured, scholarly | Philosophy, ethics, logic |
| `pamela_nagami` | Pamela Nagami | Warm yet authoritative | Classical philosophy |
| `hugh_mcguire` | Hugh McGuire | British, intellectual | Academic texts |

### Fiction Voices

| Voice ID | Narrator | Description | Best For |
|----------|----------|-------------|----------|
| `tom_weiss` | Tom Weiss | Suspenseful, thriller-style | Mystery, thriller, noir |
| `bella_bolster` | Bella Bolster | Warm, engaging | Contemporary fiction |
| `kara_shallenberg` | Kara Shallenberg | Classic fiction style | Literary classics |

### Poetry Voices

| Voice ID | Narrator | Description | Best For |
|----------|----------|-------------|----------|
| `gareth_holmes` | Gareth Holmes | British, expressive | Poetry, verse |

### Theology & Spiritual

| Voice ID | Narrator | Description | Best For |
|----------|----------|-------------|----------|
| `wayne_cooke` | Wayne Cooke | Reverent, contemplative | Religious texts |
| `eric_metzler` | Eric Metzler | Scholarly theological | Academic theology |

### British Accent Options

| Voice ID | Narrator | Description | Best For |
|----------|----------|-------------|----------|
| `ruth_golding` | Ruth Golding (RP) | Received Pronunciation | Formal British texts |
| `david_barnes` | David Barnes | BBC English | Documentary-style |
| `cori_samuel` | Cori Samuel | Modern British | Contemporary British lit |
| `peter_yearsley` | Peter Yearsley | Classic British | Period literature |

### Default/Neutral

| Voice ID | Narrator | Description | Best For |
|----------|----------|-------------|----------|
| `neutral_narrator` | Mark Twain | Clear, engaging | General use, auto-detect |
| `female_calm` | Generic female | Warm, conversational | Memoir, self-help |

### Experimental / FX (Optional)

| Voice ID | Engine | Description | Notes |
|----------|--------|-------------|-------|
| `droid_fx` | PyAudio / `ttastromech` | R2-D2 style beeps/boops | See `phase4_tts/DROID_VOICE_GUIDE.md` for setup + mapping.

> ⚠️ `droid_fx` is meant for UI flourishes, promos, or creative easter eggs. It bypasses XTTS/Kokoro and generates tones locally, so keep it out of production narration runs unless you truly want robotic output.

---

## Override Priority System

The voice selection follows this priority order (highest to lowest):

### Priority 1: CLI Override (Highest)

```bash
# Force specific voice for entire book
poetry run python -m phase4_tts.main \
  --pipeline pipeline.json \
  --file-id my_book \
  --voice jim_locke
```

**When to use**: You know exactly which voice you want for the whole audiobook.

---

### Priority 2: pipeline.json `tts_voice` Field

Edit `pipeline.json` manually:

```json
{
  "tts_voice": "tom_weiss",
  "tts_profile": "auto",
  "phase2": { ... }
}
```

**When to use**: You want a specific voice for this file, but don't want to type `--voice` every time.

---

### Priority 3: Phase 3 Suggestion (Genre-Based)

Phase 3 automatically suggests voices based on genre:

```json
{
  "phase3": {
    "files": {
      "my_book_c0001": {
        "suggested_voice": "jim_locke",
        ...
      }
    }
  }
}
```

**When to use**: Let the pipeline auto-select based on detected genre (philosophy → jim_locke, fiction → bella_bolster, etc.)

---

### Priority 4: Default Voice

Falls back to `neutral_narrator` from `configs/voice_references.json`:

```json
{
  "default_voice": "neutral_narrator"
}
```

**When to use**: No specific preference, just use something reasonable.

---

## Usage Examples

### Example 1: Let Pipeline Auto-Select (Recommended)

Just run normally - Phase 3 will detect genre and suggest appropriate voice:

```bash
# Phase 3 detects "philosophy" → suggests jim_locke
poetry run python -m phase3_chunking.chunker \
  --input /artifacts/text/meditations.cleaned.txt \
  --file-id meditations \
  --profile auto

# Phase 4 uses Phase 3 suggestion (jim_locke)
poetry run python -m phase4_tts.main \
  --pipeline pipeline.json \
  --file-id meditations
```

**Result**: Automatic genre-matched voice (no manual intervention needed).

---

### Example 2: Force Specific Voice via CLI

Override for one audiobook:

```bash
# Use British narrator for Pride & Prejudice
poetry run python -m phase4_tts.main \
  --pipeline pipeline.json \
  --file-id pride_prejudice \
  --voice ruth_golding
```

**Result**: Uses Ruth Golding regardless of Phase 3 suggestion.

---

### Example 3: Set Voice in pipeline.json

For repeated use without typing `--voice` every time:

1. Edit `pipeline.json`:
   ```json
   {
     "tts_voice": "gareth_holmes",
     "phase2": { ... }
   }
   ```

2. Run Phase 4 normally:
   ```bash
   poetry run python -m phase4_tts.main \
     --pipeline pipeline.json \
     --file-id my_poetry
   ```

**Result**: Always uses Gareth Holmes for poetry in this pipeline.

---

### Example 4: Override Per-Chunk (Advanced)

For mixed-narrator audiobooks (e.g., dialogue with multiple characters):

1. Edit `pipeline.json` after Phase 3:
   ```json
   {
     "phase3": {
       "files": {
         "book_c0001": {"suggested_voice": "tom_weiss"},
         "book_c0002": {"suggested_voice": "bella_bolster"},
         "book_c0003": {"suggested_voice": "tom_weiss"}
       }
     }
   }
   ```

2. Run Phase 4:
   ```bash
   poetry run python -m phase4_tts.main \
     --pipeline pipeline.json \
     --file-id book
   ```

**Result**: Each chunk uses different voice (useful for dialogue-heavy fiction).

---

## Chunk-Level Overrides

### Use Case: Multi-Narrator Audiobooks

For books with distinct narrators per chapter or character:

#### Step 1: Run Phase 3 Normally

```bash
poetry run python -m phase3_chunking.chunker \
  --input /artifacts/text/my_novel.cleaned.txt \
  --file-id my_novel \
  --profile fiction
```

#### Step 2: Edit pipeline.json to Assign Voices

Open `pipeline.json` and modify Phase 3 chunk entries:

```json
{
  "phase3": {
    "files": {
      "my_novel_c0001": {
        "path": "/artifacts/chunks/my_novel_c0001.txt",
        "suggested_voice": "tom_weiss"  // ← Narrator for Chapter 1
      },
      "my_novel_c0002": {
        "path": "/artifacts/chunks/my_novel_c0002.txt",
        "suggested_voice": "bella_bolster"  // ← Narrator for Chapter 2
      },
      "my_novel_c0003": {
        "path": "/artifacts/chunks/my_novel_c0003.txt",
        "suggested_voice": "tom_weiss"  // ← Back to first narrator
      }
    }
  }
}
```

#### Step 3: Run Phase 4

```bash
poetry run python -m phase4_tts.main \
  --pipeline pipeline.json \
  --file-id my_novel
```

**Result**: Chunks synthesized with different voices automatically.

---

### Bulk Chunk Override Script

For large books, manually editing JSON is tedious. Use this helper script:

```python
# tools/set_chunk_voices.py

import json
import sys

def set_voices_by_pattern(pipeline_path, file_id, pattern_map):
    """
    Set voices for chunks matching patterns.
    
    Example:
        pattern_map = {
            "c0001:c0005": "tom_weiss",      # Chunks 1-5
            "c0006:c0010": "bella_bolster",  # Chunks 6-10
            "c0011:*": "tom_weiss"           # Rest use tom_weiss
        }
    """
    with open(pipeline_path, 'r') as f:
        data = json.load(f)
    
    phase3_files = data.get("phase3", {}).get("files", {})
    
    for chunk_id, chunk_data in phase3_files.items():
        if not chunk_id.startswith(file_id):
            continue
        
        chunk_num = int(chunk_id.split('_c')[-1])
        
        for pattern, voice in pattern_map.items():
            start, end = pattern.split(':')
            start_num = int(start.replace('c', ''))
            end_num = float('inf') if end == '*' else int(end.replace('c', ''))
            
            if start_num <= chunk_num <= end_num:
                chunk_data['suggested_voice'] = voice
                print(f"Set {chunk_id} → {voice}")
                break
    
    with open(pipeline_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("✅ Voice assignments complete")

if __name__ == "__main__":
    pattern_map = {
        "c0001:c0100": "jim_locke",
        "c0101:c0200": "pamela_nagami",
        "c0201:*": "jim_locke"
    }
    
    set_voices_by_pattern("pipeline.json", sys.argv[1], pattern_map)
```

Usage:
```bash
python tools/set_chunk_voices.py my_book
```

---

## Troubleshooting

### Issue: CLI override not working

**Symptoms**: Phase 4 ignores `--voice` argument

**Fix**:
1. Check voice ID is valid:
   ```bash
   python -c "import json; print(list(json.load(open('configs/voices.json'))['voices'].keys()))"
   ```
2. Verify voice reference audio exists:
   ```bash
   ls phase4_tts/voice_references/*.wav
   ```

---

### Issue: Voice not found error

**Symptoms**: `FileNotFoundError: No reference audio found for voice_id`

**Fix**: Run voice reference preparation:
```bash
cd phase4_tts
poetry run python setup_voice_references.py
```

This downloads and prepares all voice reference audio files.

---

### Issue: Phase 3 suggestion ignored

**Symptoms**: Phase 4 uses default voice instead of Phase 3 suggestion

**Check Priority**:
1. Is there a CLI override? (`--voice`)
2. Is `tts_voice` set in `pipeline.json`? (Check top-level, not phase3)
3. Does Phase 3 output have `suggested_voice`?

**Fix**: Remove higher-priority overrides:
```bash
# Check pipeline.json
jq '.tts_voice' pipeline.json  # Should be null
jq '.phase3.files[].suggested_voice' pipeline.json  # Should show voice IDs
```

---

### Issue: Chunk-level override not applied

**Symptoms**: All chunks use same voice despite different `suggested_voice` values

**Fix**:
1. Verify Phase 3 ran successfully:
   ```bash
   jq '.phase3.status' pipeline.json  # Should be "success"
   ```

2. Check chunk data structure:
   ```bash
   jq '.phase3.files | keys' pipeline.json  # Should show chunk IDs
   ```

3. Ensure no CLI/pipeline.json override is blocking:
   ```bash
   jq '.tts_voice' pipeline.json  # Should be null
   ```

---

### Issue: Voice sounds wrong for genre

**Symptoms**: Philosophy book using thriller narrator

**Fix**: Check Phase 3 profile:
```bash
jq '.phase3.applied_profile' pipeline.json
```

If wrong profile:
```bash
# Re-run Phase 3 with correct profile
poetry run python -m phase3_chunking.chunker \
  --input /artifacts/text/book.cleaned.txt \
  --file-id book \
  --profile philosophy  # Force correct genre
```

---

## Quick Reference Card

| Scenario | Command |
|----------|---------|
| Auto-select | Run normally (no flags) |
| Force one voice | `--voice jim_locke` |
| Set default | Edit `pipeline.json` → `tts_voice: "voice_id"` |
| Per-chunk | Edit `pipeline.json` → `phase3.files.chunk_id.suggested_voice` |
| List voices | `jq '.voices \| keys' configs/voices.json` |
| Check selection | `jq '.phase3.files[].suggested_voice' pipeline.json` |

---

## Voice Reference Audio Sources

All voice references are sourced from LibriVox (public domain):

| Voice | Source URL |
|-------|------------|
| jim_locke | [Bertrand Russell - Mysticism & Logic](https://archive.org/download/mysticism_logic_1603_librivox/mysticismandlogic_01_russell_128kb.mp3) |
| tom_weiss | [The Moonstone](https://archive.org/download/moonstone_1810_librivox/moonstone_01_collins.mp3) |
| gareth_holmes | [Poetry Samples](https://archive.org/download/poems_gh_1710_librivox/poems_01_various.mp3) |
| ... | See `configs/voice_references.json` for complete list |

**Note**: Reference audio is automatically downloaded and prepared by `setup_voice_references.py`.

---

## Next Steps

1. **Test voice selection**: Run Phase 3 + 4 on sample file
2. **Experiment with overrides**: Try different voices to find favorites
3. **Create voice mappings**: Document which voices work best for your content

For questions or issues, check `TROUBLESHOOTING.md` or ask Claude for help!
