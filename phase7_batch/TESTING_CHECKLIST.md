# Phase 7 Testing Checklist

Use this checklist to verify Phase 7 is working correctly.

## Pre-Testing Setup

- [ ] Phase 6 orchestrator works (tested with at least one file successfully)
- [ ] Python 3.12 installed
- [ ] Poetry installed and in PATH
- [ ] Conda environment `phase4_tts` exists and works
- [ ] At least 2-3 test PDFs available

## Installation Testing

```bash
cd phase7_batch
```

### 1. Install Dependencies
- [ ] Run: `poetry install`
- [ ] No errors during installation
- [ ] Virtual environment created in `.venv/`

### 2. Run Verification Script
- [ ] Run: `poetry run python verify_install.py`
- [ ] All checks pass (✓)
- [ ] Phase 6 orchestrator found
- [ ] Config is valid
- [ ] Input directory exists

### 3. Check Configuration
- [ ] Open `config.yaml`
- [ ] Verify `input_dir` path is correct
- [ ] Verify `pipeline_json` path is correct
- [ ] `max_workers: 2` (reasonable default)
- [ ] `phases_to_run: [1, 2, 3, 4, 5]` (all phases)

## Functional Testing

### Test 1: Basic Batch Processing

**Setup:**
```bash
# Copy 2 test PDFs to input directory
cp path/to/test1.pdf ../input/
cp path/to/test2.pdf ../input/
```

**Execute:**
```bash
poetry run batch-audiobook
```

**Verify:**
- [ ] Configuration panel displays correctly
- [ ] Shows "Files: 2"
- [ ] Progress bar appears and updates
- [ ] CPU monitoring shows percentage
- [ ] Both files process (or show errors)
- [ ] Summary table displays at end
- [ ] Exit code 0 (success) or 2 (partial)

**Expected Duration:** 5-10 minutes per file (depending on size)

### Test 2: Resume Functionality

**Execute:**
```bash
# Run again with same files
poetry run batch-audiobook
```

**Verify:**
- [ ] Logs show `[SKIP] file1` for completed files
- [ ] No actual processing happens for completed files
- [ ] Completes in seconds (not minutes)
- [ ] Summary shows correct counts

### Test 3: Phase Selection

**Execute:**
```bash
# Run only phases 4 and 5
poetry run batch-audiobook --phases 4 5
```

**Verify:**
- [ ] Only specified phases run
- [ ] Skips phases 1-3
- [ ] Completes faster
- [ ] Output still generated

### Test 4: Worker Count

**Execute:**
```bash
# Single worker
poetry run batch-audiobook --max-workers 1 --no-resume
```

**Verify:**
- [ ] Files process sequentially (one at a time)
- [ ] Lower CPU usage
- [ ] Takes longer overall
- [ ] No errors

### Test 5: Error Handling

**Setup:**
```bash
# Add a corrupt PDF
echo "not a pdf" > ../input/corrupt.pdf
```

**Execute:**
```bash
poetry run batch-audiobook --no-resume
```

**Verify:**
- [ ] Corrupt file fails gracefully
- [ ] Other files still process
- [ ] Error logged in `batch.log`
- [ ] Summary shows 1 failed file
- [ ] Exit code 1 or 2

**Cleanup:**
```bash
rm ../input/corrupt.pdf
```

## Output Verification

After successful batch processing:

### Check Pipeline JSON
```bash
# View batch section
python -c "import json; print(json.dumps(json.load(open('../pipeline.json'))['batch'], indent=2))"
```

**Verify:**
- [ ] `batch` section exists
- [ ] `summary` has correct counts
- [ ] `files` contains each processed file
- [ ] Each file has `status`, `duration`, `phases_completed`

### Check Output Files
```bash
# List generated audiobooks
ls ../phase5_enhancement/output/*.mp3
```

**Verify:**
- [ ] One MP3 per successfully processed file
- [ ] Files have reasonable size (not empty)
- [ ] Can play in media player
- [ ] Audio quality sounds good

### Check Logs
```bash
# View batch log
tail -50 batch.log
```

**Verify:**
- [ ] No unexpected errors
- [ ] Log shows processing flow
- [ ] Timestamps are reasonable
- [ ] Any warnings are explained

## Performance Testing

### Test 1: CPU Throttling

**Setup:**
```yaml
# Edit config.yaml
cpu_threshold: 50  # Very low threshold
```

**Execute:**
```bash
poetry run batch-audiobook --no-resume
```

**Verify:**
- [ ] Log shows throttling messages
- [ ] CPU stays below threshold (roughly)
- [ ] Processing still completes

**Cleanup:**
```yaml
# Reset config.yaml
cpu_threshold: 85
```

### Test 2: Multiple Workers

**Execute:**
```bash
# 4 workers (if you have CPU headroom)
poetry run batch-audiobook --max-workers 4 --no-resume
```

**Verify:**
- [ ] Multiple files process simultaneously
- [ ] CPU usage increases
- [ ] Faster completion
- [ ] System remains responsive
- [ ] No errors or crashes

## Edge Cases

### Test 1: Empty Input Directory

