# Quick Bug Fixes Applied

## Issues Found

1. **Missing `errors` field** in `BatchMetadata` model
   - cli.py tried to append to `metadata.errors` but field didn't exist
   - Fix: Added `errors: List[str] = []` to BatchMetadata

2. **Unicode encoding error** on Windows console
   - Arrow character `→` couldn't be encoded in cp1252
   - Error: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`
   - Fix: Changed `→` to `->` for Windows compatibility

## Changes Made

### 1. models.py
```python
class BatchMetadata(BaseModel):
    file_id: str
    status: str = "pending"
    phases_completed: List[int] = []
    chunks_ids: List[int] = []
    error_message: Optional[str] = None
    errors: List[str] = []  # ← ADDED THIS
    duration: Optional[float] = None
    phase_metrics: List[PhaseMetric] = []
    start_time: Optional[float] = None
    end_time: Optional[float] = None
```

### 2. cli.py
```python
# OLD:
Phases:        {' → '.join(map(str, config.phases_to_run))}

# NEW:
phase_display = ' -> '.join(map(str, config.phases_to_run))
Phases:        {phase_display}
```

## Test Again

```bash
poetry run batch-audiobook
```

Should work now without AttributeError or UnicodeEncodeError!
