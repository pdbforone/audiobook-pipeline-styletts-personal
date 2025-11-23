#!/usr/bin/env python3
"""Quick quality check of the new Phase 2 output."""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
file_path = (
    PROJECT_ROOT
    / "phase2-extraction"
    / "extracted_text"
    / "Systematic Theology.txt"
)

print("🔍 Checking Phase 2 Output Quality")
print("=" * 60)

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

print("\n📊 Basic Stats:")
print(f"   Size: {len(text):,} chars")
print(f"   Lines: {len(text.splitlines()):,}")
print(f"   Words: {len(text.split()):,}")

print("\n🎯 TTS Quality Checks:")

# Multiple spaces
multi_space = len(re.findall(r" {2,}", text))
print(f"   Multiple spaces: {multi_space}")
if multi_space == 0:
    print("   ✅ PERFECT - No spacing issues!")
else:
    print(f"   ❌ Found {multi_space} spacing issues")

# Tabs
tabs = text.count("\t")
print(f"   Tab characters: {tabs}")
if tabs == 0:
    print("   ✅ PERFECT - No tabs!")
else:
    print(f"   ❌ Found {tabs} tabs")

# Common words (quality indicator)
sample = text[:20000].lower()
common_words = ["the", "and", "of", "to", "a", "in", "is", "that", "for", "it"]
found = sum(1 for word in common_words if f" {word} " in sample)
print(f"   Common words found: {found}/10")
if found >= 8:
    print("   ✅ EXCELLENT - Text is readable")
else:
    print(f"   ❌ Only {found}/10 common words")

# First 500 chars
print("\n📄 First 500 characters:")
print(f"{text[:500]}")

print(f"\n{'='*60}")
print("Overall Assessment:")
if multi_space == 0 and tabs == 0 and found >= 8:
    print("✅ EXCELLENT QUALITY - Ready for Phase 3!")
elif found >= 8:
    print("⚠️  GOOD QUALITY - Minor issues but usable")
else:
    print("❌ POOR QUALITY - Extraction failed")
