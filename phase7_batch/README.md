# Phase 7: Batch Processing

**Status**: Ready for testing  
**Purpose**: Process multiple audiobook files in parallel by calling Phase 6 orchestrator for each file

## Overview

Phase 7 is the **batch processor** that handles multiple PDF/ebook files simultaneously. It:

- Discovers all input files in a directory
- Calls Phase 6 orchestrator subprocess for each file
- Limits parallel workers to prevent CPU overload
- Monitors CPU usage and throttles when necessary
- Supports resume from checkpoints
- Tracks all errors and generates comprehensive reports
- Updates pipeline.json with batch summary

## Architecture

```
Phase 7 (Batch)
    ├─> Discovers all *.pdf/*.epub files in input_dir
    ├─> For each file (in parallel):
    │   └─> Calls Phase 6 orchestrator subprocess
    │       └─> Phase 6 runs phases 1-5 sequentially
    ├─> Monitors CPU usage across all workers
    ├─> Aggregates results into batch summary
    └─> Updates pipeline.json
```

**Key Design Decision**: Phase 7 does NOT call phases directly. It delegates to Phase 6, which maintains all the phase-specific logic (Conda activation, error handling, etc).

## Installation

```bash
cd phase7_batch
poetry install
```

## Configuration

Edit `config.yaml`:

```yaml
# Which phases to run (1-5)
phases_to_run: [1, 2, 3, 4, 5]

# Resume from checkpoints
resume_enabled: true

# Input/output paths
input_dir: ../input
pipeline_json: ../pipeline.json

# Parallel processing
max_workers: 2  # Files processed simultaneously
cpu_threshold: 85  # Throttle if CPU > 85%
throttle_delay: 1.0  # Wait 1s when throttling

# Logging
log_level: INFO
log_file: batch.log
```

### Key Settings

**max_workers**: Number of files to process in parallel
- **Recommended**: 2-4 for typical desktops
- Higher values increase throughput but consume more resources
- Phase 4 (TTS) is CPU-intensive, so don't overdo it

**cpu_threshold**: CPU percentage that triggers throttling
- **Recommended**: 80-90%
- Too low = wasted capacity
- Too high = system becomes unresponsive

**resume_enabled**: Skip files that already completed successfully
- **Recommended**: `true`
- Set to `false` to force reprocessing

## Usage

### Basic Usage

```bash
# Process all files in input directory
poetry run batch-audiobook

# With custom config
poetry run batch-audiobook --config my_config.yaml
```

### Advanced Options

```bash
# Override input directory
poetry run batch-audiobook --input-dir ./my_books

# Run specific phases only
poetry run batch-audiobook --phases 3 4 5

# Disable resume (force fresh processing)
poetry run batch-audiobook --no-resume

# Limit to first N files (testing)
poetry run batch-audiobook --config config.yaml
# Edit config.yaml: batch_size: 5

# Increase workers for faster processing
poetry run batch-audiobook --max-workers 4
```

### Example Workflow

```bash
# 1. Put PDFs in input directory
cp ~/Downloads/*.pdf ../input/

# 2. Run batch processing
poetry run batch-audiobook

# Output:
# ╭─────────────────────────────────────╮
# │     Batch Processing Summary        │
# ├─────────────────┬───────────────────┤
# │ Total Files     │ 10                │
# │ Successful      │ 8                 │
# │ Partial         │ 1                 │
# │ Failed          │ 1                 │
# │ Duration        │ 3245.2s (54.1min) │
# │ Avg CPU         │ 78.3%             │
# │ Status          │ PARTIAL           │
# ╰─────────────────┴───────────────────╯
```

## Output Files

```
phase7_batch/
├── batch.log              # Detailed processing log
├── config.yaml            # Configuration
└── ...

../pipeline.json           # Updated with batch summary
    └── batch:
        ├── summary:       # Overall statistics
        │   ├── total_files
        │   ├── successful_files
        │   ├── failed_files
        │   └── ...
        └── files:         # Per-file metadata
            ├── file1:
            │   ├── status: "success"
            │   ├── duration: 324.5
            │   └── phases_completed: [1,2,3,4,5]
            └── file2: ...
```

## How It Works

### 1. File Discovery

```python
input_files = list(Path(input_dir).glob("*.pdf"))
input_files += list(Path(input_dir).glob("*.epub"))
```

Finds all PDFs and EPUBs in the input directory.

### 2. Parallel Processing

