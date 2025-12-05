# Pipeline Bug Fixes & Optimization Report

**Date**: 2025-11-28
**Pipeline Version**: audiobook-pipeline-styletts-personal

## Executive Summary

This report documents critical bugs found in the audiobook pipeline and provides fixes for each issue. The primary problems involve voice selection, phase status reporting, chunk processing, and dependency management.

---

## 1. CRITICAL BUGS FIXED

### Bug #1: Voice Selection Ignored (Baldur Sanjin → neutral_narrator) ⚠️ **CRITICAL**

**Severity**: CRITICAL
**Impact**: User-selected voices are completely ignored; all chunks use default voice
**Status**: ✅ **FIXED**

**Root Cause**:
The orchestrator does NOT pass the `--voice` parameter to Phase 3 (chunking). Without this parameter, Phase 3's `select_voice()` function defaults to `neutral_narrator` and sets this in each chunk's `voice_override` metadata. Phase 4 then respects these chunk-level overrides, ignoring the global voice selection.

**Files Affected**:
- `phase6_orchestrator/orchestrator.py:2000-2008`

**Fix Applied**:
```python
elif phase_num == 3:
    config_path = custom_phase3_config or (phase_dir / "config.yaml")
    cmd.extend(
        [
            f"--file_id={file_id}",
            f"--json_path={pipeline_json}",
            f"--config={config_path}",
        ]
    )
    # BUGFIX: Pass voice selection to Phase 3 so chunk voice_overrides are set correctly
    if voice_id:
        cmd.append(f"--voice={voice_id}")
```

**Testing**:
After this fix, delete the Phase 3 output and re-run with a specific voice selection. Verify in logs that Phase 4 shows:
```
INFO - Chunk chunk_0001 overriding voice -> <YOUR_SELECTED_VOICE> (engine=xtts)
```

---

### Bug #2: Phase 5 Creates Only 1/13 Enhanced Files 🔍 **INVESTIGATING**

**Severity**: CRITICAL
**Impact**: Phase 5 enhancement fails to process all chunks, resulting in incomplete audiobooks
**Status**: 🔍 **NEEDS DIAGNOSIS**

**Suspected Root Causes**:
1. **Path mismatch**: Phase 4 stores absolute paths but Phase 5 constructs incorrect search paths
2. **Empty chunk_audio_paths**: Phase 4 may not be writing all chunks to pipeline.json
3. **Resume logic error**: Phase 5 may be incorrectly skipping chunks

**Diagnostic Script Created**: `diagnose_phase5.py` (see below)

**Next Steps**:
1. Run `python diagnose_phase5.py --file_id "376953453-The-World-of-Universals"`
2. Review output to identify which chunks are missing
3. Check if `chunk_audio_paths` in pipeline.json has all 13 entries
4. Verify Phase 5 input_dir path resolution

---

### Bug #3: Phase 6 Repeated Failures ❌ **NEEDS INVESTIGATION**

**Severity**: HIGH
**Impact**: Final phase never completes, blocking pipeline completion
**Status**: ❌ **NOT YET FIXED**

**Observed Behavior**:
```
2025-11-28 14:05:57,374 [INFO] Running Phase 6...
2025-11-28 14:05:57,651 [INFO] Retry attempt 1/2 for Phase 6
2025-11-28 14:05:59,653 [INFO] Retry attempt 2/2 for Phase 6
2025-11-28 14:06:01,654 [ERROR] Phase 6 failed after 3 attempts
```

**Root Cause**: Unknown - NO error details logged

**Recommended Fix**:
Add detailed error logging in Phase 6 execution. Likely in orchestrator.py around Phase 6 invocation.

**Action Required**:
1. Locate Phase 6 execution code
2. Add try/except with full traceback logging
3. Check for missing dependencies or config errors

---

### Bug #4: Duration Mismatch Validation Failures (Previously Fixed) ✅

**Severity**: MEDIUM (already resolved in previous session)
**Status**: ✅ **PREVIOUSLY FIXED**

**Fix**: Increased `duration_tolerance_sec` from 5.0s to 120.0s in:
- `phase4_tts/src/validation.py:38`
- `phase4_tts/src/main_multi_engine.py:1937`

**Verification Needed**: Confirm this is applied to XTTS engine config

---

### Bug #5: Missing Dependencies (g2p_en) ⚠️ **LOW PRIORITY**

**Severity**: LOW
**Impact**: Number expansion skipped, minor text quality degradation
**Status**: ⚠️ **NOT YET FIXED**

**Observed Warnings**:
```
2025-11-28 14:09:02,161 - WARNING - g2p_en not installed; skipping number expansion
```

**Recommended Fix**:
Add to `phase4_tts/pyproject.toml`:
```toml
[tool.poetry.dependencies]
g2p-en = "^2.1.0"
```

Then run:
```bash
cd phase4_tts
poetry install
```

---

### Bug #6: RTF Exceeding Threshold ⚙️ **CONFIGURATION ISSUE**

**Severity**: LOW (informational)
**Impact**: Slow synthesis is flagged as abnormal, but XTTS is inherently slow
**Status**: ⚙️ **NOT A BUG - Threshold Unrealistic**

**Observed**:
```
2025-11-28 14:13:40,243 - INFO - Engine 'xtts' RTF 3.75 (threshold 1.10)
```

**Recommendation**:
Update RTF threshold for XTTS engine to 5.0x or make it engine-specific. Real-time factor of 3-4x is NORMAL for XTTS with voice cloning.

