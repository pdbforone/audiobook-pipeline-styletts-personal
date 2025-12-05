# Phase 3 Resume Mode Bug - Voice Overrides Not Updated

**Date**: 2025-11-28
**Status**: 🔴 CRITICAL BUG DISCOVERED
**Impact**: Voice selection fails in resume mode

---

## Problem Summary

When Phase 3 runs in **resume mode**, it preserves the old `chunk_voice_overrides` from pipeline.json even when the user provides a new `--voice` parameter. This means voice selection is ignored on subsequent runs.

---

## Root Cause

**File**: `phase3-chunking/src/phase3_chunking/main.py`
**Lines**: 663-665

When Phase 3 detects existing data and enters resume mode:

```python
chunk_voice_overrides=existing_phase3.get(
    "chunk_voice_overrides", {}
),
```

This loads the old (empty) chunk_voice_overrides and NEVER regenerates them based on the current `--voice` CLI parameter.

Later in the code (lines 918-929), voice selection logic runs:

```python
selected_voice = select_voice(
    profile_name=detected_genre,
    file_id=file_id,
    pipeline_data=pipeline_data,
    cli_override=getattr(config, "voice_override", None),
)
chunk_voice_overrides = {}
if selected_voice:
    for idx, chunk_path_str in enumerate(chunk_paths):
        try:
            cid = derive_chunk_id_from_path(Path(chunk_path_str), idx)
            chunk_voice_overrides[cid] = selected_voice
        except Exception as exc:
            logger.warning(...)
```

**BUT** this code only runs in the **non-resume code path**. In resume mode, the voice selection logic is skipped entirely!

---

## Evidence

### Test Case
```bash
cd phase6_orchestrator
python orchestrator.py input.pdf --voice "Baldur Sanjin" --phases 3
```

### Expected Behavior
```python
# pipeline.json Phase 3 data:
{
  "chunk_voice_overrides": {
    "chunk_0001": "baldur_sanjin",
    "chunk_0002": "baldur_sanjin",
    ...
  }
}
```

### Actual Behavior
```python
# pipeline.json Phase 3 data (resume mode):
{
  "chunk_voice_overrides": {}  # ❌ EMPTY!
}
```

### Verification
```bash
python check_voice_overrides.py
# Output:
# Phase 3 data for 376953453-The-World-of-Universals:
#   status: partial
#   total_chunks: 13
#   chunk_voice_overrides: 0 entries  ❌
#
# NO VOICE OVERRIDES FOUND!
```

---

## Impact on Pipeline

1. **Phase 3**: Validates voice (✅) but doesn't store it in chunk metadata (❌)
2. **Phase 4**: Reads empty chunk_voice_overrides → uses default voice instead of user selection
3. **User Experience**: Voice selection appears broken - all audio uses default voice

---

## Solution

Phase 3 must ALWAYS regenerate `chunk_voice_overrides` when:
- `--voice` CLI parameter is provided, OR
- `pipeline_data['tts_voice']` global override exists, OR
- `pipeline_data['voice_overrides'][file_id]` file-level override exists

Even in resume mode!

### Proposed Fix

**Location**: `phase3-chunking/src/phase3_chunking/main.py` (resume code path)

After loading existing Phase 3 data (line ~665), add:

```python
# Resume mode: load existing data
record = Phase3Result(
    ...
    chunk_voice_overrides=existing_phase3.get("chunk_voice_overrides", {}),
    ...
)

# BUGFIX: Regenerate voice overrides if CLI voice provided (even in resume mode)
cli_voice = getattr(config, "voice_override", None)
if cli_voice or pipeline_data.get("tts_voice") or (
    file_id and pipeline_data.get("voice_overrides", {}).get(file_id)
):
    selected_voice = select_voice(
        profile_name=record.genre or "general",
        file_id=file_id,
        pipeline_data=pipeline_data,
        cli_override=cli_voice,
    )
    if selected_voice:
        chunk_voice_overrides = {}
        for idx, chunk_path_str in enumerate(record.chunk_paths):
            try:
                cid = derive_chunk_id_from_path(Path(chunk_path_str), idx)
                chunk_voice_overrides[cid] = selected_voice
            except Exception as exc:
                logger.warning(
                    "Failed to derive chunk_id for %s: %s", chunk_path_str, exc
                )
        record.chunk_voice_overrides = chunk_voice_overrides
        logger.info(f"Resume mode: Updated voice overrides to '{selected_voice}'")
```

---

## Testing

### Test 1: Fresh Run
```bash
# Reset Phase 3
python -c "import json; data = json.load(open('pipeline.json', 'r', encoding='utf-8')); data['phase3']['files']['test_file']['status'] = 'pending'; json.dump(data, open('pipeline.json', 'w', encoding='utf-8'), indent=2)"

# Run Phase 3 with voice
python orchestrator.py input.pdf --voice "Baldur Sanjin" --phases 3

# Verify
python check_voice_overrides.py
# Expected: 13 entries with "baldur_sanjin"
```

### Test 2: Resume Run
```bash
# Run Phase 3 again with DIFFERENT voice (should update overrides)
python orchestrator.py input.pdf --voice "Claribel Dervla" --phases 3

# Verify
python check_voice_overrides.py
# Expected: 13 entries with "claribel_dervla" (NOT "baldur_sanjin"!)
```

### Test 3: End-to-End
```bash
# Full pipeline with voice selection
python orchestrator.py input.pdf --voice "Baldur Sanjin" --phases 1 2 3 4

# Check Phase 4 audio was generated with correct voice
ls phase4_tts/audio_chunks/test_file/
# Expected: 13 WAV files

# Check Phase 4 logs for voice confirmation
# Expected: "Using voice: Baldur Sanjin" or "speaker=Baldur Sanjin"
```

---

## Related Issues

This bug is related to but distinct from the voice normalization fixes:

1. **Voice Normalization** (FIXED): Ensures "Baldur Sanjin" normalizes to "baldur_sanjin" consistently
2. **Voice Registry Sync** (FIXED): Ensures all 102 voices exist in voices.json
3. **Phase 4 Lookup** (FIXED): Ensures Phase 4 uses normalized keys for voice assets
4. **Phase 3 Resume Bug** (THIS ISSUE): Ensures Phase 3 updates voice overrides in resume mode

---

## Workaround (Until Fixed)

To ensure voice selection works:

1. Delete Phase 3 output before running:
   ```bash
   python -c "import json; data = json.load(open('pipeline.json', 'r', encoding='utf-8')); p3 = data.get('phase3', {}).get('files', {}); [p3.pop(k, None) for k in list(p3.keys())]; json.dump(data, open('pipeline.json', 'w', encoding='utf-8'), indent=2)"
   ```

2. Run pipeline with `--fresh` mode (if implemented):
   ```bash
   python orchestrator.py input.pdf --voice "Baldur Sanjin" --fresh
   ```

3. Manually edit pipeline.json to add voice overrides (NOT recommended for large books)

---

## Summary

- ✅ Phase 3 validation and normalization logic is CORRECT
- ✅ Phase 4 voice lookup logic is CORRECT
- ❌ Phase 3 resume mode does NOT regenerate voice overrides
- 🔴 **This is a critical bug affecting all resume runs**
- 🔴 **Blocks voice selection for large books** (where resume is essential)

**Priority**: CRITICAL - Must fix before production use with large audiobooks.
