# Voice Override Guide

**How to manually control voice selection at any level**

---

## 📋 Override Priority (Highest to Lowest)

1. **Command-line flag** - `--voice` parameter
2. **Pipeline.json file-level** - `tts_voice` field per file
3. **Pipeline.json global** - Top-level `tts_voice` 
4. **Phase 3 genre selection** - Auto-selected based on detected genre
5. **Default fallback** - `neutral_narrator`

---

## 🎯 Method 1: Command-Line Override (Highest Priority)

### Phase 3 - Genre-Aware Chunking

Override the auto-detected genre profile AND voice:

```powershell
# Force specific voice for chunking
poetry run python -m phase3_chunking.chunker `
  --file_id my_book `
  --text_path "text.txt" `
  --profile philosophy `
  --voice david_barnes  # ← OVERRIDE: Use David Barnes (British)

# List available voices
poetry run python -m phase3_chunking.chunker --list-voices
```

**Output**:
```
Available voices:
- landon_elkind: Landon D. C. Elkind (male, American, philosophy)
- pamela_nagami: Pamela Nagami (female, American, philosophy)
- david_barnes: David Barnes (male, British BBC, poetry/philosophy)
- ruth_golding: Ruth Golding (female, British RP, fiction/poetry)
...
```

### Phase 4 - TTS Synthesis

Override voice for synthesis:

```powershell
# Force specific voice reference
poetry run python src/main.py `
  --file_id my_book `
  --voice ruth_golding  # ← OVERRIDE: Use Ruth Golding voice
```

---

## 🗂️ Method 2: Pipeline.json File-Level Override

Set voice per file in `pipeline.json`:

```json
{
  "phase3": {
    "files": {
      "book1": {
        "tts_voice_override": "david_barnes",  // ← British male for this file
        "chunk_paths": [...]
      },
      "book2": {
        "tts_voice_override": "ruth_golding",  // ← British female for this file
        "chunk_paths": [...]
      }
    }
  }
}
```

**How it works**:
- Phase 3 writes `tts_voice_override` if you use `--voice` flag
- Phase 4 reads `tts_voice_override` and uses it instead of auto-selection

---

## 🌍 Method 3: Pipeline.json Global Override

Set default voice for entire pipeline:

```json
{
  "tts_voice": "landon_elkind",  // ← Use Landon Elkind for ALL files
  "tts_profile": "philosophy",
  "phase2": {...},
  "phase3": {...}
}
```

**Use case**: When processing multiple philosophy books, set once and all use same voice.

---

## 🎨 Method 4: Per-Chunk Override (Advanced)

For mixed-content books (e.g., anthology with multiple authors):

```json
{
  "phase4": {
    "chunk_voice_overrides": {
      "book1_chunk_001": "david_barnes",   // Chapter 1: British narrator
      "book1_chunk_050": "landon_elkind",  // Chapter 2: American narrator
      "book1_chunk_100": "pamela_nagami"   // Chapter 3: Female narrator
    }
  }
}
```

**How to set**:
```powershell
# Synthesize specific chunk with specific voice
poetry run python src/main.py `
  --file_id my_book `
  --chunk_id 50 `
  --voice landon_elkind
```

---

## 🔧 Implementation Examples

### Example 1: British Philosophy Book

**Scenario**: You're processing a British philosophy text and want David Barnes (BBC English).

**Phase 3**:
```powershell
poetry run python -m phase3_chunking.chunker `
  --file_id british_philosophy `
  --text_path "text.txt" `
  --profile philosophy `
  --voice david_barnes
```

**Phase 4**:
```powershell
# Will automatically use david_barnes from Phase 3
poetry run python src/main.py --file_id british_philosophy
```

---

### Example 2: Fiction with Female British Narrator

**Scenario**: Classic British fiction, prefer Ruth Golding.

**Phase 3**:
```powershell
poetry run python -m phase3_chunking.chunker `
  --file_id pride_prejudice `
  --text_path "austen.txt" `
  --profile fiction `
  --voice ruth_golding
```

---

### Example 3: Mixed Anthology

**Scenario**: Anthology with 3 authors, want different voices for each section.

**Step 1**: Process normally
```powershell
poetry run python -m phase3_chunking.chunker `
  --file_id anthology `
  --text_path "anthology.txt" `
  --profile auto
```

