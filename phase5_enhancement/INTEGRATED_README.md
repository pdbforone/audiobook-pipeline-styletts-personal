# Phase 5: Integrated Audio Enhancement with Phrase Cleanup

## 🎯 What's New

Phase 5 now includes **automatic phrase cleanup** integrated directly into the audio enhancement pipeline. This removes unwanted TTS phrases (like "You need to add some text for me to talk") **before** audio enhancement, ensuring a seamless audiobook experience.

## 🔧 How It Works

### Processing Flow

```
1. Load Audio Chunk
   ↓
2. 🧹 PHRASE CLEANUP (NEW)
   - Transcribe with Whisper
   - Detect target phrases
   - Remove matched segments
   - Smooth transitions with crossfades
   ↓
3. Volume Normalization
   ↓
4. Noise Reduction
   ↓
5. LUFS Normalization
   ↓
6. Save Enhanced Chunk
```

### Key Features

- **Smart Detection**: Uses Whisper AI to accurately transcribe and locate unwanted phrases
- **Seamless Removal**: Removes phrases with crossfade transitions to avoid audio pops
- **Automatic Fallback**: If cleanup fails, continues with original audio
- **Detailed Metrics**: Tracks how many phrases were removed per chunk
- **Optional**: Can be disabled via config if not needed

## 📦 Installation

### Quick Install (Recommended)

```powershell
path\to\audiobook-pipeline-styletts-personal\phase5_enhancement\install_integrated.bat
```

This script will:
1. ✅ Install all dependencies (including faster-whisper)
2. ✅ Backup your current files
3. ✅ Activate the integrated version
4. ✅ Test with a single chunk
5. ✅ Show you the results

### Manual Install

If you prefer manual installation:

```powershell
cd path\to\audiobook-pipeline-styletts-personal\phase5_enhancement

# Install dependencies
poetry install

# Backup current files
copy src\phase5_enhancement\main.py src\phase5_enhancement\main.py.backup
copy src\phase5_enhancement\config.yaml src\phase5_enhancement\config.yaml.backup

# Activate integrated version
copy src\phase5_enhancement\main_integrated.py src\phase5_enhancement\main.py
copy src\phase5_enhancement\config_integrated.yaml src\phase5_enhancement\config.yaml
```

## ⚙️ Configuration

### Phrase Cleanup Settings

Edit `config.yaml` to customize phrase cleanup:

```yaml
# Enable/disable phrase cleanup
enable_phrase_cleanup: true

# Phrases to detect and remove
cleanup_target_phrases:
  - "You need to add some text for me to talk"
  - "You need to add some text for me to talk."
  - "You need to add text for me to talk"
  - "You need to add text for me to talk."

# Whisper model size (tiny, base, small, medium, large)
# Larger = more accurate but slower
cleanup_whisper_model: "base"

# Save transcript files for debugging
cleanup_save_transcripts: false
```

### Performance Considerations

| Model Size | Speed | Accuracy | Model Download Size |
|------------|-------|----------|---------------------|
| `tiny` | Fastest | Good | ~40MB |
| `base` | Fast | Better | ~150MB |
| `small` | Medium | Great | ~500MB |
| `medium` | Slow | Excellent | ~1.5GB |
| `large` | Slowest | Best | ~3GB |

**Recommendation**: Use `base` for most cases. It's a good balance of speed and accuracy.

### First Run Note

The first time you run with phrase cleanup enabled, Whisper will download the model (~150MB for `base`). This is a one-time download and takes 1-2 minutes.

## 🚀 Usage

### Process All Chunks

```powershell
# Using the existing batch script (now with phrase cleanup!)
path\to\audiobook-pipeline-styletts-personal\step2_run_phase5.bat
```

### Process Single Chunk (Testing)

```powershell
cd path\to\audiobook-pipeline-styletts-personal\phase5_enhancement
poetry run python -m phase5_enhancement.main --chunk_id 42 --skip_concatenation
```

### Disable Phrase Cleanup

If you want to run without phrase cleanup:

```yaml
# In config.yaml
enable_phrase_cleanup: false
```

Or use the old version:

```powershell
copy src\phase5_enhancement\main.py.backup src\phase5_enhancement\main.py
```

## 📊 Understanding the Output

### Log Messages

