# CRITICAL: Disk Space and Memory Issues

**Date**: 2025-11-29
**Status**: 🔴 **CRITICAL - Immediate Action Required**

---

## Current Status

### Disk Space: 🔴 CRITICAL (5.6% Free)
```
Total: 463 GB
Used:  437 GB
Free:  26 GB (5.6%)
Status: 95% FULL - CRITICAL!
```

### Memory Usage: ⚠️ HIGH (80%+)
Recent Phase 5 runs show memory usage at **80.7% - 81.9%**

---

## Impact on Pipeline

### Phase 5 Failures
- **94.2% failure rate** for Phase 5
- Errors: Generic "Phase 5 failed" without details
- **Root Cause**: Likely out of disk space during audio processing

### Why Phase 5 is Affected
1. **Audio Processing**: Phase 5 enhancement creates temporary files
2. **Compression**: May need space for both input and output during processing
3. **Metadata**: Additional files for timing, subtitles, etc.

---

## Pipeline Directory Sizes

```
phase5_enhancement/processed: 16.05 GB  ← Processed audiobooks
phase4_tts/audio_chunks:       0.00 GB  (currently empty)
input:                         0.46 GB  (PDF files)
phase3-chunking/chunks:        0.00 GB  (text chunks)
phase2-extraction:             0.01 GB  (extracted text)
```

---

## Immediate Actions Required

### 1. Free Up Disk Space (URGENT)

**Move Processed Audiobooks to External Storage**:
```bash
# Create external backup location
mkdir /path/to/external/drive/audiobooks

# Move processed files
mv phase5_enhancement/processed/* /path/to/external/drive/audiobooks/

# Or compress and move
cd phase5_enhancement/processed
for book in */; do
    tar -czf "${book%/}.tar.gz" "$book"
    mv "${book%/}.tar.gz" /path/to/external/drive/audiobooks/
    rm -rf "$book"
done
```

**Clean Old Logs**:
```bash
# Find and remove old policy logs
find .pipeline/policy_logs -name "*.log" -mtime +30 -delete

# Compress old logs instead
find .pipeline/policy_logs -name "*.log" -mtime +7 -exec gzip {} \;
```

**Clean Python Cache**:
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
```

### 2. Check for Large Files

**Find largest files**:
```bash
# Windows (PowerShell)
Get-ChildItem -Recurse | Sort-Object Length -Descending | Select-Object -First 20 Name,@{N='Size(GB)';E={$_.Length/1GB}}

# Git Bash / WSL
find . -type f -exec du -h {} + 2>/dev/null | sort -rh | head -20
```

### 3. Configure Pipeline for Low Disk Space

**Option A: Process in Batches**
- Process one book at a time
- Move to external storage immediately after completion
- Delete intermediate files

**Option B: Use External Storage for Output**
```yaml
# In phase5_enhancement/config.yaml
output_dir: "E:/audiobooks/processed"  # External drive
temp_dir: "E:/audiobooks/temp"
```

---

## Recommended Disk Space

### Minimum Requirements
- **Phase 4** (TTS): ~500 MB per hour of audio
- **Phase 5** (Enhancement): ~1 GB per hour (needs temp space)
- **Recommended Free**: At least **20% of drive** (~90 GB)

### Per-Book Estimates
| Book Length | Phase 4 (Raw) | Phase 5 (Enhanced) | Total Needed |
|-------------|---------------|-------------------|--------------|
| 1 hour      | 500 MB        | 1 GB              | 1.5 GB       |
| 10 hours    | 5 GB          | 10 GB             | 15 GB        |
| 50 hours    | 25 GB         | 50 GB             | 75 GB        |
| 100 hours   | 50 GB         | 100 GB            | 150 GB       |

**"Systematic Theology"** is likely a large book requiring significant space!

---

## Long-Term Solutions

### 1. Automated Cleanup Script

Create `cleanup_old_files.py`:
```python
#!/usr/bin/env python3
"""Automatically clean old processed files."""

from pathlib import Path
import shutil
import time

# Move files older than 7 days
THRESHOLD_DAYS = 7
PROCESSED_DIR = Path("phase5_enhancement/processed")
ARCHIVE_DIR = Path("E:/audiobook_archive")  # External drive

for book_dir in PROCESSED_DIR.iterdir():
    if book_dir.is_dir():
        age_days = (time.time() - book_dir.stat().st_mtime) / 86400
        if age_days > THRESHOLD_DAYS:
            print(f"Archiving: {book_dir.name} (age: {age_days:.1f} days)")
            shutil.move(str(book_dir), str(ARCHIVE_DIR / book_dir.name))
```

### 2. Configure Windows Disk Cleanup

Enable automatic cleanup of:
- Temporary files
- Recycle Bin
- Download folder
- Windows Update cleanup

### 3. Monitor Disk Space

Add to orchestrator to check before starting:
```python
def check_disk_space(required_gb=20):
    """Fail early if disk space too low."""
    total, used, free = shutil.disk_usage("C:/")
    free_gb = free // (2**30)
    if free_gb < required_gb:
        raise RuntimeError(
            f"Insufficient disk space: {free_gb} GB free, need {required_gb} GB"
        )
```

---

## Troubleshooting Phase 5

### Check Actual Error

Phase 5 logs show generic "Phase 5 failed" - need detailed error:

```bash
# Check Phase 5 logs
cd phase5_enhancement
grep -i "error\|exception\|failed" .venv/Lib/site-packages/*/logs/*.log 2>/dev/null

# Run Phase 5 directly with verbose logging
cd phase5_enhancement
poetry run python -m phase5_enhancement.main \
    --file_id "Systematic Theology" \
    --json_path ../pipeline.json \
    --verbose
```

### Common Phase 5 Disk Issues

1. **Out of Space**: Enhancement fails midway
2. **Temp File Buildup**: Intermediate files not cleaned
3. **Permission Errors**: Can't write to output directory

---

## Immediate Next Steps

1. **Free 50+ GB disk space** by moving processed audiobooks to external storage
2. **Rerun Phase 5** for "Systematic Theology" with more disk space available
3. **Monitor disk usage** during the run
4. **Configure external storage** for future large books

---

## Summary

- 🔴 **Disk**: 95% full (26 GB free) - **CRITICAL**
- ⚠️ **Memory**: 80%+ usage - **HIGH**
- 📊 **Phase 5**: 94.2% failure rate due to resource constraints
- 🎯 **Action**: Free up 50+ GB immediately

**The pipeline cannot run reliably with only 5.6% disk space free!**
