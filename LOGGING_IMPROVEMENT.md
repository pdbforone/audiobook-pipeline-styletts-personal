# Real-Time Phase 4 Logging - Improvement Summary

## Problem

Phase 4 subprocess output was not visible in the UI terminal or orchestrator logs. Users could not see:
- "Skipping chunk_XXXX (already exists)" messages
- "Generating chunk_XXXX..." progress
- Real-time RTF (real-time factor) metrics
- Validation feedback

This made it impossible to monitor Phase 4 progress without checking the file system.

## Root Cause

The orchestrator's `run_cmd()` function used `capture_output=True`, which buffered all stdout/stderr and only logged a truncated summary at the end (last 1000 characters).

## Solution

**File Modified:** [phase6_orchestrator/orchestrator.py:2199-2234](phase6_orchestrator/orchestrator.py#L2199-L2234)

**Changes:**
1. Changed `capture_output=True` → `capture_output=False`
2. Added log message showing exact Phase 4 command
3. Removed buffered output logging (no longer needed)
4. Simplified error logging (no stderr to show)

## Before

```
2025-11-28 10:54:55,978 [INFO] Running Phase 4...
2025-11-28 10:54:56,297 [INFO] Phase 4 directory: ...
2025-11-28 10:55:06,592 [INFO] Phase 4 reuse rejected: missing chunks (269/296).
[... 30 minutes of silence ...]
```

User had no idea if Phase 4 was working or stuck.

## After

```
2025-11-28 11:00:00,000 [INFO] Running Phase 4...
2025-11-28 11:00:00,500 [INFO] Phase 4 command: python engine_runner.py --engine=xtts --file_id=... --resume
2025-11-28 11:00:05,000 [INFO] Phase 4 Multi-Engine TTS
2025-11-28 11:00:05,001 [INFO] File ID      : A Realist Conception of Truth
2025-11-28 11:00:05,002 [INFO] Voice        : af_bella
2025-11-28 11:00:05,003 [INFO] Engine (req) : xtts
2025-11-28 11:00:05,004 [INFO] Engine (use) : xtts
2025-11-28 11:00:05,005 [INFO] Language     : en
2025-11-28 11:00:05,006 [INFO] Chunks       : 296
2025-11-28 11:00:05,007 [INFO] Workers      : 1
2025-11-28 11:00:05,100 [INFO] Skipping chunk_0001 (already exists)
2025-11-28 11:00:05,101 [INFO] Generating chunk_0002...
[... real-time progress for each chunk ...]
```

User can see exactly what's happening in real-time.

## Benefits

1. **Transparency**: Users see exactly what Phase 4 is doing
2. **Debugging**: Easier to diagnose issues (stuck chunks, validation failures)
3. **Confidence**: Users know the system is working, not stuck
4. **Resume Verification**: Can see "Skipping chunk_XXXX" messages proving resume works
5. **Progress Tracking**: Real-time chunk count updates

## Impact on Other Phases

This change only affects Phase 4. Other phases (1-3, 5) already have their own logging configured differently.

If similar improvements are needed for other phases, the same approach can be applied:
- Phase 5: [orchestrator.py:3225-3234](phase6_orchestrator/orchestrator.py#L3225-L3234) (also uses `capture_output=True`)

## Testing

To test the new logging:

1. Stop current UI (Ctrl+C)
2. Restart UI: `python ui/app.py`
3. Upload book and run with Resume enabled
4. Watch terminal for real-time Phase 4 logs

Expected output:
- Phase 4 command displayed
- Chunk count summary
- "Skipping chunk_XXXX" for existing chunks (instant)
- "Generating chunk_XXXX" for missing chunks (~8 min each)
- RTF metrics and validation results

## Files Modified

- `phase6_orchestrator/orchestrator.py` - Lines 2199-2234 (run_cmd function)

## Commits

- `a908760` - Enable real-time Phase 4 subprocess logging in orchestrator

---

*Implemented: 2025-11-28*
