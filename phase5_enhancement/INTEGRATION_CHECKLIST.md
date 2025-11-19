# Phase 5 Integration Checklist ✅

Follow these steps in order to integrate phrase cleanup into Phase 5.

## 📋 Pre-Installation Checklist

- [ ] **Verify Phase 4 is complete** - Check that `phase4_tts/audio_chunks/` contains your TTS-generated audio files
- [ ] **Backup your work** - Make a backup of your current `pipeline_magi.json`
- [ ] **Internet connection** - Whisper model will download ~150MB on first run
- [ ] **Disk space** - Ensure you have at least 500MB free space

## 🔧 Installation Steps

### Step 1: Run Installation Script

```powershell
path\to\audiobook-pipeline-styletts-personal\phase5_enhancement\install_integrated.bat
```

**What happens**:
- [ ] Poetry installs dependencies (faster-whisper, etc.)
- [ ] Current files backed up as `*.backup_before_integration`
- [ ] Integrated version activated
- [ ] Test chunk processed
- [ ] Success message displayed

**If errors occur**: Check the troubleshooting section in `INTEGRATED_README.md`

### Step 2: Verify Installation

- [ ] No error messages in console
- [ ] File created: `processed/enhanced_0000.wav`
- [ ] Backups created: `main.py.backup_before_integration`, `config.yaml.backup_before_integration`
- [ ] Log file shows phrase cleanup attempt

## 🧪 Testing Steps

### Step 3: Run Comparison Test

```powershell
path\to\audiobook-pipeline-styletts-personal\phase5_enhancement\test_integration.bat
```

**What to check**:
- [ ] Both test directories created: `test_with_cleanup/` and `test_without_cleanup/`
- [ ] Both files exist: `enhanced_0000.wav` in each directory
- [ ] File sizes are DIFFERENT (cleaned should be smaller if phrase was present)
- [ ] Logs show cleanup status (cleaned, clean, or disabled)

### Step 4: Listen to Results

- [ ] Open `processed/test_with_cleanup/enhanced_0000.wav` - Should NOT have unwanted phrase
- [ ] Open `processed/test_without_cleanup/enhanced_0000.wav` - Should STILL have unwanted phrase (if present)
- [ ] Compare audio quality between both versions
- [ ] Check transcript if created: `test_with_cleanup/chunk_0_transcript.srt`

## 🚀 Production Deployment

### Step 5: Process Full Audiobook

```powershell
path\to\audiobook-pipeline-styletts-personal\step2_run_phase5.bat
```

**Monitor during processing**:
- [ ] Log shows "Initializing phrase cleaner..." at startup
- [ ] Each chunk shows cleanup status (🧹 symbol in logs)
- [ ] No crash or fatal errors
- [ ] Progress continues smoothly

**Expected time**: 
- Small corpus (10 chunks): ~10 minutes
- Medium corpus (100 chunks): ~90 minutes
- Large corpus (899 chunks): ~15 hours

### Step 6: Verify Results

- [ ] Check `processed/` directory contains all enhanced chunks
- [ ] Open `pipeline_magi.json` and verify phase5 section exists
- [ ] Check metrics: `phrases_removed_total`, `chunks_with_phrases`
- [ ] Randomly listen to 5-10 enhanced chunks to verify quality

## 📊 Success Metrics

Your integration is successful if:

- [ ] **Zero failures**: All chunks processed successfully
- [ ] **Phrases removed**: Metrics show non-zero `phrases_removed_total` (if phrases were present)
- [ ] **Audio quality**: Enhanced chunks sound clean and professional
- [ ] **No errors**: `phase5.errors` array is empty in `pipeline_magi.json`
- [ ] **Correct order**: Chunk numbers are sequential and complete

## 🔄 Optional: Integrate with Orchestrator

If you want to run the entire pipeline (Phases 1-5) automatically:

### Step 7: Test Orchestrator

```powershell
cd path\to\audiobook-pipeline-styletts-personal
poetry run python -m phase6_orchestrator --pipeline pipeline_magi.json --phase 5
```

- [ ] Orchestrator runs Phase 5 with integrated cleanup
- [ ] No errors in orchestrator logs
- [ ] Phase 5 results appear in `pipeline_magi.json`

## ⚠️ Troubleshooting Checklist

If something goes wrong:

- [ ] **Check logs**: `audio_enhancement.log` for detailed error messages
- [ ] **Verify dependencies**: Run `poetry install` again
- [ ] **Check disk space**: Ensure enough free space for temporary files
- [ ] **Rollback if needed**: Copy `*.backup_before_integration` files back

### Common Issues:

| Symptom | Action |
|---------|--------|
| Import error for `faster_whisper` | Run: `poetry install` |
| Model download timeout | Check internet, try again |
| Processing very slow | Use smaller model: `cleanup_whisper_model: "tiny"` |
| Phrases not detected | Try larger model: `cleanup_whisper_model: "small"` |
| Need to rollback | Copy backups: `main.py.backup_before_integration` → `main.py` |

## 🎯 Final Verification

Complete this checklist before considering integration done:

- [ ] Installation successful
- [ ] Test chunk processed correctly
- [ ] Comparison test shows cleanup working
- [ ] Full processing completed without errors
- [ ] Audio quality meets expectations
- [ ] Metrics in pipeline.json are correct
- [ ] Documentation read and understood

## 📝 Post-Integration

After successful integration:

- [ ] Update any automation scripts to use new Phase 5
- [ ] Document any custom configuration changes
- [ ] Test with a small corpus before processing large batches
- [ ] Monitor first few batches closely

## 🎉 Completion

When all checkboxes are ticked:

**Congratulations!** Your Phase 5 pipeline now includes automatic phrase cleanup integrated seamlessly into the audio enhancement process. You can now process audiobooks from start to finish without manual intervention!

---

## 📚 Quick Reference

**Documentation**:
- Full guide: `INTEGRATED_README.md`
- Summary: `INTEGRATION_SUMMARY.md`
- This checklist: `INTEGRATION_CHECKLIST.md`

**Scripts**:
- Install: `install_integrated.bat`
- Test: `test_integration.bat`
- Process: `step2_run_phase5.bat`

**Rollback**:
```powershell
copy src\phase5_enhancement\main.py.backup_before_integration src\phase5_enhancement\main.py
copy src\phase5_enhancement\config.yaml.backup_before_integration src\phase5_enhancement\config.yaml
```

---

**Version**: 2.0  
**Date**: October 30, 2025  
**Status**: ✅ Ready for Use


