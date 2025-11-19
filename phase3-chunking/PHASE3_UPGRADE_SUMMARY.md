# Phase 3 Genre-Aware Chunking Upgrade

**Date**: October 18, 2025  
**Status**: ✅ Complete

## What Was Upgraded

Phase 3 has been enhanced with **genre-aware chunking** that automatically detects text genre and applies optimized chunking strategies for better TTS narration.

### New Files Created

1. **`profiles.py`** - Genre-specific chunking profiles
   - 5 profiles: philosophy, fiction, academic, memoir, technical, auto
   - Each with optimized word/character ranges and special rules
   
2. **`detect.py`** - Auto-classification logic
   - Rule-based heuristics for genre detection
   - Analyzes: sentence length, quotes, dialogue, citations, code
   - Returns genre with confidence score
   
3. **`voice_selection.py`** - Voice registry integration
   - Reads from `configs/voices.json`
   - Selects appropriate voice based on genre
   
4. **`chunker.py`** - New main entry point
   - Integrates all genre-aware features
   - Can be used alongside or instead of `main.py`
   
5. **`configs/voices.json`** - Voice registry
   - Defines 4 voices with genre preferences
   - TTS parameters for each voice

### Files Modified

- **`models.py`** - Added genre-aware fields:
  - `applied_profile`: Genre used (e.g., 'philosophy')
  - `genre_confidence`: Detection confidence (0-1)
  - `suggested_voice`: Selected voice ID

## How It Works

### 1. Genre Detection

```python
# Analyzes text for patterns:
- Philosophy: Long sentences, abstract concepts
- Fiction: High quote ratio, dialogue tags
- Academic: Citations, formal language, lists
- Memoir: First-person narrative, anecdotes
- Technical: Code blocks, instructional language
```

**Example**:
```
Input: "The Master said, 'Fine words and an insinuating appearance...'"
Output: philosophy (confidence: 0.85)
```

### 2. Profile-Based Chunking

| Profile | Word Range | Char Range | Special Rules |
|---------|-----------|------------|---------------|
| Philosophy | 280-450 | 1400-2250 | No semicolon splits, preserve arguments |
| Fiction | 200-350 | 1000-1750 | Preserve quotes, no mid-dialogue splits |
| Academic | 150-300 | 750-1500 | Preserve lists, citations |
| Memoir | 220-360 | 1100-1800 | Short direct address, emotional breaks |
| Technical | 150-300 | 750-1500 | Preserve code, formulas, steps |
| Auto | 200-400 | 1000-2000 | Heuristic detection, balanced |

### 3. Voice Selection

Each profile maps to preferred voices:
- **Philosophy/Academic** → `jim_locke` (measured, scholarly)
- **Fiction/Memoir** → `female_calm` (warm, engaging)
- **Technical/Auto** → `neutral_narrator` (clear, impartial)

## Testing

### Quick Test: Genre Detection

Run this to test genre detection on The Analects:

```powershell
cd phase3-chunking
poetry run python -c "
from src.phase3_chunking.detect import detect_genre

text = '''The Master said, 'Fine words and an insinuating appearance are seldom associated with true virtue.' The philosopher Tsang said, 'I daily examine myself on three points: -whether, in transacting business for others, I may have been not faithful; -whether, in intercourse with friends, I may have been not sincere; -whether I may have not mastered and practiced the instructions of my teacher.'''

metadata = {'title': 'The Analects', 'author': 'Confucius'}

genre, confidence, scores = detect_genre(text, metadata)
print(f'Detected genre: {genre}')
print(f'Confidence: {confidence:.2f}')
print(f'All scores: {scores}')
"
```

**Expected output**:
```
Detected genre: philosophy
Confidence: 0.65
All scores: {'philosophy': 0.65, 'fiction': 0.05, ...}
```

### Full Test: Chunking with Genre

```powershell
cd phase3-chunking

# Test with auto-detection (will detect philosophy)
poetry run python -m src.phase3_chunking.chunker `
  --file_id analects_test_v2 `
  --text_path "../phase2-extraction/extracted_text/analects_test_v2.txt" `
  --chunks_dir "chunks" `
  --profile auto `
  --pipeline_path "../pipeline.json" `
  -v
```

**Expected output**:
```
============================================================
PHASE 3: GENRE-AWARE CHUNKING
============================================================
File ID: analects_test_v2
Profile: auto
Auto-detected genre: philosophy (confidence: 0.65)
Using profile: philosophy
  Word range: 280-450
  Char range: 1400-2250
  Rules: {'no_semicolon_splits': True, 'add_context': True, ...}
Selected voice: jim_locke
...
PHASE 3 CHUNKING SUMMARY
============================================================
Applied Profile: philosophy
Genre Confidence: 0.65
Selected Voice: jim_locke
Status: success
Chunks created: 42
```

### Test Different Profiles

```powershell
# Force fiction profile
poetry run python -m src.phase3_chunking.chunker `
  --file_id test `
  --text_path "test.txt" `
  --profile fiction

# Force academic profile
poetry run python -m src.phase3_chunking.chunker `
  --file_id test `
  --text_path "test.txt" `
  --profile academic
```

## Integration with Existing Code

### Option 1: Use New chunker.py (Recommended)

```powershell
# Replace main.py calls with chunker.py
poetry run python -m phase3_chunking.chunker `
  --file_id <file_id> `
  --text_path <path> `
  --profile auto
```

### Option 2: Keep main.py (Backward Compatible)

The existing `main.py` still works as before! Genre-aware features are **optional enhancements**.

```powershell
# Old way still works
poetry run python -m phase3_chunking.main `
  --file_id <file_id>
```

## Voice Registry

Edit `configs/voices.json` to:
- Add new voices
- Change voice preferences for genres
- Modify TTS parameters

**Example**:
```json
{
  "voices": {
    "custom_voice": {
      "description": "My custom voice",
      "preferred_profiles": ["memoir"],
      "tts_engine_params": {
        "pitch": 0,
        "rate": 1.0
      }
    }
  }
}
```

## Troubleshooting

### Issue: "Voice registry not found"

**Fix**: Ensure `configs/voices.json` exists at monorepo root:
```powershell
# Should exist at:
audiobook-pipeline-styletts-personal/configs/voices.json
```

### Issue: Low genre confidence

**Action**: Use `--profile` to explicitly set genre instead of auto:
```powershell
--profile philosophy  # Instead of --profile auto
```

### Issue: Wrong genre detected

**Fix**: 
1. Check Phase 2 metadata for `suggested_tts_profile`
2. Explicitly set profile: `--profile fiction`
3. Improve genre detection rules in `detect.py`

## Next Steps

1. **Test on The Analects**: Run full chunking test (see above)
2. **Verify voice selection**: Check output includes `Selected Voice: jim_locke`
3. **Test other genres**: Try fiction/academic samples
4. **Integrate with orchestrator**: Update Phase 6 to call `chunker.py` instead of `main.py` (optional)

## Benefits

✅ **Better TTS quality**: Chunks optimized for each genre  
✅ **No mid-dialogue splits**: Fiction preserves complete conversations  
✅ **Logical completeness**: Philosophy preserves complex arguments  
✅ **Voice matching**: Automatic voice selection based on content  
✅ **Backward compatible**: Existing code still works  

---

**Ready to test!** Start with the Quick Test above, then run a full chunking test on The Analects.

