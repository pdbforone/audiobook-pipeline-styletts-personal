# Pipeline State Manager

**Atomic, transaction-based state management for pipeline.json**

## The Problem

The audiobook pipeline relies on `pipeline.json` as its single source of truth. But the current implementation has critical flaws:

```python
# ❌ UNSAFE - Current pattern
with open('pipeline.json', 'w') as f:
    json.dump(pipeline, f)
```

**Risks:**
- **No atomicity** - crash mid-write = corrupted JSON
- **No locking** - concurrent writes = race conditions
- **No validation** - malformed data silently accepted
- **No backups** - one bad write loses all state
- **No audit trail** - can't debug what happened

## The Solution

Transaction-based state manager with bulletproof guarantees:

```python
# ✅ SAFE - New pattern
from pipeline_common import PipelineState

state = PipelineState("pipeline.json")

with state.transaction() as txn:
    txn.data['phase1']['status'] = 'success'
    txn.data['phase1']['metrics'] = {'duration': 42.0}
    # Commits atomically on success, rolls back on exception
```

**Guarantees:**
- ✓ **Atomic writes** - write-to-temp-then-rename (OS-level atomicity)
- ✓ **File locking** - prevents concurrent corruption
- ✓ **Schema validation** - Pydantic ensures correctness
- ✓ **Automatic backups** - versioned history before every write
- ✓ **Transaction log** - audit trail for debugging
- ✓ **Rollback on error** - failed transactions leave state unchanged

---

## Quick Start

### Basic Usage

```python
from pipeline_common import PipelineState

# Initialize
state = PipelineState("pipeline.json")

# Simple read
data = state.read()

# Simple write (routes through a transactional commit under the hood)
state.write({"phase1": {"status": "pending"}}, validate=False)

# Explicit full-replacement write using a seeded transaction
with state.transaction(validate=False, seed_data={"phase1": {"status": "pending"}}):
    pass

# Transactional update
with state.transaction() as txn:
    txn.data['phase1']['status'] = 'success'
    txn.data['phase1']['files'] = {'book.pdf': {'hash': 'abc123'}}
    # Automatic: backup, validate, atomic write, log
```

### Error Handling

```python
try:
    with state.transaction() as txn:
        txn.data['phase4']['status'] = 'running'

        # If this fails, transaction rolls back automatically
        run_tts_synthesis()

        txn.data['phase4']['status'] = 'success'
except Exception as e:
    # State unchanged - transaction rolled back
    print(f"Phase 4 failed: {e}")

# Targeted error handling
from pipeline_common import StateReadError, StateValidationError

try:
    state.read()
except StateReadError:
    print("pipeline.json is unreadable - try restoring a backup.")
except StateValidationError:
    print("pipeline.json failed schema validation - investigate recent writes.")
```

### Backup Management

```python
# List recent backups
backups = state.list_backups(limit=10)
print(f"Found {len(backups)} backups")

# Restore from backup (e.g., after corruption)
if backups:
    state.restore_backup(backups[0])
    print("State restored")
```

### Transaction History

```python
# View audit trail
history = state.get_transaction_history(limit=20)
for record in history:
    print(f"{record['timestamp']}: {record['operation']} - {record['success']}")
```

---

## Migration Guide

### Before (Unsafe)

```python
# Phase 6 orchestrator - current pattern
with open(pipeline_json, 'r') as f:
    pipeline = json.load(f)

pipeline['phase1'] = {
    'status': 'success',
    'metrics': {'duration': 42.0}
}

with open(pipeline_json, 'w') as f:
    json.dump(pipeline, f, indent=4)
```

### After (Safe)

```python
# Phase 6 orchestrator - with state manager
from pipeline_common import PipelineState

state = PipelineState(pipeline_json)

with state.transaction() as txn:
    txn.data['phase1'] = {
        'status': 'success',
        'metrics': {'duration': 42.0}
    }
```

### Complete Migration Example