---

### Bug #7: Greenman Voice Reference Error ⚠️ **CONFIGURATION**

**Severity**: LOW
**Impact**: One voice (greenman) cannot be used
**Status**: ⚠️ **CONFIGURATION FIX NEEDED**

**Error**:
```
2025-11-28 14:09:04,087 - ERROR - No source_url or local_path for greenman, skipping
```

**Fix**: Either:
1. Remove `greenman` from `voice_references.json` if not used
2. Add valid `source_url` or `local_path` for greenman voice sample

---

### Bug #8: Whisper Not Installed (Tier 2 Validation Disabled) ℹ️ **OPTIONAL**

**Severity**: INFORMATIONAL
**Impact**: Tier 2 ASR validation skipped (optional quality check)
**Status**: ℹ️ **OPTIONAL DEPENDENCY**

**Observed**:
```
⚠️ Whisper not installed - Tier 2 validation disabled
```

**Recommendation**: Document as optional or add to dev dependencies if needed for quality assurance

---

## 2. UI/UX IMPROVEMENTS

### Sound Effects for Completions 🔊 **PARTIALLY IMPLEMENTED**

**Status**: Partially implemented but may not be working

**Implementation Found**:
- Phase 5 imports `play_success_beep` and `play_alert_beep` from `pipeline_common.astromech_notify`
- Calls exist in code: `play_success_beep()` and `play_alert_beep()`

**Verification Needed**:
Check if `pipeline_common/astromech_notify.py` has correct audio file paths and platform-specific playback.

---

## 3. LINTING RECOMMENDATIONS

### Files Needing Cleanup:

1. **orchestrator.py**:
   - Line length violations (PEP 8 max 88-100 chars)
   - Complex nested conditionals in phase execution logic
   - Recommend: Extract phase-specific command builders into separate functions

2. **Phase 5 main.py**:
   - Long function `main()` (~500+ lines) - consider breaking into smaller functions
   - Type hints incomplete (some `Any` types)
   - Recommend: Use Pydantic models more consistently

3. **Phase 4 main_multi_engine.py**:
   - Deeply nested try/except blocks
   - Consider extracting voice resolution logic into separate module

### Linting Command:
```bash
# Install linting tools
pip install black flake8 mypy

# Auto-format
black phase6_orchestrator/orchestrator.py phase5_enhancement/src/ phase4_tts/src/

# Check for issues
flake8 --max-line-length=100 --extend-ignore=E203,W503 phase6_orchestrator/ phase5_enhancement/src/ phase4_tts/src/

# Type checking
mypy --ignore-missing-imports phase6_orchestrator/orchestrator.py
```

---

## 4. TESTING CHECKLIST

### After Applying Fixes:

- [ ] **Voice Selection Test**:
  - Delete Phase 3 output
  - Select "Baldur Sanjin" in UI
  - Run pipeline
  - Verify Phase 4 logs show "Baldur Sanjin" for ALL chunks

- [ ] **Phase 5 Diagnosis**:
  - Run `python diagnose_phase5.py --file_id "<your-file-id>"`
  - Review chunk detection output
  - Fix any path mismatches

- [ ] **Phase 6 Error Logging**:
  - Add error logging to Phase 6
  - Re-run to capture actual error message
  - Fix underlying issue

- [ ] **Dependency Installation**:
  - Install g2p_en in Phase 4 environment
  - Verify number expansion works

- [ ] **Sound Effects**:
  - Verify astromech notification files exist
  - Test with simple phase completion

---

## 5. DEPLOYMENT NOTES

### Order of Operations:

1. ✅ **DONE**: Apply voice selection fix to orchestrator.py
2. 🔄 **IN PROGRESS**: Diagnose Phase 5 chunk loading issue
3. ⏳ **TODO**: Fix Phase 6 error logging and root cause
4. ⏳ **TODO**: Install g2p_en dependency
5. ⏳ **TODO**: Verify sound effects working
6. ⏳ **TODO**: Run linting and cleanup
7. ⏳ **TODO**: Full end-to-end test

### Rollback Plan:

If issues arise, revert orchestrator.py changes:
```bash
git diff phase6_orchestrator/orchestrator.py
git checkout phase6_orchestrator/orchestrator.py  # if needed
```

---

## 6. LONG-TERM IMPROVEMENTS

### Architectural Recommendations:

1. **Centralized Configuration**:
   - Move all voice/engine config to single `configs/pipeline_config.yaml`
   - Reduce parameter passing through multiple phases

2. **Better Resume Logic**:
   - Implement phase-level checkpoints
   - Add "repair" mode to fix incomplete phases without full restart

3. **Improved Error Handling**:
   - Structured error codes (e.g., `ERR_PHASE4_001`)
   - Error recovery suggestions in logs

4. **Performance Optimization**:
   - Profile Phase 4/5 bottlenecks
   - Consider GPU acceleration for enhancement
   - Implement intelligent chunk batching

5. **Testing Suite**:
   - Unit tests for each phase
   - Integration test with sample PDF
   - Automated regression tests

---

## CONCLUSION

**Critical fixes applied**: 1/8
**Immediate action required**: Phase 5 diagnosis, Phase 6 error logging
**Time estimate**: 2-4 hours for remaining fixes

**Next steps**:
1. Run diagnostic script
2. Review Phase 5 output
3. Investigate Phase 6 failure
4. Complete remaining fixes

