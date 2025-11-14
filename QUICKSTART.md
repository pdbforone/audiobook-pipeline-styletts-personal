# 🚀 Quick Start Guide
## Personal Audiobook Studio

Get up and running in 10 minutes.

> **Update (Nov 2025):** F5-TTS has been removed to keep the workstation lean.  
> XTTS v2 is now the expressive default, with Kokoro-onnx as a fast CPU backup.

---

## Installation

### 1. Install TTS Engines

Install both for the best quality + fallback combo:

```bash
# XTTS v2 (primary expressive engine)
pip install TTS

# Kokoro-onnx (fast CPU backup)
pip install kokoro-onnx soundfile

# Better phonemes (optional but nice)
sudo apt-get install espeak-ng
```

### 2. Install Professional Audio Processing

```bash
# For pro-grade mastering (highly recommended)
pip install pedalboard

# Already installed: pyloudnorm, librosa, numpy
```

### 3. Install UI

```bash
cd ui
pip install -r requirements.txt

# Or directly:
pip install gradio>=4.0.0
```

---

## First Audiobook in 3 Steps

### Step 1: Launch Studio

```bash
python ui/app.py
```

Opens at `http://localhost:7860`

### Step 2: Create Audiobook

1. Click "📖 Single Book" tab
2. Upload your book (.epub, .pdf, .txt)
3. Select voice: **george_mckayland** (for philosophy)
4. Choose engine: **XTTS (Expressive)**
5. Pick preset: **audiobook_intimate**
6. Click **🎬 Generate Audiobook**

### Step 3: Listen & Enjoy

Find your audiobook in:
```
phase5_enhancement/processed/
```

---

## Test Without UI (Command Line)

### Generate Sample Audio

```bash
cd phase4_tts

# Quick test with Chatterbox (fast)
poetry run python src/main.py \
  --file_id "test" \
  --text "To be or not to be, that is the question." \
  --voice george_mckayland \
  --engine chatterbox
```

### Apply Professional Mastering

```bash
cd phase5_enhancement

# Master with "intimate" preset
poetry run python -c "
from src.phase5_enhancement.mastering import MasteringEngine
import librosa
import soundfile as sf

# Load audio
audio, sr = librosa.load('input.wav', sr=48000, mono=True)

# Master
engine = MasteringEngine()
result = engine.master(audio, sr, preset='audiobook_intimate')

# Save
sf.write('output_mastered.wav', result.audio, sr)
print(f'LUFS: {result.metrics[\"lufs\"]}')
"
```

---

## Engine Comparison Test

Generate the same text with both engines:

```bash
# Test text
TEXT="Philosophy is the art of living well."

# XTTS (expressive)
python test_engine.py --engine xtts --text "$TEXT"

# Kokoro (fast)
python test_engine.py --engine kokoro --text "$TEXT"

# Listen and compare quality!
```

---

## Recommended First Projects

### 1. **Philosophy Book** (Your Specialty)
```
Book: Marcus Aurelius - Meditations
Voice: george_mckayland
Engine: XTTS (Expressive)
Preset: audiobook_intimate
Time: ~4-5 hours
Quality: Insanely great
```

### 2. **Classic Fiction**
```
Book: Edgar Allan Poe - The Raven
Voice: vincent_price_01
Engine: XTTS (Expressive)
Preset: audiobook_dynamic
Time: ~30 minutes
Quality: Chilling
```

### 3. **Short Test** (Validate Setup)
```
Book: Any short story (5-10 pages)
Voice: Any
Engine: Kokoro (fast)
Preset: minimal
Time: ~10 minutes
Quality: Good for testing
```

---

## Troubleshooting

### UI Won't Start

```bash
# Check Gradio installation
pip install --upgrade gradio

# Check port availability
lsof -i :7860

# Use different port
python ui/app.py --server-port 8080
```

### XTTS Import Error

```bash
# Verify installation
python -c "from TTS.api import TTS; print('OK')"

# If fails, reinstall:
pip install --upgrade --force-reinstall TTS
```

### Audio Quality Issues

```bash
# Install pedalboard for pro mastering
pip install pedalboard

# Verify
python -c "import pedalboard; print('OK')"
```

### Voice Not Found

Check paths in:
```
phase4_tts/configs/voice_references.json
```

Update paths to match your system.

---

## Next Steps

1. ✅ Generate your first audiobook
2. 📊 Compare engines (XTTS vs Kokoro)
3. 🎚️ Try different mastering presets
4. 🎤 Add your own voice to library
5. 📦 Queue a batch of books overnight

Read full guide: **CRAFT_EXCELLENCE_VISION.md**

---

**Ready?**

```bash
python ui/app.py
```

**Let's craft something insanely great.**
