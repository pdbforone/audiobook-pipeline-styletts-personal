# Phase 5 Execution Guide - Audio Enhancement
# ============================================

## Overview
Phase 5 will:
1. Read all audio chunks from Phase 4 (from pipeline.json)
2. Apply noise reduction to each chunk
3. Normalize volume and LUFS (-23 dB target)
4. Stitch all chunks together with 0.5s crossfades
5. Export final audiobook as MP3 with metadata
6. Update pipeline.json with results

## Prerequisites
✅ Phase 4 must be completed successfully
✅ Audio chunks must exist in: phase4_tts/audio_chunks/
✅ pipeline.json must have phase4 data

## Configuration
File: phase5_enhancement/config.yaml

Key Settings:
- Sample Rate: 48000 Hz (upsampled from Phase 4's 24000 Hz)
- LUFS Target: -23.0 dB (industry standard for audiobooks)
- Crossfade: 0.5 seconds between chunks
- Workers: 2 parallel threads
- Quality: SNR threshold 15 dB minimum

Output:
- Enhanced chunks → phase5_enhancement/processed/enhanced_XXXX.wav
- Final audiobook → phase5_enhancement/processed/audiobook.mp3
- Playlist → phase5_enhancement/processed/audiobook.m3u

## Execution Methods

### Method 1: Via Orchestrator (RECOMMENDED)
```bash
cd path\to\audiobook-pipeline-styletts-personal\phase6_orchestrator

python orchestrator.py ..\input\The_Analects_of_Confucius_20240228.pdf --phases 5 --pipeline-json ..\pipeline.json
```

**Advantages:**
- Automatic resume from checkpoints
- Error handling and retries
- Progress reporting with Rich
- Consistent with Phase 4 workflow

**Expected Output:**
```
▶ Running Phase 5...
Phase 5 directory: C:\...\phase5_enhancement
Command: poetry run python src\phase5_enhancement\main.py
Processing 500 audio chunks in parallel...
Enhancement complete: 500 successful, 0 failed
Final audiobook created: processed/audiobook.mp3
Duration: 3600.5 seconds (60 minutes)
✓ Phase 5 completed successfully
```

---

### Method 2: Direct Execution (For Testing)
```bash
cd path\to\audiobook-pipeline-styletts-personal\phase5_enhancement

# Install dependencies (if not already)
poetry install --no-root

# Run Phase 5
poetry run python src\phase5_enhancement\main.py --config config.yaml
```

**Options:**
- `--config config.yaml` - Specify config file (default: config.yaml)
- `--chunk_id 441` - Process only a specific chunk (for testing)
- `--skip_concatenation` - Skip final MP3 creation (process chunks only)

---

### Method 3: Test Single Chunk First
```bash
cd path\to\audiobook-pipeline-styletts-personal\phase5_enhancement

# Test on chunk_441 only
poetry run python src\phase5_enhancement\main.py --chunk_id 441 --skip_concatenation
```

**This will:**
- Process only chunk_441.wav
- Apply noise reduction + LUFS normalization
- Save to: processed/enhanced_0441.wav
- Skip final MP3 creation (for quick testing)

**Verify:**
```bash
# Play the enhanced chunk
start processed\enhanced_0441.wav

# Compare with original
start ..\phase4_tts\audio_chunks\chunk_441.wav
```

Listen for:
- ✅ Cleaner audio (less background noise)
- ✅ Consistent volume (not too quiet/loud)
- ✅ No distortion or clipping
- ✅ Same content (no missing words)

---

## Expected Runtime

| Chunks | Estimated Time | Notes |
|--------|----------------|-------|
| 1 chunk | ~5-10 seconds | Testing single chunk |
| 100 chunks | ~5-10 minutes | Partial processing |
| 500 chunks | ~25-50 minutes | Full audiobook |

**Factors:**
- CPU speed (2 workers in parallel)
- Audio length per chunk (~8-12 seconds each)
- Noise reduction complexity
- Disk I/O speed

---

## Monitoring Progress

### Console Output
```
2025-10-03 21:00:00 - INFO - Processing 500 audio chunks in parallel...
2025-10-03 21:00:15 - INFO - Volume normalized chunk 0: RMS 0.0234 → 0.1234
2025-10-03 21:00:15 - INFO - Saved enhanced chunk: processed/enhanced_0000.wav
2025-10-03 21:00:16 - INFO - Volume normalized chunk 1: RMS 0.0198 → 0.1156
...
2025-10-03 21:25:30 - INFO - Creating final audiobook...
2025-10-03 21:27:00 - INFO - Final audiobook created: processed/audiobook.mp3
2025-10-03 21:27:00 - INFO - Duration: 3600.5 seconds
```

### Log File
Real-time logging → `phase5_enhancement/audio_enhancement.log`

```bash
# Watch the log in real-time (PowerShell)
Get-Content audio_enhancement.log -Wait -Tail 20
```

---

## Output Verification

### 1. Check Processed Chunks
```bash
cd processed
dir enhanced_*.wav

# Should see 500 files (or however many chunks Phase 4 produced)
# enhanced_0000.wav through enhanced_0499.wav
```

### 2. Play Final Audiobook
```bash
start processed\audiobook.mp3
```

**Listen for:**
- ✅ Smooth transitions between chunks (no pops/clicks)
- ✅ Consistent volume throughout
- ✅ Clear speech (no excessive noise)
- ✅ No missing content

### 3. Check Metadata
```bash
# View MP3 metadata (PowerShell)
$mp3 = [System.IO.FileInfo]"processed\audiobook.mp3"
$shell = New-Object -ComObject Shell.Application
$folder = $shell.NameSpace($mp3.DirectoryName)
$file = $folder.ParseName($mp3.Name)
0..287 | ForEach-Object { "$($folder.GetDetailsOf($null, $_)): $($folder.GetDetailsOf($file, $_))" } | Where-Object { $_ -match "Title|Artist|Album" }
```

**Expected:**
- Title: "The Analects of Confucius"
- Artist: "Confucius"
- Album: "Audiobook"

---

## Troubleshooting

### Error: "No audio chunks found to process"
**Cause:** Phase 4 not completed or pipeline.json missing phase4 data

**Fix:**
1. Check pipeline.json has phase4 section:
   ```bash
   python -c "import json; p=json.load(open('../pipeline.json')); print('Phase 4 files:', list(p.get('phase4',{}).get('files',{}).keys()))"
   ```
2. If empty, re-run Phase 4

---

### Error: "Audio file not found"
**Cause:** Chunk paths in pipeline.json don't match actual files

**Fix:**
1. Check chunk files exist:
   ```bash
   cd ..\phase4_tts\audio_chunks
   dir chunk_*.wav | Measure-Object
   ```
2. Verify paths in pipeline.json:
   ```bash
   python -c "import json; p=json.load(open('../pipeline.json')); paths=p.get('phase4',{}).get('files',{}).get('The_Analects_of_Confucius_20240228',{}).get('chunk_audio_paths',[]); print(f'Found {len(paths)} paths'); print('First 3:', paths[:3])"
   ```

---

### Warning: "Quality failed for chunk_XXX"
**Cause:** SNR below threshold (15 dB) after enhancement

**Impact:** Non-critical - Phase 5 will retry with fallback (skip noise reduction)

**If persistent:**
1. Lower SNR threshold in config.yaml:
   ```yaml
   snr_threshold: 10.0  # Was 15.0
   ```
2. Disable quality validation:
   ```yaml
   quality_validation_enabled: false
   ```

---

### Error: "Processing timeout"
**Cause:** Chunk took >60 seconds to process (very rare)

**Fix:** Increase timeout in config.yaml:
```yaml
processing_timeout: 120  # Was 60
```

---

## Quality Metrics

After completion, check pipeline.json for metrics:

```bash
python -c "import json; p=json.load(open('../pipeline.json')); m=p.get('phase5',{}).get('metrics',{}); print(f'Successful: {m.get(\"successful\")}'); print(f'Failed: {m.get(\"failed\")}'); print(f'Avg SNR Improvement: {m.get(\"avg_snr_improvement\",0):.1f} dB'); print(f'Total Duration: {m.get(\"total_duration\",0)/60:.1f} minutes')"
```

**Good Metrics:**
- Successful: 490-500 chunks (>98% success rate)
- Failed: 0-10 chunks (<2% failure)
- SNR Improvement: 2-8 dB average
- Total Duration: 25-50 minutes

---

## Next Steps After Phase 5

1. **Listen to final audiobook:**
   ```bash
   start processed\audiobook.mp3
   ```

2. **Check file size:**
   ```bash
   Get-Item processed\audiobook.mp3 | Select-Object Length, LastWriteTime
   ```
   - Expected: 50-150 MB (depending on book length)

3. **Copy to final destination** (optional):
   ```bash
   copy processed\audiobook.mp3 path\to\Music\Audiobooks\
   ```

4. **Review pipeline.json** for full pipeline summary:
   ```bash
   python -c "import json; p=json.load(open('../pipeline.json')); print('Pipeline Status:'); [print(f'  Phase {i}: {p.get(f\"phase{i}\",{}).get(\"status\",\"pending\")}') for i in range(1,6)]"
   ```

---

## Resume from Failure

If Phase 5 fails midway, it will auto-resume:

```bash
# Just re-run the same command
python orchestrator.py ..\input\The_Analects_of_Confucius_20240228.pdf --phases 5 --pipeline-json ..\pipeline.json
```

**Resume Logic:**
- Checks pipeline.json for completed chunks
- Skips already-processed chunks
- Only processes remaining/failed chunks
- Updates final MP3 with all chunks

---

## Performance Tips

1. **For faster processing**, increase workers:
   ```yaml
   max_workers: 4  # Was 2 (use CPU core count)
   ```

2. **For lower memory usage**, decrease workers:
   ```yaml
   max_workers: 1  # Sequential processing
   ```

3. **Skip noise reduction** (faster, lower quality):
   ```yaml
   noise_reduction_factor: 0.0  # Was 0.8
   ```

4. **Skip volume normalization** (faster):
   ```yaml
   enable_volume_normalization: false  # Was true
   ```

---

**Ready to run!** Use Method 1 (orchestrator) for production, or Method 3 (single chunk) for testing first.