**Setup:**
```bash
# Temporarily rename input files
mv ../input/*.pdf ../input_backup/
```

**Execute:**
```bash
poetry run batch-audiobook
```

**Verify:**
- [ ] Error message: "No input files found"
- [ ] Exits gracefully
- [ ] No crash

**Cleanup:**
```bash
mv ../input_backup/*.pdf ../input/
```

### Test 2: Invalid Config

**Setup:**
```yaml
# Create bad_config.yaml
invalid yaml content [
```

**Execute:**
```bash
poetry run batch-audiobook --config bad_config.yaml
```

**Verify:**
- [ ] Falls back to defaults
- [ ] Warning logged
- [ ] Still runs

**Cleanup:**
```bash
rm bad_config.yaml
```

### Test 3: Phase 6 Not Found

**Setup:**
```bash
# Temporarily rename Phase 6
mv ../phase6_orchestrator ../phase6_backup
```

**Execute:**
```bash
poetry run batch-audiobook
```

**Verify:**
- [ ] Error: "Orchestrator not found"
- [ ] All files fail
- [ ] Actionable error message
- [ ] Exit code 1

**Cleanup:**
```bash
mv ../phase6_backup ../phase6_orchestrator
```

## Integration Testing

### Test 1: Full Pipeline (All Phases)

**Setup:**
- [ ] Fresh PDF (not in pipeline.json)
- [ ] All phases enabled
- [ ] Resume enabled

**Execute:**
```bash
poetry run batch-audiobook
```

**Verify:**
- [ ] Phase 1: Validation completes
- [ ] Phase 2: Text extraction completes
- [ ] Phase 3: Chunking completes
- [ ] Phase 4: TTS synthesis completes
- [ ] Phase 5: Enhancement completes
- [ ] Final audiobook generated
- [ ] All phases in pipeline.json show "success"

### Test 2: Partial Pipeline (Skip Phases)

**Execute:**
```bash
# Skip validation and extraction
poetry run batch-audiobook --phases 3 4 5
```

**Verify:**
- [ ] Uses existing Phase 2 output
- [ ] Runs phases 3-5 only
- [ ] Faster completion
- [ ] Output still correct

## Stress Testing (Optional)

### Test 1: Large Batch

**Setup:**
```bash
# Add 10+ PDFs to input
```

**Execute:**
```bash
poetry run batch-audiobook
```

**Verify:**
- [ ] All files process (or fail gracefully)
- [ ] System doesn't crash
- [ ] Resume works after restart
- [ ] Memory usage reasonable

### Test 2: Large Files

**Setup:**
```bash
# Add 500+ page PDF
```

**Execute:**
```bash
poetry run batch-audiobook
```

**Verify:**
- [ ] Processes without timeout
- [ ] Memory usage acceptable
- [ ] Output audiobook complete

## Cleanup Testing

### Test 1: Clean Run

```bash
# Remove all output
rm ../phase3-chunking/chunks/*.txt
rm ../phase4_tts/audio_chunks/*.wav
rm ../phase5_enhancement/output/*.mp3
rm batch.log

# Run fresh
poetry run batch-audiobook --no-resume
```

**Verify:**
- [ ] Recreates all output
- [ ] No errors about missing files
- [ ] Complete processing

## Windows-Specific Testing

### Test 1: Batch Script

**Execute:**
```cmd
run_batch.bat
```

**Verify:**
- [ ] Runs verification first
- [ ] Starts batch processing
- [ ] Shows progress
- [ ] Displays summary
- [ ] Pauses at end

### Test 2: Path Handling

**Verify:**
- [ ] Handles paths with spaces
- [ ] Handles backslashes correctly
- [ ] Unicode filenames work

## Final Acceptance Criteria

Phase 7 is production-ready when:

✅ All "Installation Testing" checks pass  
✅ All "Functional Testing" tests succeed  
✅ Output audiobooks sound good  
✅ Resume functionality works  
✅ Error handling is graceful  
✅ Logs are clear and helpful  
✅ Performance is acceptable  
✅ No crashes or data corruption  

## If Tests Fail

### Installation Failures
1. Check Python version: `python --version`
2. Check Poetry version: `poetry --version`
3. Clear Poetry cache: `poetry cache clear --all pypi`
4. Reinstall: `poetry install`

### Runtime Failures
1. Check `batch.log` for details
2. Test Phase 6 individually
3. Verify Conda environment
4. Try `--max-workers 1`
5. Check disk space and memory

### Quality Issues
1. Test Phase 6 with same file
2. Check Phase 4 TTS quality
3. Verify Phase 5 enhancement settings
4. Review chunk coherence in Phase 3

## Next Steps After Passing

1. **Production use**: Process your full library
2. **Monitor**: Watch logs and system resources
3. **Tune**: Adjust `max_workers` and `cpu_threshold`
4. **Automate**: Set up scheduled processing
5. **Document**: Note any library-specific issues

## Testing Completed

- Date tested: ___________
- Tester: ___________
- All tests passed: [ ] Yes [ ] No
- Notes:

---

Ready to test? Start with "Installation Testing" and work your way down. Good luck! 🚀