**Step 2**: Manually edit `pipeline.json`
```json
{
  "phase4": {
    "chunk_voice_overrides": {
      "anthology_chunk_001": "david_barnes",   // Author 1 (British)
      "anthology_chunk_050": "landon_elkind",  // Author 2 (American)
      "anthology_chunk_100": "pamela_nagami"   // Author 3 (Female)
    }
  }
}
```

**Step 3**: Synthesize (will use different voices)
```powershell
poetry run python src/main.py --file_id anthology
```

---

## 📝 Quick Reference: All Override Methods

| Method | Scope | Priority | How to Set |
|--------|-------|----------|------------|
| CLI flag | Single run | **Highest** | `--voice <voice_id>` |
| File-level JSON | Per file | High | Edit `phase3.files.<file_id>.tts_voice_override` |
| Global JSON | All files | Medium | Edit top-level `tts_voice` |
| Per-chunk JSON | Per chunk | High | Edit `phase4.chunk_voice_overrides.<chunk_id>` |
| Auto-detection | Default | **Lowest** | Automatic from Phase 3 genre |

---

## 🎤 List All Available Voices

### From Command Line

```powershell
# Phase 3 - List from voice registry
poetry run python -m phase3_chunking.chunker --list-voices

# Phase 4 - List available references
poetry run python src/main.py --list-voices
```

### From Python

```python
from phase3_chunking.voice_selection import list_available_voices

voices = list_available_voices()
for voice_id, description in voices.items():
    print(f"{voice_id}: {description}")
```

**Output**:
```
landon_elkind: Measured, analytical tone for philosophy
pamela_nagami: Clear, authoritative female voice
david_barnes: BBC English male voice
ruth_golding: RP/BBC English female voice
...
```

---

## 🔍 Finding the Right Voice

### By Genre

```python
from phase3_chunking.voice_selection import load_voice_registry

registry = load_voice_registry()
philosophy_voices = [
    v_id for v_id, v_data in registry['voices'].items()
    if 'philosophy' in v_data['preferred_profiles']
]
print(f"Philosophy voices: {philosophy_voices}")
```

### By Accent

```python
british_voices = [
    v_id for v_id, v_data in registry['voices'].items()
    if 'British' in v_data.get('accent', '')
]
print(f"British voices: {british_voices}")
```

### By Gender

```python
female_voices = [
    v_id for v_id, v_data in registry['voices'].items()
    if v_data.get('gender') == 'female'
]
print(f"Female voices: {female_voices}")
```

---

## 💡 Tips & Best Practices

### ✅ DO

- **Listen to samples first** - Download LibriVox samples before choosing
- **Match accent to content** - British literature → British voice
- **Test with one chunk** - Use `--chunk_id 0 --voice <voice>` to test
- **Document your choice** - Add note in pipeline.json why you chose voice

### ❌ DON'T

- **Mix wildly different voices** - Jarring transitions confuse listeners
- **Override every chunk** - Only use per-chunk for intentional variety
- **Ignore genre matches** - Auto-selection usually works well

---

## 🚨 Troubleshooting

### Override Not Working

**Symptom**: Phase 4 still uses auto-selected voice despite override.

**Fix**: Check priority order:
1. Verify `--voice` flag spelling
2. Check `pipeline.json` for conflicting overrides
3. Ensure voice ID exists in `configs/voices.json`

**Debug**:
```powershell
# Check what voice Phase 4 is using
poetry run python src/main.py --file_id test --verbose
```

Look for log line:
```
Using voice: <voice_id> (source: <cli|file_override|global|auto>)
```

---

### Voice Not Available

**Symptom**: `Voice '<voice_id>' not found`

**Fix**: 
1. List available voices: `--list-voices`
2. Check spelling (case-sensitive!)
3. Verify `configs/voices.json` includes the voice
4. For Phase 4, ensure `configs/voice_references.json` has reference audio

---

## 📚 Examples by Use Case

### Academic Lecture Series
```powershell
# American male, scholarly
--profile philosophy --voice landon_elkind
```

### British Poetry Collection
```powershell
# British male, rhythmic
--profile poetry --voice gareth_holmes
```

### Horror Anthology
```powershell
# Female, atmospheric
--profile fiction --voice bella_bolster
```

### Classic British Fiction
```powershell
# Female British RP
--profile fiction --voice ruth_golding
```

### Theology/Medieval Texts
```powershell
# Contemplative male
--profile academic --voice eric_metzler
```

---

**Need more voices?** See `ADDING_NEW_VOICES.md` for instructions on adding custom narrators from LibriVox or your own recordings.
