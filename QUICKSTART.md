# 🚀 Quick Start Guide
## Personal Audiobook Studio

Get up and running in 10 minutes.

---

## Installation

### 1. Install TTS Engines

Choose at least one (F5-TTS recommended):

```bash
# F5-TTS (Best quality, recommended)
cd /tmp
git clone https://github.com/SWivid/F5-TTS
cd F5-TTS
pip install -e .

# XTTS v2 (Alternative, great multilingual support)
pip install TTS

# Chatterbox (Already installed in your system)
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
4. Choose engine: **F5-TTS (Expressive)**
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

Generate the same text with all 3 engines:

```bash
# Test text
TEXT="Philosophy is the art of living well."

# F5-TTS (best quality)
python test_engine.py --engine f5 --text "$TEXT"

# XTTS (versatile)
python test_engine.py --engine xtts --text "$TEXT"

# Chatterbox (fast)
python test_engine.py --engine chatterbox --text "$TEXT"

# Listen and compare quality!
```

---

## Recommended First Projects

### 1. **Philosophy Book** (Your Specialty)
```
Book: Marcus Aurelius - Meditations
Voice: george_mckayland
Engine: F5-TTS (Expressive)
Preset: audiobook_intimate
Time: ~4-5 hours
Quality: Insanely great
```

### 2. **Classic Fiction**
```
Book: Edgar Allan Poe - The Raven
Voice: vincent_price_01
Engine: F5-TTS (Expressive)
Preset: audiobook_dynamic
Time: ~30 minutes
Quality: Chilling
```

### 3. **Short Test** (Validate Setup)
```
Book: Any short story (5-10 pages)
Voice: Any
Engine: Chatterbox (fast)
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

### F5-TTS Import Error

```bash
# Verify installation
python -c "from f5_tts.api import F5TTS; print('OK')"

# If fails, reinstall:
cd /tmp/F5-TTS
pip install -e . --force-reinstall
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
2. 📊 Compare engines (F5 vs XTTS vs Chatterbox)
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
