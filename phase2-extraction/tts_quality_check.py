#!/usr/bin/env python3
"""
STRICT TTS-GRADE QUALITY CHECKER for Systematic Theology
Zero tolerance for extraction errors that could cause TTS hallucinations
"""
from pathlib import Path
import re
from collections import Counter

extracted_file = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction\extracted_text\Systematic Theology.txt")

print("=" * 80)
print("TTS-GRADE QUALITY CHECK - SYSTEMATIC THEOLOGY")
print("=" * 80)
print("Standards: Zero tolerance for errors that cause TTS hallucinations")

if not extracted_file.exists():
    print(f"\n❌ File not found: {extracted_file}")
    exit(1)

# Read the file
with open(extracted_file, 'r', encoding='utf-8') as f:
    full_text = f.read()

# Stats
total_chars = len(full_text)
total_words = len(full_text.split())

print(f"\n📊 FILE STATISTICS:")
print(f"   Size: {total_chars:,} characters")
print(f"   Words: {total_words:,}")

# TTS-Critical Checks
issues = []
warnings = []
critical_failures = []

print("\n" + "=" * 80)
print("🔍 TTS-CRITICAL CHECKS")
print("=" * 80)

# 1. ENCODING ERRORS - Zero Tolerance
print("\n1️⃣  ENCODING ERRORS (Zero Tolerance):")
replacement_chars = full_text.count('�')
if replacement_chars > 0:
    critical_failures.append(f"Found {replacement_chars} replacement characters (�)")
    print(f"   ❌ CRITICAL: {replacement_chars} replacement characters found")
else:
    print(f"   ✓ No replacement characters")

# Check for private use area characters (often indicates font mapping issues)
private_use = sum(1 for c in full_text if 0xE000 <= ord(c) <= 0xF8FF)
if private_use > 0:
    critical_failures.append(f"Found {private_use} private use area characters (font mapping error)")
    print(f"   ❌ CRITICAL: {private_use} private use area characters (font mapping failed)")
else:
    print(f"   ✓ No private use area characters")

# 2. GIBBERISH PATTERNS - Very Low Tolerance
print("\n2️⃣  GIBBERISH PATTERNS:")
sample = full_text[:20000]  # First 20k chars

# Check for excessive non-ASCII
non_ascii_ratio = sum(1 for c in sample if ord(c) > 127) / len(sample)
if non_ascii_ratio > 0.15:  # Very strict - 15% max
    critical_failures.append(f"High non-ASCII ratio: {non_ascii_ratio:.1%}")
    print(f"   ❌ CRITICAL: {non_ascii_ratio:.1%} non-ASCII characters (threshold: 15%)")
elif non_ascii_ratio > 0.05:
    warnings.append(f"Moderate non-ASCII ratio: {non_ascii_ratio:.1%}")
    print(f"   ⚠️  WARNING: {non_ascii_ratio:.1%} non-ASCII characters")
else:
    print(f"   ✓ Non-ASCII ratio: {non_ascii_ratio:.1%} (good)")

# Check character type distribution
alpha_ratio = sum(1 for c in sample if c.isalpha()) / len(sample)
if alpha_ratio < 0.65:  # Should be mostly letters
    critical_failures.append(f"Low alphabetic ratio: {alpha_ratio:.1%}")
    print(f"   ❌ CRITICAL: Only {alpha_ratio:.1%} alphabetic characters (need >65%)")
else:
    print(f"   ✓ Alphabetic ratio: {alpha_ratio:.1%}")

# 3. COMMON WORDS CHECK - Must Have These
print("\n3️⃣  ENGLISH LANGUAGE VERIFICATION:")
text_lower = sample.lower()
must_have_words = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'that', 'for', 'it']
found_words = sum(1 for word in must_have_words if f' {word} ' in text_lower)

if found_words < 8:
    critical_failures.append(f"Only found {found_words}/10 common English words")
    print(f"   ❌ CRITICAL: Only {found_words}/10 common words (need 8+)")
else:
    print(f"   ✓ Found {found_words}/10 common English words")

# 4. PUNCTUATION CHECK - Critical for TTS
print("\n4️⃣  PUNCTUATION (Critical for TTS prosody):")
periods = sample.count('.')
commas = sample.count(',')
questions = sample.count('?')
exclamations = sample.count('!')

# Calculate expected punctuation density
word_count = len(sample.split())
punct_per_100_words = (periods + commas + questions + exclamations) / word_count * 100

if punct_per_100_words < 5:
    critical_failures.append(f"Low punctuation density: {punct_per_100_words:.1f} per 100 words")
    print(f"   ❌ CRITICAL: {punct_per_100_words:.1f} punctuation marks per 100 words")
    print(f"      (need 5+) - Will cause bad TTS phrasing")
elif punct_per_100_words < 10:
    warnings.append(f"Below-average punctuation: {punct_per_100_words:.1f} per 100 words")
    print(f"   ⚠️  WARNING: {punct_per_100_words:.1f} punctuation marks per 100 words")
else:
    print(f"   ✓ Punctuation density: {punct_per_100_words:.1f} per 100 words")
    print(f"      Periods: {periods}, Commas: {commas}, Questions: {questions}, Exclamations: {exclamations}")

# 5. SENTENCE STRUCTURE
print("\n5️⃣  SENTENCE STRUCTURE:")
sentences = [s.strip() for s in re.split(r'[.!?]+', sample) if s.strip()]
if len(sentences) < 10:
    critical_failures.append(f"Only {len(sentences)} sentences in first 20k chars")
    print(f"   ❌ CRITICAL: Only {len(sentences)} sentences detected")
