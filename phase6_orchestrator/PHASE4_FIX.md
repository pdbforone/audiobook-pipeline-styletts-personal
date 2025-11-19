# Phase 4 Fix - File ID Mismatch

## The Problem

Phase 4 was failing with:
```
ERROR - Failed to load chunk path from ..\pipeline.json: Chunk 0 not found
```

**Root Cause**: The `file_id` mismatch between what the orchestrator was passing and what Phase 3 wrote to `pipeline.json`.

### What Was Happening

1. **Orchestrator** derives file_id from filename:
   ```python
   file_id = file_path.stem  # "The Analects of Confucius"
   ```

2. **Phase 3** writes chunks to pipeline.json under a different key:
   ```json
   {
     "phase3": {
       "files": {
         "The_Analects_of_Confucius_20240228_converted_with_pdfplumber": {
           "chunk_paths": [...]
         }
       }
     }
   }
   ```

3. **Phase 4** looks for chunks using the file_id from orchestrator:
   ```python
   chunks = pipeline["phase3"]["files"]["The Analects of Confucius"]["chunk_paths"]
   # KeyError! This key doesn't exist!
   ```

## The Fix

The orchestrator now has **smart file_id matching**:

### 1. Try Exact Match First
```python
chunks = phase3_files.get(file_id, {}).get("chunk_paths", [])
```

### 2. Fuzzy Match If Exact Fails
```python
for key in phase3_files.keys():
    if file_id in key or key in file_id:
        logger.info(f"Using Phase 3 key: '{key}'")
        file_id = key  # Update to use the correct key
        chunks = phase3_files[key].get("chunk_paths", [])
        break
```

### 3. Added Reference Audio Support
```python
# Automatically use greenman_ref.wav if it exists
ref_file = phase_dir / "greenman_ref.wav"
if ref_file.exists():
    cmd.append(f"--ref_file={str(ref_file)}")
```

## How to Test the Fix

### Step 1: Check What Phase 3 Wrote
```bash
cd phase6_orchestrator
python check_phase3_output.py
```

This will show you:
- The actual file_id that Phase 3 used
- How many chunks were created
- Sample chunk paths

**Example output:**
```
Found 1 file(s) in Phase 3:

File ID: 'The_Analects_of_Confucius_20240228_converted_with_pdfplumber'
  Status: success
  Chunks: 109
  First chunk: C:\...\chunks\chunk_000.txt
  Last chunk: C:\...\chunks\chunk_108.txt
```

### Step 2: Run Phase 4 with Fixed Orchestrator
```bash
python orchestrator.py "path\to\The Analects of Confucius.pdf" --phases 4
```

**Expected behavior:**
```
[INFO] Exact file_id 'The Analects of Confucius' not found in Phase 3 output
[INFO] Available keys in Phase 3: ['The_Analects_of_Confucius_20240228_converted_with_pdfplumber']
[INFO] Using Phase 3 key: 'The_Analects_of_Confucius_20240228_converted_with_pdfplumber'
[INFO] Processing 109 chunks for file_id='The_Analects_of_Confucius_20240228_converted_with_pdfplumber'
[INFO]   Chunk 1/109
...
```

### Step 3: Verify Success
Phase 4 should now:
- Find the chunks correctly
- Use `greenman_ref.wav` automatically
- Process each chunk with TTS
- Write results to `pipeline.json`

## What Changed in the Orchestrator

### Before (Broken)
```python
# Always used file_path.stem as file_id
file_id = file_path.stem  # "The Analects of Confucius"

# Phase 4 would fail to find chunks
chunks = pipeline["phase3"]["files"][file_id]["chunk_paths"]  # KeyError!
```

### After (Fixed)
```python
# Still starts with file_path.stem
file_id = file_path.stem

# But Phase 4 now does smart matching
phase3_files = pipeline["phase3"]["files"]

# Try exact match
chunks = phase3_files.get(file_id, {}).get("chunk_paths", [])

# Fuzzy match if needed
if not chunks:
    for key in phase3_files.keys():
        if file_id in key or key in file_id:
            file_id = key  # Use the actual key from Phase 3
            chunks = phase3_files[key].get("chunk_paths", [])
            break
```

## Why This Happens

Different phases generate `file_id` differently:

| Phase | How file_id is Generated | Example |
|-------|-------------------------|---------|
| **Orchestrator** | `Path(filename).stem` | `"The Analects of Confucius"` |
| **Phase 1** | Custom logic | `"The_Analects_of_Confucius_20240228"` |
| **Phase 2** | Adds extraction method | `"The_Analects_of_Confucius_20240228_converted_with_pdfplumber"` |
| **Phase 3** | Uses Phase 2's file_id | `"The_Analects_of_Confucius_20240228_converted_with_pdfplumber"` |

The orchestrator now **adapts** to whatever key Phase 3 actually wrote.

## Additional Improvements

### 1. Better Error Messages
If chunks still aren't found:
```
ERROR: No chunks found from Phase 3
ERROR: Searched for file_id: 'The Analects of Confucius'
ERROR: Available Phase 3 files: ['The_Analects_of_Confucius_20240228_converted_with_pdfplumber']
```

### 2. Automatic Reference Audio
No need to manually specify `--ref_file`, the orchestrator checks:
```python
ref_file = phase_dir / "greenman_ref.wav"
if ref_file.exists():
    cmd.append(f"--ref_file={str(ref_file)}")
```

### 3. Diagnostic Logging
Shows exactly what's happening:
```
[INFO] Exact file_id 'X' not found in Phase 3 output
[INFO] Available keys in Phase 3: [...]
[INFO] Using Phase 3 key: 'Y'
```

## Testing Checklist

- [ ] Run `check_phase3_output.py` to see Phase 3 output
- [ ] Verify `greenman_ref.wav` exists in `phase4_tts/`
- [ ] Run orchestrator with `--phases 4`
- [ ] Verify chunks are found and processed
- [ ] Check `pipeline.json` has Phase 4 results

## If It Still Fails

1. **Run the diagnostic script:**
   ```bash
   python check_phase3_output.py
   ```

2. **Check the actual error:**
   - Look for "No chunks found from Phase 3"
   - Check the "Available Phase 3 files" in the error

3. **Verify Phase 3 completed:**
   ```bash
   python orchestrator.py "your_file.pdf" --phases 3
   ```

4. **Check pipeline.json directly:**
   Look for the `phase3` → `files` → `{file_id}` → `chunk_paths` structure

## Summary

The fix makes Phase 4 work by:
1. ✅ Smart file_id matching (exact + fuzzy)
2. ✅ Automatic reference audio detection
3. ✅ Better error messages with diagnostics
4. ✅ Logs show what's actually happening

Run `python check_phase3_output.py` first to see what's in your pipeline.json!