```python
async with trio.open_nursery() as nursery:
    for file_path in input_files:
        nursery.start_soon(process_single_file, file_path, config, semaphore)
```

Uses Trio for async concurrency with a semaphore to limit parallel workers.

### 3. Phase 6 Subprocess Call

```python
cmd = [
    sys.executable,
    str(orchestrator_path),
    str(file_path),
    f"--pipeline-json={config.pipeline_json}",
    f"--phases",
] + [str(p) for p in config.phases_to_run]

process = await trio.run_process(cmd, ...)
```

Each file spawns a Phase 6 orchestrator subprocess that handles all phase execution.

### 4. CPU Monitoring

```python
async def monitor_cpu_usage(...):
    while not stop_event.is_set():
        cpu = psutil.cpu_percent(interval=0.1)
        if cpu > config.cpu_threshold:
            await trio.sleep(config.throttle_delay)
```

Background task monitors CPU and adds delays when threshold exceeded.

### 5. Result Aggregation

```python
summary = BatchSummary.from_metadata_list(
    metadata_list,
    total_duration,
    avg_cpu
)
update_pipeline_json(config, summary, metadata_list)
```

After all files complete, aggregates results and updates pipeline.json.

## Resume Functionality

When `resume_enabled: true`:

1. Before processing each file, checks pipeline.json
2. If all required phases show `status: "success"` for that file
3. Skips the file and logs `[SKIP] file_id already completed`
4. This allows restarting failed batches without reprocessing successful files

Example:
```bash
# Initial run - processes 10 files, 2 fail
poetry run batch-audiobook
# Output: 8 success, 2 failed

# Fix issues, run again - only processes the 2 failed files
poetry run batch-audiobook
# Output: [SKIP] file1... [SKIP] file2... [START] file9... [START] file10...
```

## Error Handling

### File-Level Errors

If a file fails:
- Error logged to `batch.log`
- Metadata marked as `failed` or `partial`
- Processing continues with other files
- Summary shows which files failed

### Phase-Level Errors

Phase errors are handled by Phase 6 orchestrator:
- Phase 6 has retry logic (up to 2 retries per phase)
- Phase 6 logs actionable error messages
- If a phase fails, Phase 6 aborts that file
- Phase 7 receives exit code and marks file accordingly

### Critical Errors

If Phase 7 encounters a critical error:
- Python exceptions logged with traceback
- Exit code 1 returned
- Partial results saved to pipeline.json

## Monitoring

### During Execution

```
[2025-10-15 14:23:10] [INFO] Found 5 files to process
[2025-10-15 14:23:11] [START] book1
[2025-10-15 14:23:11] [START] book2
[2025-10-15 14:28:45] [SUCCESS] book1 in 334.2s
[2025-10-15 14:28:50] [START] book3
[2025-10-15 14:30:15] [WARNING] CPU 89.3% > 85%; throttling for 1.0s
[2025-10-15 14:32:20] [FAIL] book2: Orchestrator failed with exit code 1
[2025-10-15 14:32:20] [START] book4
...
```

### Rich Progress Bar

```
Processing files... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 60% (3/5) 0:05:23
```

### Final Summary

Rich tables show:
- Overall statistics (total, success, fail, duration, CPU)
- Per-file details (file ID, status, duration, error)
- Error list (first 10 errors if any)

## Troubleshooting

### Issue: "Orchestrator not found"

**Cause**: Phase 6 orchestrator script not found

**Fix**:
```bash
# Check Phase 6 exists
ls ../phase6_orchestrator/orchestrator.py

# If missing, create Phase 6 first
cd ../phase6_orchestrator
poetry install
```

### Issue: High CPU usage, system unresponsive

**Cause**: Too many workers or CPU threshold too high

**Fix**:
```yaml
# In config.yaml
max_workers: 1  # Reduce workers
cpu_threshold: 70  # Lower threshold
```

### Issue: Files not being skipped on resume

**Cause**: Resume not detecting completed files

**Fix**:
```bash
# Check pipeline.json structure
python -c "import json; print(json.load(open('../pipeline.json'))['phase5']['status'])"

# If phase5 status is not "success", file will reprocess
# This is expected behavior
```

### Issue: All files fail immediately

**Cause**: Phase 6 orchestrator failing to execute

**Fix**:
```bash
# Test Phase 6 directly
cd ../phase6_orchestrator
poetry run python orchestrator.py ../input/test.pdf

# Check error message
# Likely Conda environment or dependency issue
```

