# Coverage Test Guide

## What These Tests Do

The coverage tests verify that **no text is lost** between phases:

1. **Test 1: Phase 2→3 Text Coverage**
   - Reads the extracted text from Phase 2
   - Concatenates all Phase 3 chunks
   - Compares them to ensure 100% coverage
   - Shows similarity % if not exact match

2. **Test 2: Phase 3→4 Audio Coverage**
   - Counts Phase 3 text chunks
   - Counts Phase 4 audio files
   - Checks that all audio files exist
   - Samples random chunks to verify audio quality

## How to Run

### Option 1: Quick Run (Recommended)
```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline\phase6_orchestrator
run_coverage_tests.bat
```

### Option 2: Manual Run
```bash
# Check structure first
python check_pipeline_structure.py

# Run tests
python tests\test_coverage.py --show-diff
```

### Option 3: Run with specific file
```bash
python tests\test_coverage.py --file-id "The_Analects_of_Confucius_20240228" --show-diff
```

## Expected Output

### ✅ Success Looks Like This:
```
==================================================================
TEST 1: Phase 2 → Phase 3 Text Coverage
==================================================================

📊 Results:
  Original text length: 245,123 chars
  Concatenated chunks: 245,123 chars
  Similarity ratio: 1.0000 (100.00%)
  Number of chunks: 517
  ✅ EXACT MATCH - All text preserved!

==================================================================
TEST 2: Phase 3 → Phase 4 Audio Coverage
==================================================================

📊 Counts:
  Phase 3 text chunks: 517
  Phase 4 audio files: 517
  ✅ MATCH: All chunks have audio
  ✅ All audio files exist

🎵 Validating 104 random audio samples...
  ✅ All sampled audio files have valid content

==================================================================
SUMMARY
==================================================================
Test 1 (Phase 2→3 Text Coverage): ✅ PASS
Test 2 (Phase 3→4 Audio Coverage): ✅ PASS

🎉 ALL TESTS PASSED - No text skipped!
```

### ⚠️ Common Issues

**Issue: "Missing chunk file(s)"**
- Some Phase 3 chunks don't exist on disk
- Check: `C:\Users\myson\Pipeline\audiobook-pipeline\phase3-chunking\chunks\`
- Fix: Re-run Phase 3

**Issue: "Similarity ratio: 0.9875 (98.75%)"**  
- Near match but not exact (usually whitespace)
- Use `--show-diff` to see differences
- Usually acceptable if > 99%

**Issue: "MISMATCH: 12 chunks difference!"**
- Phase 3 and Phase 4 have different counts
- Check pipeline.json Phase 4 status
- Some chunks may have failed in TTS

**Issue: "librosa not available"**
- Audio quality checks will be skipped
- Install: `pip install librosa`
- Not critical - just can't verify audio duration/quality

**Issue: "too short: 0.23s" or "silent: RMS=0.000042"**
- Audio exists but is problematic
- Chunk likely failed TTS but created empty file
- Check the specific chunk's error log

## What To Do If Tests Fail

1. **Check which test failed**:
   - Test 1 failure = Phase 3 chunking issue
   - Test 2 failure = Phase 4 TTS issue

2. **For Test 1 failures**:
   ```bash
   # Re-run Phase 3
   cd ..\phase3-chunking
   python -m phase3_chunking.cli --input ..\input\[your_file].pdf --json_path ..\pipeline.json
   ```

3. **For Test 2 failures**:
   ```bash
   # Check which chunks are missing
   python check_phase4_output.py
   
   # Re-run Phase 4 (with resume)
   cd ..\phase6_orchestrator
   python orchestrator.py ..\input\[your_file].pdf --phases 4 --pipeline-json ..\pipeline.json
   ```

## Files Created

- `check_pipeline_structure.py` - Quick structure check
- `run_coverage_tests.bat` - One-click test runner
- `tests/test_coverage.py` - The actual test suite

## Next Steps After Tests Pass

Once coverage tests pass:
1. ✅ You know no text was skipped
2. ✅ All chunks have audio
3. ✅ Ready to run Phase 5 (enhancement)
4. ✅ Can create final audiobook

Run Phase 5:
```bash
python orchestrator.py ..\input\[your_file].pdf --phases 5 --pipeline-json ..\pipeline.json
```