```
🧹 Running phrase cleanup on chunk 42...
✓ Removed 1 phrase(s) from chunk 42
Volume normalized chunk 42: RMS 0.1234 → 0.5678
✓ Saved enhanced chunk 42: processed/enhanced_0042.wav
```

### Metrics in pipeline.json

```json
{
  "phase5": {
    "metrics": {
      "phrases_removed_total": 42,
      "chunks_with_phrases": 42,
      "cleanup_errors": 0
    }
  }
}
```

### Chunk-Level Metadata

```json
{
  "chunk_id": 42,
  "cleanup_status": "cleaned",  # or "clean", "disabled", "error"
  "phrases_removed": 1,
  "cleanup_processing_time": 2.3
}
```

## ❓ Troubleshooting

### Issue: "No module named 'faster_whisper'"

**Solution**: Run `poetry install` in the phase5_enhancement directory

```powershell
cd path\to\audiobook-pipeline-styletts-personal\phase5_enhancement
poetry install
```

### Issue: Whisper model download fails

**Solution**: Check your internet connection or manually download:

```python
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
```

### Issue: Processing is slow

**Solutions**:
1. Use a smaller model: `cleanup_whisper_model: "tiny"`
2. Disable cleanup for less critical chunks: `enable_phrase_cleanup: false`
3. Process fewer workers: `max_workers: 1` (in config.yaml)

### Issue: Phrases not being detected

**Solutions**:
1. Check the phrase text matches exactly (case-insensitive)
2. Try a larger model: `cleanup_whisper_model: "small"`
3. Enable transcripts to debug: `cleanup_save_transcripts: true`
   - Check `processed/*_transcript.srt` files

### Issue: Want to rollback to old version

```powershell
copy src\phase5_enhancement\main.py.backup_before_integration src\phase5_enhancement\main.py
copy src\phase5_enhancement\config.yaml.backup_before_integration src\phase5_enhancement\config.yaml
```

## 🔍 Verification Checklist

After installation, verify everything works:

- [ ] Dependencies installed: `poetry install` succeeded
- [ ] Test chunk processed: `enhanced_0000.wav` created
- [ ] No errors in log output
- [ ] Metrics show phrases detected (if present in audio)
- [ ] Pipeline.json updated with phase5 data

## 📈 Performance Impact

**Added per chunk**:
- ~2-3 seconds for transcription (with `base` model)
- ~0.5 seconds for phrase removal (if phrase found)

**Example**: 899 chunks
- Without cleanup: ~45 minutes
- With cleanup: ~90 minutes (doubled time, but worth it for quality!)

## 🎓 Benefits

### Before Integration

1. Phase 4 generates audio with phrases
2. Phase 5 enhances audio (phrases still present)
3. Manual cleanup needed with separate tool
4. Risk of file mismatch between directories

### After Integration

1. Phase 4 generates audio
2. Phase 5 **automatically cleans** then enhances
3. No manual cleanup needed
4. Single source of truth (enhanced chunks)
5. Complete pipeline automation

## 🔗 Integration with Orchestrator

The integrated version works seamlessly with Phase 6 (orchestrator):

```powershell
poetry run python -m phase6_orchestrator --pipeline pipeline.json
```

Phase 6 will automatically:
1. Run Phase 4 (TTS)
2. Run Phase 5 with integrated cleanup ✨ NEW!
3. Pull enhanced chunks for final audiobook

## 📝 Notes

- **Backward Compatible**: Old Phase 5 logic is preserved if you disable cleanup
- **Safe Rollback**: Backups created automatically during installation
- **Production Ready**: Tested with Meditations corpus (899 chunks)
- **Well Logged**: Detailed logging for debugging and monitoring

## 🚦 Next Steps

1. **Install**: Run `install_integrated.bat`
2. **Test**: Process a single chunk to verify
3. **Review**: Check the output and logs
4. **Deploy**: Run full Phase 5 with `step2_run_phase5.bat`
5. **Monitor**: Watch the logs for phrase removal stats

## 📞 Support

If you encounter issues:

1. Check the **Troubleshooting** section above
2. Review logs in `audio_enhancement.log`
3. Check `pipeline.json` for error details
4. Review chunk-level metadata in phase5 results

---

**Last Updated**: October 30, 2025  
**Version**: 2.0 - Integrated Phrase Cleanup  
**Status**: ✅ Production Ready