```python
#!/usr/bin/env python3
"""
Phase 6 Orchestrator - Migrated to use PipelineState
"""
import sys
from pathlib import Path

# Add pipeline_common to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline_common import PipelineState, StateError


def run_orchestrator(input_file: str, pipeline_json: str):
    """Run phases 1-5 with atomic state management"""

    state = PipelineState(pipeline_json)

    # Phase 1: Validation
    print("Running Phase 1: Validation...")
    try:
        result = run_phase1(input_file)

        # Update state atomically
        with state.transaction() as txn:
            txn.data['phase1'] = {
                'status': 'success',
                'files': result.files,
                'metrics': result.metrics
            }
        print("✓ Phase 1 complete")
    except Exception as e:
        print(f"✗ Phase 1 failed: {e}")
        # State unchanged - transaction rolled back
        return False

    # Phase 2: Extraction
    print("Running Phase 2: Extraction...")
    try:
        # Read current state
        data = state.read()
        file_id = data.get('file_id')

        result = run_phase2(file_id)

        # Update atomically
        with state.transaction() as txn:
            txn.data['phase2'] = {
                'status': 'success',
                'files': result.files,
                'metrics': result.metrics
            }
        print("✓ Phase 2 complete")
    except Exception as e:
        print(f"✗ Phase 2 failed: {e}")
        return False

    # Continue for phases 3-5...

    return True


def run_phase1(input_file):
    # Existing Phase 1 logic
    pass

def run_phase2(file_id):
    # Existing Phase 2 logic
    pass


if __name__ == '__main__':
    success = run_orchestrator(
        input_file='book.pdf',
        pipeline_json='pipeline.json'
    )
    sys.exit(0 if success else 1)
```

---

## Advanced Features

### Schema Validation

```python
# Enable strict validation (requires Pydantic)
state = PipelineState("pipeline.json", validate_on_read=True)

# Valid data passes
with state.transaction() as txn:
    txn.data['phase1'] = {
        'status': 'success',  # Valid status
        'metrics': {'duration': 42.0}
    }

# Invalid data raises StateValidationError
try:
    with state.transaction() as txn:
        txn.data['phase1'] = "not a dict"  # Invalid!
except StateValidationError as e:
    print(f"Validation failed: {e}")
```

### Custom Backup Settings

```python
# Keep more backups, disable auto-backup
state = PipelineState(
    "pipeline.json",
    max_backups=100,
    backup_before_write=False  # Manual backup control
)

# Manual backup
state.backup_manager.create_backup()
```

### Debugging with Transaction Log

```python
# View what happened during a failed run
history = state.get_transaction_history(limit=50)

for record in history:
    if not record['success']:
        print(f"Failed operation: {record['operation']}")
        print(f"  Time: {record['timestamp']}")
        print(f"  Error: {record['details']}")
```

---

## Architecture

### File Structure

```
pipeline.json              # Current state (atomic writes)
pipeline.json.lock         # Lock file (prevents concurrent writes)
.pipeline/
  ├── backups/
  │   ├── pipeline_20241106_120000_123456.json.bak
  │   ├── pipeline_20241106_130000_234567.json.bak
  │   └── ... (up to max_backups files)
  └── transactions.log     # Append-only audit log
```

### How Atomic Writes Work

1. **Create backup** of current state (if enabled)
2. **Write to temporary file** with unique name (e.g., `pipeline.12345_1699284123.tmp`)
3. **Flush to disk** (`fsync`) to ensure data is written
4. **Atomic rename** temp file → actual file (OS-level atomic operation)
5. **Log transaction** to audit trail
6. **Rotate backups** if over limit

If the process crashes at any point:
- Steps 1-3: Original file unchanged
- Step 4: Either old file OR new file exists (never corrupted partial write)
- Step 5-6: State is valid, just log/backups incomplete

### How File Locking Works

```python
with state._file_lock(timeout=10.0):
    # Only one process can enter this block at a time
    # Other processes wait up to timeout seconds
    data = read_state()
    modify(data)
    write_state(data)
```

**Cross-Platform Locking:**
- **Unix/Linux/macOS**: Uses `fcntl.flock()` for advisory locking
- **Windows**: Uses `msvcrt.locking()` for mandatory locking
- **Exclusive lock** during write operations
- **Timeout-based** to prevent deadlocks
- **Automatic cleanup** on process exit
- **Cross-process** safety (works across Python processes)

