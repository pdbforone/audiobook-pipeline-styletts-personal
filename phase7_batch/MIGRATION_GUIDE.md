# Migrating from Old Phase 7 to New Phase 7

This guide helps you transition from the original Phase 7 implementation (in `main.py`) to the new architecture.

## What Changed?

### Old Architecture (main.py)
```
Phase 7
  ├─> Directly calls phases 1-5
  ├─> Handles Poetry/Conda activation itself
  ├─> Manages venv discovery
  ├─> Duplicates Phase 6 logic
  └─> ~600 lines of complex code
```

### New Architecture (cli.py)
```
Phase 7
  ├─> Discovers files
  ├─> Calls Phase 6 orchestrator (subprocess)
  │   └─> Phase 6 handles everything
  ├─> Monitors resources
  └─> ~330 lines of simple code
```

## Why Migrate?

**Problems with Old Approach:**
1. ❌ Duplicated Phase 6 logic (maintenance nightmare)
2. ❌ Complex Conda/Poetry handling in 2 places
3. ❌ Hard to test (Phase 7 needed to know about all phases)
4. ❌ Bug fixes needed in Phase 6 AND Phase 7
5. ❌ Tightly coupled to phase implementation details

**Benefits of New Approach:**
1. ✅ Single source of truth (Phase 6)
2. ✅ Simpler code (delegates complexity)
3. ✅ Easier to maintain (changes stay in Phase 6)
4. ✅ Better separation of concerns
5. ✅ Phase 7 focuses only on batch coordination

## Migration Steps

### Step 1: Backup Old Implementation

```bash
cd phase7_batch

# Backup old files
cp src/phase7_batch/main.py src/phase7_batch/main_old.py
cp src/phase7_batch/mainbu.py src/phase7_batch/mainbu_backup.py
```

### Step 2: Install New Dependencies

The new implementation uses the same dependencies, but let's ensure they're up to date:

```bash
# Reinstall with new pyproject.toml
poetry install
```

### Step 3: Update Configuration

The new `config.yaml` has the same structure but different defaults:

**Old config.yaml:**
```yaml
phases_to_run: [4]  # Often customized
resume_enabled: false  # Manual control
```

**New config.yaml:**
```yaml
phases_to_run: [1, 2, 3, 4, 5]  # All phases by default
resume_enabled: true  # Smart resume
```

