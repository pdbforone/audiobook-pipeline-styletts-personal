#!/usr/bin/env python3
"""
Verify Systematic Theology extraction quality
Check if it's actually gibberish or readable
"""
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
extracted_file = PROJECT_ROOT / "phase2-extraction" / "extracted_text" / "Systematic Theology.txt"

print("=" * 80)
print("SYSTEMATIC THEOLOGY - QUALITY CHECK")
print("=" * 80)

if not extracted_file.exists():
    print(f"\n❌ File not found: {extracted_file}")
    exit(1)

# Read the file
with open(extracted_file, 'r', encoding='utf-8') as f:
    full_text = f.read()

# Stats
total_chars = len(full_text)
total_words = len(full_text.split())
total_lines = len(full_text.splitlines())

print(f"\n📊 FILE STATISTICS:")
print(f"   Size: {total_chars:,} characters ({total_chars/1024:.1f} KB)")
print(f"   Words: {total_words:,}")
print(f"   Lines: {total_lines:,}")

# Sample from beginning, middle, end
samples = {
    "Beginning (first 500 chars)": full_text[:500],
    "Middle (chars 50,000-50,500)": full_text[50000:50500] if len(full_text) > 50500 else full_text[len(full_text)//2:len(full_text)//2+500],
    "End (last 500 chars)": full_text[-500:]
}

print("\n📄 TEXT SAMPLES:")
print("=" * 80)

for title, sample in samples.items():
    print(f"\n{title}:")
    print("-" * 80)
    print(sample)
    print("-" * 80)
    
    # Quick quality check
    words = sample.split()
    if len(words) > 10:
        english_words = sum(w.isalpha() and len(w) > 2 for w in words[:20])
        print(f"English-like words in first 20: {english_words}/20")

# Comprehensive quality checks
print("\n🔍 QUALITY ANALYSIS:")
print("=" * 80)

# 1. Character distribution
sample_for_analysis = full_text[:10000]  # First 10k chars
alphabetic = sum(c.isalpha() for c in sample_for_analysis)
digits = sum(c.isdigit() for c in sample_for_analysis)
spaces = sum(c.isspace() for c in sample_for_analysis)
punctuation = sum(c in '.,!?;:\'"()-' for c in sample_for_analysis)
other = len(sample_for_analysis) - alphabetic - digits - spaces - punctuation

print(f"\n📈 Character Distribution (first 10k chars):")
print(f"   Alphabetic: {alphabetic/len(sample_for_analysis):.1%}")
print(f"   Digits: {digits/len(sample_for_analysis):.1%}")
print(f"   Spaces: {spaces/len(sample_for_analysis):.1%}")
print(f"   Punctuation: {punctuation/len(sample_for_analysis):.1%}")
print(f"   Other: {other/len(sample_for_analysis):.1%}")

# 2. Common English words check
common_words = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'that', 'for', 'it', 
                'with', 'as', 'was', 'on', 'are', 'by', 'this', 'be', 'from', 'or']
text_lower = full_text[:10000].lower()
found_common = sum(f" {word} " in text_lower for word in common_words)

print(f"\n📚 English Common Words (first 10k chars):")
print(f"   Found {found_common}/20 most common English words")

# 3. Check for gibberish patterns
gibberish_indicators = [
    ('Excessive unicode symbols', len(re.findall(r'[□■○●◆◇△▽▲▼◀▶←→↑↓]', sample_for_analysis))),
    ('Replacement character �', sample_for_analysis.count('�')),
    ('Private use area', sum(ord(c) >= 0xE000 and ord(c) <= 0xF8FF for c in sample_for_analysis)),
    ('Non-ASCII ratio', sum(ord(c) > 127 for c in sample_for_analysis) / len(sample_for_analysis))
]

print(f"\n⚠️  Gibberish Indicators:")
has_issues = False
for indicator, value in gibberish_indicators:
    if indicator == 'Non-ASCII ratio':
        status = "❌" if value > 0.3 else "✓"
        print(f"   {status} {indicator}: {value:.1%}")
        if value > 0.3:
            has_issues = True
    else:
        status = "❌" if value > 50 else "✓"
        print(f"   {status} {indicator}: {value}")
        if value > 50:
            has_issues = True

# Final verdict
print("\n" + "=" * 80)
print("🎯 VERDICT:")
print("=" * 80)

if alphabetic/len(sample_for_analysis) > 0.6 and found_common > 10 and not has_issues:
    print("\n✅ TEXT IS READABLE - GOOD QUALITY EXTRACTION")
    print("   - High alphabetic character ratio")
    print("   - Contains common English words")
    print("   - No significant gibberish indicators")
    print("\n   The file is ready to use!")
    print("   However, it should be processed through Phase 1 → Phase 2 for proper tracking.")
    print("\n   Run: python process_systematic_theology_FIXED.py")
elif alphabetic/len(sample_for_analysis) > 0.4 and found_common > 5:
    print("\n⚠️  TEXT IS PARTIALLY READABLE")
    print("   - Some quality issues detected")
    print("   - May have font encoding problems in some sections")
    print("\n   Recommendation: Re-extract with pypdf")
    print("   Run: python complete_fix_CORRECTED.py")
else:
    print("\n❌ TEXT IS GIBBERISH")
    print("   - Low alphabetic character ratio")
    print("   - Few common English words")
    print("   - Significant gibberish indicators")
    print("\n   Recommendation: Re-extract with different method")
    print("   Run: python test_extraction_methods.py")

print("\n" + "=" * 80)
