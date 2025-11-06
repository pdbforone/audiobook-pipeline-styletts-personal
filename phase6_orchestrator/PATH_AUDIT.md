# Phase 6 Orchestrator Path Audit

## Summary
✅ **ALL PATHS IN ORCHESTRATOR.PY ARE CORRECT**

The issue was a bug in argument parsing where `file_path = args.file.resolve()` was being called AFTER the existence check. This has been fixed.

## Phase-by-Phase Path Verification

### Phase 1: Validation
**Orchestrator Command:**
```bash
poetry run python src/phase1_validation/validation.py --file={file_path} --json_path={pipeline_json}
```

**Actual File Structure:**
```
phase1-validation/
└── src/
    └── phase1_validation/
        └── validation.py  ✓ EXISTS
```

**Arguments Expected:**
- `--file`: Input PDF path ✓
- `--json_path`: Pipeline JSON path ✓

**Status:** ✅ CORRECT

---

### Phase 2: Text Extraction
**Orchestrator Command:**
```bash
poetry run python src/phase2_extraction/extraction.py --file_id={file_id} --json_path={pipeline_json}
```

**Actual File Structure:**
```
phase2-extraction/
└── src/
    └── phase2_extraction/
        └── extraction.py  ✓ EXISTS
```

**Arguments Expected:**
- `--file_id`: File identifier ✓
- `--json_path`: Pipeline JSON path ✓

**Status:** ✅ CORRECT

---

### Phase 3: Chunking
**Orchestrator Command:**
```bash
poetry run python -m phase3_chunking.main --file_id={file_id} --json_path={pipeline_json}
```

**Actual File Structure:**
```
phase3-chunking/
└── src/
    └── phase3_chunking/
        └── main.py  ✓ EXISTS
```

**Arguments Expected:**
- `--file_id`: File identifier ✓
- `--json_path`: Pipeline JSON path ✓

**Note:** Phase 3 uses `-m` (module mode) for relative imports. This is correct.

**Status:** ✅ CORRECT

---

### Phase 4: TTS Synthesis (Special: Conda)
**Orchestrator Command:**
```bash
conda run -n phase4_tts --no-capture-output python src/phase4_tts/main.py \
  --chunk_id={chunk_id} \
  --file_id={file_id} \
  --json_path={pipeline_json} \
  --enable-splitting \
  --ref_file={ref_file}
```

**Actual File Structure:**
```
phase4_tts/
└── src/
    └── phase4_tts/
        └── main.py  ✓ EXISTS
```

**Arguments Expected:**
- `--chunk_id`: Chunk number ✓
- `--file_id`: File identifier ✓
- `--json_path`: Pipeline JSON path ✓
- `--enable-splitting`: Enable NLTK splitting ✓
- `--ref_file`: Reference audio (optional) ✓

**Status:** ✅ CORRECT

---

### Phase 5: Audio Enhancement
**Orchestrator Command:**
```bash
poetry run python src/phase5_enhancement/main.py
```

**Actual File Structure:**
```
phase5_enhancement/
└── src/
    └── phase5_enhancement/
        ├── main.py  ✓ EXISTS
        └── config.yaml  ✓ REQUIRED
```

**Arguments Expected:**
- NONE - reads from `config.yaml` ✓

**Status:** ✅ CORRECT

---

## Bug That Was Fixed

### Original Bug (Line 599-602):
```python
# Validate input file
if not args.file.exists():  # ❌ Checking BEFORE resolving!
    print_status(f"[red]ERROR: File not found: {args.file}[/red]")
    return 1

file_path = args.file.resolve()  # Resolves AFTER check
```

### Fixed Version (Line 599-602):
```python
# Validate input file (resolve path first)
file_path = args.file.resolve()  # ✅ Resolve FIRST
if not file_path.exists():
    print_status(f"[red]ERROR: File not found: {file_path}[/red]")
    return 1
```

**Explanation:** 
- `Path("../input/file.pdf").exists()` can fail on Windows with relative paths
- `Path("../input/file.pdf").resolve().exists()` works because it converts to absolute first

---

## Recommendations

### 1. Test the Fixed Orchestrator
```powershell
cd phase6_orchestrator
python orchestrator.py ../input/The_Analects_of_Confucius_20240228.pdf
```

### 2. If Still Fails, Try Absolute Path
```powershell
python orchestrator.py "C:\Users\myson\Pipeline\audiobook-pipeline\input\The_Analects_of_Confucius_20240228.pdf"
```

### 3. Verify Conda Environment for Phase 4
```powershell
conda env list | findstr phase4_tts
```

If not found, create it:
```powershell
cd ..\phase4_tts
conda env create -f environment.yml
conda activate phase4_tts
pip install git+https://github.com/resemble-ai/chatterbox.git
pip install piper-tts librosa requests torchaudio
```

---

## File Locations Reference

```
C:\Users\myson\Pipeline\audiobook-pipeline\
├── input/
│   └── The_Analects_of_Confucius_20240228.pdf  ✓ EXISTS
├── pipeline.json  ← Single source of truth
├── phase1-validation/
│   └── src/phase1_validation/validation.py
├── phase2-extraction/
│   └── src/phase2_extraction/extraction.py
├── phase3-chunking/
│   └── src/phase3_chunking/main.py
├── phase4_tts/
│   └── src/phase4_tts/main.py
├── phase5_enhancement/
│   ├── src/phase5_enhancement/main.py
│   └── src/phase5_enhancement/config.yaml  ← Required for Phase 5
└── phase6_orchestrator/
    └── orchestrator.py  ← YOU ARE HERE
```

---

## Common Errors & Solutions

### Error: "File not found: C:\...\inpu"
**Cause:** Path being truncated in console output  
**Solution:** Fixed in orchestrator.py (already done)

### Error: "Conda environment 'phase4_tts' not found"
**Cause:** Conda env not created  
**Solution:** Run conda env create -f environment.yml in phase4_tts/

### Error: "Phase X script not found"
**Cause:** Running orchestrator from wrong directory  
**Solution:** Always run from phase6_orchestrator/ directory

### Error: "Phase 3 import errors"
**Cause:** Need to use -m flag for module imports  
**Solution:** Already handled correctly in orchestrator (line 329)

---

## Conclusion

✅ All paths are correct  
✅ Bug has been fixed  
✅ Ready to test end-to-end pipeline

**Next Step:** Run the orchestrator and test!