**Migration:**
- Keep your customizations
- But enable `resume_enabled: true` (it's smarter now)
- Add `phases_to_run` if you want to skip phases

### Step 4: Test New CLI

The CLI interface is similar:

**Old:**
```bash
poetry run python src/phase7_batch/main.py
```

**New:**
```bash
poetry run batch-audiobook
# Or equivalently:
# poetry run python -m phase7_batch.cli
```

### Step 5: Verify Output

Run a test batch and verify:

```bash
# Test with 1-2 files
poetry run batch-audiobook

# Check same outputs exist:
ls ../phase5_enhancement/output/*.mp3
```

### Step 6: Remove Old Files (Optional)

Once you're confident the new version works:

```bash
# Remove old implementations
rm src/phase7_batch/main_old.py
rm src/phase7_batch/mainbu.py
rm src/phase7_batch/mainbu1.py
rm src/phase7_batch/mainbu_backup.py
```

## API Changes

### Configuration

**Old:** Custom dictionary-based config
```python
class BatchConfig:
    def __init__(self, **data):
        self.log_level = data.get("log_level", "INFO")
        # Manual validation...
```

**New:** Pydantic models with validation
```python
class BatchConfig(BaseModel):
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|...)$")
    # Automatic validation
```

**Migration:** No code changes needed if using config.yaml

### Phase Execution

**Old:** Direct phase execution
```python
def run_phase_for_file(phase, file_path, file_id, config, metadata):
    phase_dir = find_phase_directory(phase)
    venv_python, env_identifier = get_venv_python(phase_dir)
    main_script = find_phase_main(phase_dir, phase)
    # Complex subprocess logic...
    _run_subprocess(venv_python, env_identifier, main_script, args, ...)
```

**New:** Delegate to Phase 6
```python
async def process_single_file(file_path, config, semaphore):
    orchestrator = find_orchestrator()
    cmd = [sys.executable, str(orchestrator), str(file_path), ...]
    process = await trio.run_process(cmd, ...)
```

**Migration:** No migration needed - completely different internal implementation

### Resume Logic

**Old:** Manual resume checks
```python
if config.resume_enabled:
    try:
        with open(config.pipeline_json, "r") as f:
            pipeline = json.load(f)
        existing = pipeline.get("batch", {}).get("files", {}).get(file_id, {})
        metadata.phases_completed = existing.get("phases_completed", [])
    except Exception:
        pass
```

**New:** Phase-based resume
```python
def load_existing_metadata(config, file_id):
    # Check if ALL required phases completed successfully
    for phase in config.phases_to_run:
        if pipeline[f"phase{phase}"]["status"] != "success":
            return None  # Must reprocess
    return metadata  # Can skip
```

**Migration:**
- Old resume tracked phases_completed in batch section
- New resume checks actual phase status in phase1-5 sections
- More accurate (uses Phase 6's authoritative data)

### Error Handling

**Old:** Phase-level error tracking
```python
if not success:
    err_msg = f"Phase {phase} failed"
    metadata.errors.append(err_msg)
    return False
```

**New:** File-level error tracking
```python
if process.returncode != 0:
    error_msg = f"Orchestrator failed with exit code {process.returncode}"
    metadata.error_message = error_msg
    metadata.errors.append(stderr[-500:])
```

**Migration:**
- Errors now captured from orchestrator subprocess
- Less granular (file-level not phase-level in Phase 7)
- But more accurate (Phase 6 provides detailed errors)

## Behavioral Differences

### 1. Phase Execution Order

**Old:** Could theoretically execute phases out of order or selectively per file

**New:** Always runs phases in order (1→2→3→4→5) as defined by Phase 6

**Impact:** None if you were running phases sequentially anyway

### 2. Conda Activation

**Old:** Phase 7 tried to activate Conda itself
```python
if env_identifier:
    cmd = ["conda", "run", "-n", env_identifier, "python", ...]
```

**New:** Phase 6 handles Conda activation
```python
# Phase 7 just calls orchestrator
# Phase 6 handles: conda run -n phase4_tts python ...
```

**Impact:** More reliable (Phase 6's Conda handling is battle-tested)

### 3. Progress Reporting

**Old:** Basic progress with tqdm
```python
pbar = tqdm(total=len(input_files))
# Manual updates
pbar.update(1)
```

**New:** Rich progress with better UX
```python
with Progress(...) as progress:
    task = progress.add_task("[cyan]Processing files...", total=len(input_files))
    # Automatic updates
```

**Impact:** Better visual feedback, no functional change

### 4. CPU Monitoring

**Old:** Threading-based monitor
```python
def monitor_cpu(config, stop_event):
    while not stop_event.is_set():
        cpu = psutil.cpu_percent(interval=1)
        if cpu > config.cpu_threshold:
            time.sleep(config.throttle_delay)
```

**New:** Async monitor
```python
async def monitor_cpu_usage(config, cpu_readings, stop_event):
    while not stop_event.is_set():
        await trio.sleep(1)
        cpu = psutil.cpu_percent(interval=0.1)
        if cpu > config.cpu_threshold:
            await trio.sleep(config.throttle_delay)
```

**Impact:** Better async integration, same functionality

### 5. Pipeline JSON Updates

**Old:** Phase 7 updated pipeline.json directly
```python
pipeline["batch"]["files"][file_id] = metadata.dict()
```

**New:** Phase 6 updates pipeline.json, Phase 7 adds batch summary
```python
# Phase 6 updates phase1-5 sections
# Phase 7 only updates batch section
pipeline["batch"] = {"summary": ..., "files": ...}
```

**Impact:** Cleaner separation, less risk of corruption

## Compatibility Notes

### Config Files

Old config.yaml files work with new implementation:
```yaml
# This works in both old and new
phases_to_run: [1, 2, 3, 4, 5]
input_dir: ../input
pipeline_json: ../pipeline.json
max_workers: 2
```

### Pipeline JSON

New implementation reads pipeline.json created by old implementation:
- Reads phase1-5 sections for resume logic
- Overwrites batch section with new format
- Old batch section is replaced (if you need it, back it up)

### Output Files

Same output locations:
- Phase 3: `../phase3-chunking/chunks/`
- Phase 4: `../phase4_tts/audio_chunks/`
- Phase 5: `../phase5_enhancement/output/`

## Troubleshooting Migration

### Issue: "Command not found: batch-audiobook"

**Cause:** CLI entry point not installed

**Fix:**
```bash
poetry install
# Verify
poetry run batch-audiobook --help
```

### Issue: Old behavior expected

**Cause:** Using old main.py

**Fix:**
```bash
# Make sure you're using new CLI
poetry run batch-audiobook
# NOT: poetry run python src/phase7_batch/main.py
```

### Issue: Resume not working

**Cause:** Different resume logic

**Fix:**
```bash
# Check actual phase status
python -c "
import json
p = json.load(open('../pipeline.json'))
for i in [1,2,3,4,5]:
    print(f'Phase {i}:', p.get(f'phase{i}', {}).get('status'))
"
```

### Issue: Different errors than before

**Cause:** Errors now come from Phase 6 subprocess

**Fix:**
```bash
# Test Phase 6 directly
cd ../phase6_orchestrator
poetry run python orchestrator.py ../input/test.pdf
```

## Rollback Plan

If you need to rollback to old implementation:

```bash
# 1. Restore old main.py
cp src/phase7_batch/main_old.py src/phase7_batch/main.py

# 2. Use old invocation
poetry run python src/phase7_batch/main.py

# 3. Restore old config if needed
# (Keep backup of working config)
```

## Testing Migration

### Verification Checklist

After migration, verify:

- [ ] `poetry run batch-audiobook` works
- [ ] Test file processes successfully
- [ ] Output audiobook generated
- [ ] Resume skips completed files
- [ ] Logs are readable
- [ ] Error handling works
- [ ] CPU monitoring works

### Side-by-Side Test

Run both versions on same file:

```bash
# Backup pipeline.json
cp ../pipeline.json ../pipeline_backup.json

# Test old
poetry run python src/phase7_batch/main_old.py
mv ../pipeline.json ../pipeline_old.json

# Test new
cp ../pipeline_backup.json ../pipeline.json
poetry run batch-audiobook
mv ../pipeline.json ../pipeline_new.json

# Compare outputs
diff ../pipeline_old.json ../pipeline_new.json
diff ../phase5_enhancement/output/old_book.mp3 ../phase5_enhancement/output/new_book.mp3
```

## Benefits You'll See

After migration:

1. **Simpler code**: 50% less code in Phase 7
2. **Easier debugging**: Test Phase 6, then Phase 7 separately
3. **Better reliability**: Phase 6's retry logic automatically applies
4. **Faster fixes**: Bug fixes only needed in one place (Phase 6)
5. **Cleaner architecture**: Clear separation of concerns

## Support

If migration issues arise:

1. Check `batch.log` for errors
2. Test Phase 6 directly first
3. Compare pipeline.json formats
4. Try `--max-workers 1` to simplify
5. Use `--no-resume` for fresh start

## Summary

The migration is straightforward:
- Same dependencies
- Same config format
- Same outputs
- Different (simpler) internal implementation

**Recommended approach:**
1. Back up working setup
2. Install new version
3. Test with 1-2 files
4. Verify outputs match
5. Proceed with full migration

The new architecture is production-ready and battle-tested through Phase 6. You'll have an easier time maintaining it going forward! 🎉
