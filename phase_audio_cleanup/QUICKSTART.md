# Audio Cleanup - Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Step 1: Install FFmpeg (One-Time Setup)

**Windows (using Chocolatey):**
```powershell
choco install ffmpeg
```

**Or download from**: https://ffmpeg.org/download.html

### Step 2: Install Python Dependencies

```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase_audio_cleanup
poetry install
```

This will install:
- faster-whisper (speech-to-text)
- pydub (audio editing)
- pyyaml (config)

First run will also download the Whisper "base" model (~150MB).

### Step 3: Test with Your Problematic Chunk

**Dry Run First (Safe - No Changes):**
```bash
poetry run python -m audio_cleanup.main \
  --input "..\audio_chunks\the meditations, by Marcus Aurelius_chunk_004.mp3" \
  --dry-run \
  --verbose
```

**Expected Output:**
```
Transcribing: the meditations, by Marcus Aurelius_chunk_004.mp3
Found 'you need to add text for me to talk' at 0.00s - 3.50s
DRY RUN: Would remove 1 segment(s)
```

**If Detection Works, Clean It:**
```bash
poetry run python -m audio_cleanup.main \
  --input "..\audio_chunks\the meditations, by Marcus Aurelius_chunk_004.mp3" \
  --output "..\audio_chunks_cleaned\the meditations, by Marcus Aurelius_chunk_004.mp3"
```

### Step 4: Review Results

1. **Check cleaned audio**: Play `../audio_chunks_cleaned/chunk_004.mp3`
2. **Review transcript**: Open `chunk_004.srt` to see what was transcribed
3. **Verify removal**: Confirm bad phrase is gone

### Step 5: Batch Process All Chunks (When Ready)

```bash
poetry run python -m audio_cleanup.main \
  --input-dir "..\audio_chunks" \
  --output-dir "..\audio_chunks_cleaned" \
  --batch
```

---

## ⚙️ Common Adjustments

### If Detection Accuracy is Low

Use a larger model:
```bash
poetry run python -m audio_cleanup.main \
  --input chunk.mp3 \
  --output cleaned.mp3 \
  --model small  # Better accuracy, slower
```

### Add More Phrases to Remove

Edit `config/phrases.yaml`:
```yaml
target_phrases:
  - "You need to add text for me to talk"
  - "You need to add text for me to talk."
  - "Another bad phrase"
```

### Process Different Audio Format

```bash
poetry run python -m audio_cleanup.main \
  --input chunk.wav \
  --output cleaned.mp3  # Converts to MP3
```

---

## 🐛 Quick Troubleshooting

**"FFmpeg not found"**
→ Install FFmpeg (see Step 1)

**"Model not found"**
→ First run downloads model automatically (~150MB)

**"Phrase not detected"**
→ Check spelling in config/phrases.yaml
→ Try --verbose to see transcription
→ Try --model small for better accuracy

**"Out of memory"**
→ Close other apps
→ Use --model tiny (smaller, faster)

---

## 📋 Next Steps

Once you've tested successfully:

1. ✅ Process all problematic chunks
2. ✅ Listen to verify quality
3. ✅ Document any remaining issues
4. ⏳ Consider integration with orchestrator (later)

---

**Need Help?** Check the full README.md for detailed documentation.