else:
    avg_sentence_length = word_count / len(sentences) if sentences else 0
    print(f"   ✓ {len(sentences)} sentences detected")
    print(f"   ✓ Average sentence length: {avg_sentence_length:.1f} words")
    
    if avg_sentence_length > 50:
        warnings.append(f"Very long sentences (avg {avg_sentence_length:.1f} words)")
        print(f"      ⚠️  WARNING: Long sentences may cause TTS issues")

# 6. SPECIAL CHARACTERS THAT BREAK TTS
print("\n6️⃣  TTS-BREAKING CHARACTERS:")
problem_chars = {
    '□': 'Missing character box',
    '■': 'Filled box',
    '●': 'Bullet point (wrong encoding)',
    '◆': 'Diamond',
    '▯': 'Rectangle',
    '\x00': 'Null character',
    '\x01': 'Control character',
}

found_problem_chars = {}
for char, desc in problem_chars.items():
    count = full_text.count(char)
    if count > 0:
        found_problem_chars[char] = (count, desc)
        critical_failures.append(f"Found {count}x '{char}' ({desc})")
        print(f"   ❌ CRITICAL: {count}x '{char}' - {desc}")

if not found_problem_chars:
    print(f"   ✓ No TTS-breaking special characters")

# 7. WORD INTEGRITY CHECK
print("\n7️⃣  WORD INTEGRITY:")
words = sample.split()[:500]  # First 500 words

# Check for garbled words (too many consonants in a row, etc.)
garbled_words = []
for word in words:
    clean_word = re.sub(r'[^a-zA-Z]', '', word)
    if len(clean_word) >= 4:
        # Check for excessive consonants in a row
        consonant_runs = re.findall(r'[bcdfghjklmnpqrstvwxyz]{5,}', clean_word.lower())
        if consonant_runs:
            garbled_words.append(word)
        # Check for no vowels
        if not re.search(r'[aeiou]', clean_word.lower()):
            garbled_words.append(word)

if len(garbled_words) > 10:
    critical_failures.append(f"Found {len(garbled_words)} potentially garbled words")
    print(f"   ❌ CRITICAL: {len(garbled_words)} garbled words detected")
    print(f"      Examples: {', '.join(garbled_words[:5])}")
elif len(garbled_words) > 0:
    warnings.append(f"Found {len(garbled_words)} suspicious words")
    print(f"   ⚠️  WARNING: {len(garbled_words)} suspicious words")
    print(f"      Examples: {', '.join(garbled_words[:3])}")
else:
    print(f"   ✓ No obviously garbled words")

# 8. LINE BREAK SANITY
print("\n8️⃣  LINE BREAKS & FORMATTING:")
lines = full_text.split('\n')
empty_lines = sum(1 for line in lines if not line.strip())
very_short_lines = sum(1 for line in lines if 0 < len(line.strip()) < 10)

print(f"   Total lines: {len(lines)}")
print(f"   Empty lines: {empty_lines} ({empty_lines/len(lines):.1%})")
print(f"   Very short lines (<10 chars): {very_short_lines}")

if very_short_lines > len(lines) * 0.3:
    warnings.append("Many short lines - may have formatting artifacts")
    print(f"   ⚠️  WARNING: {very_short_lines/len(lines):.1%} very short lines")

# 9. SAMPLE TEXT ANALYSIS
print("\n9️⃣  TEXT SAMPLES (Human Review):")
print("   " + "-" * 76)
print("   BEGINNING (first 300 chars):")
print("   " + full_text[:300].replace('\n', '\n   '))
print("   " + "-" * 76)
print("   MIDDLE (around char 100,000):")
mid_start = min(100000, len(full_text)//2)
print("   " + full_text[mid_start:mid_start+300].replace('\n', '\n   '))
print("   " + "-" * 76)

# FINAL VERDICT
print("\n" + "=" * 80)
print("🎯 TTS-GRADE VERDICT")
print("=" * 80)

if critical_failures:
    print("\n❌ FAILED - NOT SUITABLE FOR TTS")
    print("\nCritical Issues:")
    for i, issue in enumerate(critical_failures, 1):
        print(f"   {i}. {issue}")
    print("\n💡 RECOMMENDATION:")
    print("   This extraction has critical errors that WILL cause TTS hallucinations.")
    print("   You must re-extract with a different method.")
    print("\n   Next steps:")
    print("   1. Run: python test_extraction_methods.py")
    print("   2. Test which extraction method produces clean text")
    print("   3. Re-extract using the best method")
    exit_code = 1
elif warnings:
    print("\n⚠️  MARGINAL QUALITY - USE WITH CAUTION")
    print("\nWarnings:")
    for i, warning in enumerate(warnings, 1):
        print(f"   {i}. {warning}")
    print("\n💡 RECOMMENDATION:")
    print("   Text is readable but has minor issues that might affect TTS quality.")
    print("   Consider re-extracting with pypdf for optimal results.")
    print("\n   To proceed anyway: python process_systematic_theology_FIXED.py")
    print("   To re-extract: python complete_fix_CORRECTED.py")
    exit_code = 0
else:
    print("\n✅ EXCELLENT - TTS-READY")
    print("\n   All quality checks passed!")
    print("   Text is clean, well-formatted, and suitable for TTS synthesis.")
    print("\n💡 NEXT STEP:")
    print("   Process through pipeline for tracking:")
    print("   python process_systematic_theology_FIXED.py")
    exit_code = 0

print("\n" + "=" * 80)
exit(exit_code)
