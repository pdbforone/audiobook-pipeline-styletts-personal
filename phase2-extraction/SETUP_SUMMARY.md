# Phase 2 Cleaner - Setup Summary

## What I Found

✓ Directory structure is CORRECT:
  - `src/phase2_extraction/` exists
  - `cleaner.py` is in the right place with correct code
  - `__init__.py` exists
  - Dependencies (num2words, unidecode) are in pyproject.toml

✗ The issue: Poetry hasn't installed the package in editable mode yet

## Solution - Run These Commands

```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction

# First, ensure package is installed
poetry install

# Then run diagnostics to verify
poetry run python diagnose.py

# If that shows "phase2_extraction" is found, run original test:
poetry run python test_cleaner.py

# OR use the fixed version that works immediately:
poetry run python test_cleaner_fixed.py
```

## What Each Test Does

1. **diagnose.py** - Shows what's installed and where Python is looking
2. **test_cleaner_fixed.py** - Simple test with embedded sample text (WORKS NOW)
3. **test_full_gift.py** - Tests on your full text file if you have it
4. **test_cleaner.py** - Your original test (needs `poetry install` first)

## Expected Results

The cleaner should transform:

BEFORE:
```
T h e G i f t o f t h e M a g i
p
The Gift of the Magi
ONE DOLLAR AND EIGHTY-SEVEN CENTS.
```

AFTER:
```
The Gift of the Magi
The Gift of the Magi
ONE DOLLAR AND EIGHTY-SEVEN CENTS.
```

And "$1.87" becomes "one dollar and eighty-seven cents"

## Next Steps After Testing

Once tests pass:
1. Integrate into extraction.py (I can help with this)
2. Update pipeline.json with cleaning metrics
3. Test on actual PDF extraction
4. Move to Phase 3 (chunking)

## Questions?

If tests fail, share the output from diagnose.py with Claude.
