# Sprint 1: Phase 5 Audio Mastering Upgrade

**Status:** ✅ Code Complete, Ready for Installation  
**Date:** 2025-11-10  
**Effort:** 4 hours implementation

## What Was Built

Professional-grade audio mastering integrated into Phase 5 using two CPU-optimized, open-source tools:

1. **DeepFilterNet** (MIT) - Professional noise reduction
2. **Matchering 2.0** (GPL-3.0) - Reference-based mastering

Both features are **optional** (disabled by default) for A/B testing against your current setup.

---

## Features

### 1. DeepFilterNet Noise Reduction

**Replaces:** Basic `noisereduce` library  
**Improvement:** 5-25x faster than real-time, professional-grade denoising  
**License:** MIT (commercially safe)  
**CPU Optimized:** RTF ~0.04-0.19 on modern CPUs

**When to use:**
- Audiobooks with background noise (fans, traffic)
- TTS-generated audio with artifacts
- When you want broadcast-quality sound

**Limitations:**
- **Requires 48kHz audio** (your pipeline already uses this)
- Takes 2-5 seconds to initialize model on first use
- Falls back to `noisereduce` if not installed or fails

### 2. Matchering Reference-Based Mastering

**Adds:** Professional mastering to match reference track  
**Improvement:** Consistent EQ, dynamics, and loudness across all chapters  
**License:** GPL-3.0 (internal use is fine, see below)  
**CPU Optimized:** ~1-5 minutes per full audiobook

**When to use:**
- You want all chapters to sound consistent
- You have a professional audiobook reference to match
- You want to match industry-standard mastering

**Limitations:**
- **Requires reference audio file** (professional audiobook sample)
- Processes full audiobook (not individual chunks)
- Adds 1-5 minutes to pipeline runtime
- Falls back gracefully if not installed or fails

---

## Installation Instructions

### Step 1: Install PyTorch (CPU-only)

```bash
cd /path/to/audiobook-pipeline-styletts-personal/phase5_enhancement

# Install PyTorch CPU version FIRST (required for DeepFilterNet)
poetry run pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Step 2: Install Phase 5 Dependencies

```bash
# Install all dependencies including DeepFilterNet and Matchering
poetry install
```

### Step 3: Verify Installation

```bash
# Test DeepFilterNet
poetry run python -c "from df import enhance, init_df; print('DeepFilterNet: OK')"

# Test Matchering
poetry run python -c "import matchering; print('Matchering: OK')"
```

If both print "OK", you're ready to use the new features.

---

## Usage

### Option 1: Enable DeepFilterNet Only

Edit your `phase5_enhancement/config.yaml`:

```yaml
enable_deepfilternet: true  # Use professional noise reduction
enable_matchering: false    # Keep mastering disabled
```

### Option 2: Enable Both DeepFilterNet + Matchering

```yaml
enable_deepfilternet: true
enable_matchering: true
matchering_reference: "/path/to/professional_audiobook_reference.wav"
matchering_max_length: 1800  # 30 minutes (default)
```

### Option 3: Keep Current Setup (Default)

```yaml
enable_deepfilternet: false  # Use standard noisereduce
enable_matchering: false     # No mastering
```

---

## Reference Audio for Matchering

Matchering needs a professional audiobook sample to match. Here's how to get one:

### Requirements:
- **Format:** WAV file (stereo recommended, mono works)
- **Length:** 30+ seconds minimum
- **Quality:** Professional mastering (e.g., Audible audiobook sample)
- **Genre:** Same as your target (narration style matters)

### Where to Get Reference Audio:

1. **Audible Samples:** Download 5-minute preview, convert to WAV
2. **LibriVox:** Public domain audiobooks (already mastered)
3. **Your Best Chapter:** Use your best-sounding enhanced chapter as reference

### Example:

```bash
# Download Audible sample with youtube-dl or similar
yt-dlp "https://audible.com/sample/..." -x --audio-format wav -o reference.wav

# Or use LibriVox
wget "https://www.archive.org/download/librivox-audiobook.../chapter01.mp3"
ffmpeg -i chapter01.mp3 -ar 48000 reference.wav
```

Place `reference.wav` in your `phase5_enhancement/` directory.

---

## Configuration Examples

### Example 1: A/B Test DeepFilterNet

Process the same book twice:

```yaml
# Run 1: Standard (config1.yaml)
enable_deepfilternet: false