---

## Testing

Run the demonstration script:

```bash
python3 pipeline_common/demo.py
```

This proves:
- Atomic writes prevent corruption
- Transactions commit/rollback correctly
- Backups are created and rotated
- Concurrent access is safe
- Schema validation works
- Crash recovery succeeds

Run the test suite (requires pytest):

```bash
cd pipeline_common
pytest test_state_manager.py -v
```

---

## API Reference

### PipelineState

```python
class PipelineState:
    def __init__(
        self,
        path: str | Path,
        validate_on_read: bool = False,
        max_backups: int = 50,
        backup_before_write: bool = True
    )
```

**Methods:**

- `read(validate=None) -> Dict` - Read current state
- `write(data, validate=True)` - Write state atomically
- `transaction() -> StateTransaction` - Create transaction context manager
- `list_backups(limit=10) -> List[Path]` - List recent backups
- `restore_backup(backup_path) -> bool` - Restore from backup
- `get_transaction_history(limit=50) -> List[Dict]` - View audit log

### StateTransaction

```python
with state.transaction() as txn:
    txn.data['key'] = 'value'  # Modify in place
    # Commits on __exit__ if no exception
    # Rolls back if exception raised
```

---

## Performance

**Overhead:**
- ~1-2ms per transaction (backup + atomic write + log)
- ~100-200μs for file lock acquisition (uncontended)
- ~50KB disk space per backup (for typical pipeline.json)

**Scalability:**
- Handles 100+ transactions/second easily
- Concurrent access limited by file locking (sequential writes)
- Backup rotation prevents disk space growth

**Recommendations:**
- Use transactions for all state updates
- Disable validation in performance-critical paths (validate in tests instead)
- Increase `max_backups` if you want longer history

---

## Troubleshooting

### Lock Timeout

```
StateLockError: Could not acquire lock after 10s
```

**Cause:** Another process holds the lock too long

**Solutions:**
- Increase timeout: `state = PipelineState(path, timeout=30.0)`
- Check for stuck processes: `ps aux | grep python`
- Remove stale lock: `rm pipeline.json.lock` (safe if no processes running)

### Corrupted State

```
StateError: Corrupted state file: JSONDecodeError
```

**Cause:** Manual edit, disk error, or crash (rare)

**Solutions:**
```python
# Restore from most recent backup
backups = state.list_backups()
if backups:
    state.restore_backup(backups[0])
```

### Validation Errors

```
StateValidationError: Schema validation failed
```

**Cause:** Data doesn't match expected schema

**Solutions:**
- Check phase output matches schema (see `PIPELINE_JSON_SCHEMA.md`)
- Disable validation temporarily: `state.write(data, validate=False)`
- Update schema in `pipeline_common/models.py` if structure changed

---

## Design Philosophy

### Why Transactions?

Database-inspired transactions provide clean semantics:
- **Atomic** - all changes succeed or none do
- **Consistent** - only valid states persisted
- **Isolated** - concurrent transactions don't interfere
- **Durable** - committed changes survive crashes

### Why File Locking?

Alternative approaches considered:
- ❌ **No locking** - race conditions, data loss
- ❌ **Application-level locks** - doesn't work across processes
- ❌ **Database** - adds complexity, not needed for single-file state
- ✅ **File locking** - OS-level guarantees, simple, cross-process

### Why Backups?

Git-inspired versioning:
- Every write creates a backup (like a commit)
- Can restore any previous state
- Rotation prevents unbounded growth
- Enables time-travel debugging

---

## Future Enhancements

Potential improvements (not implemented yet):

1. **Compression** - gzip backups to save space
2. **Encryption** - encrypt state at rest
3. **Replication** - sync to remote storage (S3, etc.)
4. **Merge strategies** - handle concurrent edits intelligently
5. **Event hooks** - callbacks on state changes
6. **Async API** - `async with state.transaction()`

---

## License

Part of the audiobook-pipeline-chatterbox project.

---

## Credits

Built with inspiration from:
- SQLite's atomic commit protocol
- Git's content-addressable storage
- PostgreSQL's MVCC transactions
- Redis's AOF persistence

Designed for reliability, not features. Every line justified.
