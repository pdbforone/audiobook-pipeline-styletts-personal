# Phase 7 Quick Start Guide

Get Phase 7 batch processing running in 5 minutes.

## Prerequisites

✅ Phase 6 orchestrator working (tested with at least one file)  
✅ Python 3.12  
✅ Poetry installed  
✅ Conda environment for Phase 4 (if running TTS)

## Installation

```bash
# Navigate to Phase 7
cd phase7_batch

# Install dependencies
poetry install

# Verify installation
poetry run python verify_install.py
```

Expected output:
```
============================================================
Phase 7 Batch Processing - Installation Check
============================================================
Checking imports...
  ✓ All dependencies available

Checking Phase 6 orchestrator...
  ✓ Found: C:\...\phase6_orchestrator\orchestrator.py

Checking configuration...
  ✓ Config valid
    - Input dir: ../input
    - Max workers: 2
    - Phases: [1, 2, 3, 4, 5]

Checking input directory...
  ✓ Input directory: C:\...\input
    - PDFs: 3
    - EPUBs: 0
    - Total: 3

============================================================
✓ All checks passed!

Ready to run:
  poetry run batch-audiobook
```

## Basic Usage

### 1. Add Your Files

```bash
# Copy PDFs to input directory
cp ~/Documents/*.pdf ../input/
```

### 2. Run Batch Processing

```bash
# Process all files with default settings
poetry run batch-audiobook
```

You'll see:
```
╭─────────────────────────────────────────────╮
│            Configuration                    │
├─────────────────────────────────────────────┤
│ Input Dir:     ..\input                     │
│ Files:         3                            │
│ Pipeline JSON: ..\pipeline.json             │
│ Max Workers:   2                            │
│ CPU Threshold: 85%                          │
│ Resume:        Enabled                      │
│ Phases:        1 → 2 → 3 → 4 → 5            │
╰─────────────────────────────────────────────╯

Processing files... ━━━━━━━━━━━━━ 100% (3/3) 0:15:23
```

### 3. Check Results

After completion:
```
╭─────────────────────────────────────────╮
│    Batch Processing Summary             │
├───────────────┬─────────────────────────┤
│ Total Files   │ 3                       │
│ Successful    │ 3                       │
│ Partial       │ 0                       │
│ Failed        │ 0                       │
│ Duration      │ 923.5s (15.4min)        │
│ Avg CPU       │ 78.2%                   │
│ Status        │ SUCCESS                 │
╰───────────────┴─────────────────────────╯
```

## Common Tasks

### Process Specific Phases Only

```bash
# Skip validation, only run extraction and chunking
poetry run batch-audiobook --phases 2 3

# Regenerate TTS only
poetry run batch-audiobook --phases 4

# Just enhance audio
poetry run batch-audiobook --phases 5
```

### Adjust Worker Count

```bash
# Slower but more stable (1 file at a time)
poetry run batch-audiobook --max-workers 1

# Faster if you have CPU headroom
poetry run batch-audiobook --max-workers 4
```

### Disable Resume

```bash
# Force reprocess everything
poetry run batch-audiobook --no-resume
```

### Custom Configuration

Create `my_config.yaml`:
```yaml
phases_to_run: [1, 2, 3]  # Skip TTS for testing
resume_enabled: true
input_dir: ./test_books
pipeline_json: ./test_pipeline.json
max_workers: 1
cpu_threshold: 70
log_level: DEBUG
```

Run with it:
```bash
poetry run batch-audiobook --config my_config.yaml
```

## Troubleshooting

### "Orchestrator not found"

Phase 6 isn't set up:
```bash
cd ../phase6_orchestrator
ls orchestrator.py  # Should exist
```

### "No input files found"

Check input directory:
```bash
ls -la ../input/*.pdf
```

### High CPU, system slow

Reduce workers:
```bash
poetry run batch-audiobook --max-workers 1
```

Or edit `config.yaml`:
```yaml
max_workers: 1
cpu_threshold: 70  # Throttle earlier
```

### Files not resuming

Check if phases actually completed:
```bash
# Look for phase5 success
grep -A 5 '"phase5"' ../pipeline.json
```

If status isn't "success", file will reprocess (expected).

### Some files fail

Check `batch.log`:
```bash
grep "FAIL" batch.log
grep "ERROR" batch.log
```

Common causes:
- Corrupt PDFs → Check with Phase 1 directly
- Out of memory → Reduce workers
- Conda environment → Test Phase 4 directly

## Next Steps

Once Phase 7 works:

1. **Scale up**: Increase `max_workers` based on your CPU
2. **Automate**: Add to cron/Task Scheduler for regular processing
3. **Monitor**: Check `batch.log` for issues
4. **Optimize**: Profile bottlenecks with different phase combinations

## Tips

- **Start small**: Test with 2-3 files first
- **Watch resources**: Monitor CPU/RAM in Task Manager
- **Use resume**: Don't disable unless you need fresh processing
- **Check quality**: Listen to samples before processing large batches
- **Keep logs**: `batch.log` is invaluable for debugging

## Example Session

```bash
# 1. Setup
cd phase7_batch
poetry install
poetry run python verify_install.py

# 2. Test run with 2 files
# Edit config.yaml: batch_size: 2
poetry run batch-audiobook

# 3. Check results
ls ../phase5_enhancement/output/*.mp3

# 4. Full batch
# Edit config.yaml: batch_size: null
poetry run batch-audiobook

# 5. Resume after fixing issues
poetry run batch-audiobook  # Skips successful files
```

## Success Criteria

You're ready for production when:

✅ Test run completes successfully  
✅ Output audiobooks sound good  
✅ Resume works (skips completed files)  
✅ Logs are clean (no unexpected errors)  
✅ CPU usage is manageable  

Now you can process your entire book library! 📚🎧
