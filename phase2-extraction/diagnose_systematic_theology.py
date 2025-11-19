#!/usr/bin/env python3
"""
Diagnose extraction issues with Systematic Theology.txt
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
extracted_file = PROJECT_ROOT / "phase2-extraction" / "extracted_text" / "Systematic Theology.txt"

print("=" * 80)
print("SYSTEMATIC THEOLOGY EXTRACTION DIAGNOSTIC")
print("=" * 80)

# Read sample
try:
    with open(extracted_file, 'r', encoding='utf-8') as f:
        full_text = f.read()
    
    sample = full_text[:2000]
    
    print(f"\n📊 FILE STATS:")
    print(f"   Total length: {len(full_text):,} characters")
    print(f"   Total words: {len(full_text.split()):,}")
    print(f"   Total lines: {len(full_text.splitlines()):,}")
    
    print(f"\n📝 FIRST 500 CHARACTERS:")
    print("-" * 80)
    print(sample[:500])
    print("-" * 80)
    
    print(f"\n🔤 CHARACTER ANALYSIS:")
    print(f"   Unique characters: {len(set(full_text))}")
    print(f"   Alphabetic ratio: {sum(c.isalpha() for c in sample) / len(sample):.1%}")
    print(f"   Digit ratio: {sum(c.isdigit() for c in sample) / len(sample):.1%}")
    print(f"   Space ratio: {sum(c.isspace() for c in sample) / len(sample):.1%}")
    print(f"   Punctuation ratio: {sum(not c.isalnum() and not c.isspace() for c in sample) / len(sample):.1%}")
    
    # Check for common gibberish patterns
    print(f"\n🔍 GIBBERISH DETECTION:")
    
    # Check for excessive special characters
    special_chars = set('□■○●◆◇△▽▲▼◀▶←→↑↓↔↕⇐⇒⇑⇓⇔⇕∴∵∩∪⊂⊃⊆⊇⊥∠∴')
    special_count = sum(c in special_chars for c in sample)
    print(f"   Special unicode chars: {special_count} ({special_count/len(sample):.1%})")
    
    # Check for excessive non-ASCII
    non_ascii = sum(ord(c) > 127 for c in sample)
    print(f"   Non-ASCII characters: {non_ascii} ({non_ascii/len(sample):.1%})")
    
    # Check for actual words
    words = sample.split()[:50]
    english_like = sum(word.isalpha() and len(word) > 2 for word in words)
    print(f"   English-like words in first 50: {english_like}/50")
    
    print(f"\n📋 FIRST 50 WORDS:")
    print(" ".join(words[:50]))
    
    # Look for PDF font mapping issues (common cause of gibberish)
    print(f"\n⚠️  POTENTIAL ISSUES:")
    if non_ascii / len(sample) > 0.3:
        print("   ❌ HIGH NON-ASCII RATIO - Likely font encoding issue")
    if english_like < 30:
        print("   ❌ LOW ENGLISH WORD COUNT - Text extraction method problem")
    if special_count > 100:
        print("   ❌ EXCESSIVE SPECIAL CHARACTERS - Font mapping problem")
    
    # Try to detect if it's encrypted or using custom fonts
    if any(c in sample for c in ['', '', '', '']):
        print("   ⚠️  Contains private use area Unicode - Custom font mapping issue")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
