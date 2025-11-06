# Test Scripts for Phase 2 Text Cleaner

This directory contains test scripts to verify the text cleaning functionality.

## Quick Start

### Option 1: Run with path fix (works immediately)
```bash
poetry run python test_cleaner_fixed.py
```

### Option 2: Run diagnostic first
```bash
poetry run python diagnose.py
```
This will show you if the package is installed and all dependencies are available.

### Option 3: Test with full Gift of the Magi text
```bash
poetry run python test_full_gift.py
```
Note: Requires `Gift of the Magi.txt` in this directory.

## Fixing "ModuleNotFoundError"

If you get `ModuleNotFoundError: No module named 'phase2_extraction'`, run:

```bash
poetry install
```

This installs the package in editable mode so Python can find it.

## What Each Script Does

- **diagnose.py**: Shows Python environment, paths, and checks if packages are installed
- **test_cleaner_fixed.py**: Quick test with sample text (works without package install)
- **test_full_gift.py**: Full test on your actual text file
- **test_cleaner.py**: Original test (requires `poetry install` first)

## Expected Output

The cleaner should:
- Remove stray single characters (like "p" and "O" on their own lines)
- Collapse spaced-out text: "T h e" → "The"
- Normalize currency: "$1.87" → "one dollar and eighty-seven cents"
- Fix encoding artifacts: "â€œ" → '"'
- Preserve paragraph structure and punctuation

## Files Created

After running tests, you'll see:
- `test_output.txt` - Output from test_cleaner_fixed.py
- `Gift_of_Magi_CLEANED.txt` - Full cleaned version (from test_full_gift.py)