### Issue: Some files get "partial" status

**Cause**: Some phases succeeded, others failed

**Analysis**:
```bash
# Check which phases failed
grep "FAIL" batch.log | grep "file_id"

# Check pipeline.json for details
python -c "
import json
data = json.load(open('../pipeline.json'))
for phase in [1,2,3,4,5]:
    print(f'Phase {phase}:', data.get(f'phase{phase}', {}).get('status'))
"
```

## Performance Tips

### Optimize Worker Count

Test different worker counts to find sweet spot:

```bash
# 1 worker - slowest but most stable
poetry run batch-audiobook --max-workers 1

# 2 workers - good balance (recommended)
poetry run batch-audiobook --max-workers 2

# 4 workers - faster but may cause issues
poetry run batch-audiobook --max-workers 4
```

Monitor CPU usage. If consistently < 80%, increase workers. If > 95%, decrease.

### Batch Processing Strategy

For large batches (>10 files):

1. **Test run**: Process 2-3 files first
   ```bash
   # Edit config.yaml: batch_size: 3
   poetry run batch-audiobook
   ```

2. **Verify quality**: Check output audiobooks

3. **Full batch**: Remove batch_size limit
   ```bash
   # Edit config.yaml: batch_size: null
   poetry run batch-audiobook
   ```

4. **Resume failures**: Fix issues, rerun
   ```bash
   poetry run batch-audiobook  # Only processes failed files
   ```

### Phase Selection

Skip phases you don't need:

```bash
# Already validated files? Skip Phase 1
poetry run batch-audiobook --phases 2 3 4 5

# Just want to regenerate audio? Skip 1-3
poetry run batch-audiobook --phases 4 5
```

## Integration with Phase 6

Phase 7 treats Phase 6 as a black box:

```
Phase 7 Responsibilities:
- File discovery
- Parallel execution
- CPU monitoring
- Result aggregation

Phase 6 Responsibilities:
- Sequential phase execution
- Conda activation (Phase 4)
- Error handling & retries
- Progress reporting
- Checkpoint management
```

This separation means:
- Phase 6 can be improved independently
- Phase 7 doesn't need to know about Conda, venvs, etc.
- Testing is simpler (test Phase 6 alone, then Phase 7 alone)

## Testing

Run tests:

```bash
poetry run pytest tests/ -v --cov
```

Test structure:
```
tests/
└── test_cli.py
    ├── test_config_loading
    ├── test_file_discovery
    ├── test_orchestrator_finding
    ├── test_metadata_tracking
    ├── test_resume_functionality
    └── test_summary_generation
```

## Limitations

1. **No cross-file optimization**: Each file processed independently
2. **Shared pipeline.json**: All files update same JSON (potential race conditions, but unlikely with subprocess isolation)
3. **No distributed processing**: All workers on same machine
4. **Fixed phase order**: Cannot reorder phases per file

## Future Improvements

- [ ] Add `--dry-run` flag to preview what will be processed
- [ ] Add `--file-pattern` to filter input files (e.g., `*.pdf` only)
- [ ] Add email notifications on completion
- [ ] Add Prometheus metrics export for monitoring
- [ ] Add database backend (SQLite) for large batches
- [ ] Add distributed processing (Celery/RQ)
- [ ] Add web UI for monitoring progress

## FAQ

**Q: Can I process files from multiple directories?**  
A: Not directly. Either:
- Copy all files to one directory
- Run Phase 7 multiple times with different `--input-dir`

**Q: What if I interrupt with Ctrl+C?**  
A: Graceful shutdown. Running files may complete or fail, but no corruption. Restart with resume enabled.

**Q: Can I run multiple Phase 7 instances?**  
A: Not recommended. They share pipeline.json and may conflict. Use `max_workers` instead.

**Q: How long does batch processing take?**  
A: Varies greatly:
- Small book (50 pages): ~3-5 minutes
- Medium book (200 pages): ~10-20 minutes  
- Large book (500 pages): ~30-60 minutes
- With 2 workers: ~Half the time

**Q: Does it work on Windows/Mac/Linux?**  
A: Yes. Trio and subprocess are cross-platform. Tested on Windows 11.

## Support

If you encounter issues:

1. Check `batch.log` for detailed errors
2. Test Phase 6 individually on a problem file
3. Verify Phase 4 Conda environment exists
4. Check available disk space and memory
5. Try reducing `max_workers` to 1

## License

Same as main project.