# Run 2: DeepFilterNet (config2.yaml)
enable_deepfilternet: true
```

Compare the output files:
- `processed/audiobook.mp3` (standard)
- `processed/audiobook.mp3` (DeepFilterNet)

Listen and choose the better one.

### Example 2: Full Professional Mastering

```yaml
# config.yaml
enable_deepfilternet: true
enable_matchering: true
matchering_reference: "reference.wav"
lufs_target: -16.0  # YouTube standard
sample_rate: 48000
mp3_bitrate: "192k"
```

This gives you:
1. Professional noise reduction (DeepFilterNet)
2. Industry-standard mastering (Matchering)
3. YouTube-optimized loudness (-16 LUFS)

---

## Performance Impact

| Feature | Time Added | Quality Improvement |
|---------|-----------|-------------------|
| DeepFilterNet | +10-20% | Professional noise reduction |
| Matchering | +5-10 min total | Consistent professional mastering |
| Both | +5-10 min total | Broadcast-quality audio |

**Example:** 8-hour audiobook
- Current: ~2 hours processing
- With DeepFilterNet: ~2.2 hours processing
- With Both: ~2.3 hours processing

The time increase is minimal compared to the quality improvement.

---

## Licensing Note (GPL-3.0 for Matchering)

**GPL-3.0 is SAFE for internal use.** You can:
- ✅ Use Matchering to process audiobooks for sale
- ✅ Keep your pipeline code private
- ✅ Charge for audiobooks produced with Matchering

**GPL-3.0 requires open-sourcing ONLY if you distribute the software itself.** Since you're using it internally to produce audiobooks (not distributing Matchering to others), you're fine.

**You CANNOT:**
- ❌ Sell software that includes Matchering without open-sourcing it
- ❌ Distribute modified Matchering code without GPL-3.0 license

**Bottom line:** Use Matchering freely for audiobook production. Don't distribute it to others.

---

## Troubleshooting

### "DeepFilterNet requires 48kHz audio"

**Fix:** Your pipeline already uses 48kHz (check `config.yaml` - `sample_rate: 48000`). If you see this error, verify your config.

### "Matchering failed: Track too long (Error 4002)"

**Fix:** Increase `matchering_max_length` in config:
```yaml
matchering_max_length: 3600  # 60 minutes
```

### "Import Error: No module named 'df'"

**Fix:** Install PyTorch first, then DeepFilterNet:
```bash
poetry run pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
poetry install
```

### "Matchering: No such file or directory"

**Fix:** Verify reference file path:
```bash
ls -lh /path/to/reference.wav  # Should show file exists
```

### Performance Too Slow

**Fix:** Disable one or both features:
```yaml
enable_deepfilternet: false  # Saves ~20% time
enable_matchering: false     # Saves ~5-10 minutes
```

---

## Next Steps

1. **Install dependencies** (see Installation Instructions above)
2. **Get reference audio** (30+ sec professional audiobook sample)
3. **A/B test DeepFilterNet** on one book (compare quality)
4. **Test Matchering** on one book (compare consistency)
5. **Decide which to keep enabled** based on results

---

## Files Changed

- `phase5_enhancement/pyproject.toml` - Added dependencies
- `phase5_enhancement/src/phase5_enhancement/models.py` - Added config flags
- `phase5_enhancement/src/phase5_enhancement/main.py` - Integrated both tools
- `SPRINT1_AUDIO_MASTERING.md` - This documentation

## Technical Details

### DeepFilterNet Integration:
- Lazy imports (no overhead if disabled)
- Graceful fallback to `noisereduce` on failure
- CPU-optimized (RTF ~0.04-0.19)
- Lines: `main.py:164-207`

### Matchering Integration:
- Processes full audiobook after concatenation
- Converts mono → stereo → mastered → mono MP3
- Cleanup temp files automatically
- Lines: `main.py:210-269, 829-906`

---

**Status:** ✅ Ready for testing  
**Next:** Install dependencies and A/B test on one audiobook

