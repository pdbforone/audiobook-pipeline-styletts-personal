#!/usr/bin/env python3
"""Quick check of the new Phase 2 output."""

from pathlib import Path
import re

# Check the new output
PROJECT_ROOT = Path(__file__).resolve().parents[1]
new_file = (
    PROJECT_ROOT
    / "phase2-extraction"
    / "extracted_text"
    / "Systematic Theology.txt"
)

print("?? Checking New Phase 2 Output")
print("=" * 60)

if not new_file.exists():
    print("? File not found!")
    raise SystemExit(1)

with open(new_file, "r", encoding="utf-8") as f:
    text = f.read()

print(f"? File exists: {new_file.name}")
print(f"   Size: {len(text):,} chars")

# Check for multiple spaces
multiple_spaces = len(re.findall(r" {2,}", text))
print("\n?? Quality Check:")
print(f"   Multiple spaces: {multiple_spaces}")

if multiple_spaces == 0:
    print("   ? PERFECT! No spacing issues!")
else:
    print(f"   ? Still has {multiple_spaces} spacing issues")
    # Show first example
    matches = list(re.finditer(r" {2,}", text))[:1]
    for match in matches:
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        context = text[start:end].replace("\n", "?")
        print(f"   Example: ...{context}...")

print("\n?? Comparison to Test Output:")
test_file = (
    PROJECT_ROOT
    / "phase2-extraction"
    / "extracted_text"
    / "Systematic Theology_TTS_READY.txt"
)

if test_file.exists():
    with open(test_file, "r", encoding="utf-8") as f:
        test_text = f.read()

    test_spaces = len(re.findall(r" {2,}", test_text))

    print(f"   Test output:  {test_spaces} spacing issues")
    print(f"   New output:   {multiple_spaces} spacing issues")

    if multiple_spaces == test_spaces == 0:
        print("\n   ?? SUCCESS! Both outputs are clean!")
    elif multiple_spaces == 0:
        print("\n   ? New output is BETTER than test!")
    elif multiple_spaces < test_spaces:
        print("\n   ? New output is better (fewer issues)")
    elif multiple_spaces > test_spaces:
        print("\n   ? New output is WORSE")
    else:
        print("\n   ??  Both have issues")

print("\n" + "=" * 60)
