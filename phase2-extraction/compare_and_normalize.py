#!/usr/bin/env python3
"""
Compare both Systematic Theology extractions for TTS readiness.
Focus on: completeness (no truncation), quality (no errors), normalization.
"""
import re
from pathlib import Path

print("=" * 80)
print("SYSTEMATIC THEOLOGY - TTS QUALITY ASSESSMENT")
print("=" * 80)

existing_file = Path(r"extracted_text/Systematic Theology.txt")
multipass_file = Path(r"Systematic_Theology_multipass.txt")


def read_samples(file_path):
    """Read beginning, middle, end samples."""
    with open(file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    total_len = len(full_text)
    return {
        "full_text": full_text,
        "length": total_len,
        "beginning": full_text[:1000],
        "middle": full_text[total_len // 2 : total_len // 2 + 1000],
        "end": full_text[-1000:],
    }


def normalize_whitespace(text):
    """Normalize whitespace for TTS."""
    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)
    # Collapse multiple newlines (keep max 2 for paragraph breaks)
    text = re.sub(r"\n\n\n+", "\n\n", text)
    # Remove trailing spaces on lines
    lines = text.split("\n")
    lines = [line.rstrip() for line in lines]
    return "\n".join(lines)


def count_tts_issues(text):
    """Count issues that affect TTS quality."""
    sample = text[:50000]  # First 50k chars

    issues = {}

    # Critical issues
    issues["replacement_chars"] = text.count("�")
    issues["multi_spaces"] = len(re.findall(r"  +", text[:20000]))

    # Check for common words (in normalized sample)
    normalized_sample = re.sub(r" +", " ", sample.lower())
    common_words = ["the", "and", "of", "to", "a", "in", "is", "that"]
    issues["common_words_found"] = sum(
        1 for w in common_words if f" {w} " in normalized_sample
    )

    # Check punctuation
    punct = sum(sample.count(c) for c in ".!?,;:")
    words = len(sample.split())
    issues["punct_density"] = (punct / words * 100) if words else 0

    # Check for artifacts
    issues["has_oceanpdf"] = "oceanofpdf" in text.lower()

    return issues


# Load both files
print("\n📂 Loading files...")
existing = read_samples(existing_file)
multipass = read_samples(multipass_file)

print(f"✓ Existing: {existing['length']:,} chars")
print(f"✓ Multi-pass: {multipass['length']:,} chars")
print(
    f"  Difference: {multipass['length'] - existing['length']:,} chars ({(multipass['length']/existing['length']-1)*100:.1f}% more)"
)

# Check for truncation
print("\n" + "=" * 80)
print("🔍 TRUNCATION CHECK")
print("=" * 80)

print("\nExisting file ends with:")
print("-" * 80)
print(existing["end"])
print("-" * 80)

print("\nMulti-pass file ends with:")
print("-" * 80)
print(multipass["end"])
print("-" * 80)

# The longer file is less likely to be truncated
if multipass["length"] > existing["length"]:
    print("\n⚠️  Multi-pass extracted MORE text (less likely to be truncated)")
else:
    print("\n⚠️  Existing extracted MORE text (less likely to be truncated)")

# Analyze TTS issues in BOTH
print("\n" + "=" * 80)
print("🎯 TTS QUALITY ISSUES")
print("=" * 80)

print("\nExisting file:")
existing_issues = count_tts_issues(existing["full_text"])
for key, val in existing_issues.items():
    print(f"  {key}: {val}")

print("\nMulti-pass file:")
multipass_issues = count_tts_issues(multipass["full_text"])
for key, val in multipass_issues.items():
    print(f"  {key}: {val}")

# Normalize BOTH and save
print("\n" + "=" * 80)
print("🔧 NORMALIZING BOTH FILES")
print("=" * 80)

existing_normalized = normalize_whitespace(existing["full_text"])
multipass_normalized = normalize_whitespace(multipass["full_text"])

# Save normalized versions
existing_norm_file = Path("extracted_text/Systematic Theology_normalized.txt")
multipass_norm_file = Path("Systematic_Theology_multipass_normalized.txt")

with open(existing_norm_file, "w", encoding="utf-8") as f:
    f.write(existing_normalized)
print(f"✓ Saved: {existing_norm_file}")
print(f"  Length: {len(existing_normalized):,} chars")
print(
    f"  Reduction: {len(existing['full_text']) - len(existing_normalized):,} chars"
)

with open(multipass_norm_file, "w", encoding="utf-8") as f:
    f.write(multipass_normalized)
print(f"✓ Saved: {multipass_norm_file}")
print(f"  Length: {len(multipass_normalized):,} chars")
print(
    f"  Reduction: {len(multipass['full_text']) - len(multipass_normalized):,} chars"
)

# Re-check issues after normalization
print("\n" + "=" * 80)
print("✅ POST-NORMALIZATION QUALITY")
print("=" * 80)

print("\nExisting (normalized):")
existing_norm_issues = count_tts_issues(existing_normalized)
for key, val in existing_norm_issues.items():
    print(f"  {key}: {val}")

existing_score = 1.0
if existing_norm_issues["replacement_chars"] > 0:
    existing_score -= 0.5
if existing_norm_issues["multi_spaces"] > 10:
    existing_score -= 0.2
if existing_norm_issues["common_words_found"] < 6:
    existing_score -= 0.3
if existing_norm_issues["punct_density"] < 5:
    existing_score -= 0.2

print(f"\n  TTS Score: {existing_score:.2f}")

print("\nMulti-pass (normalized):")
multipass_norm_issues = count_tts_issues(multipass_normalized)
for key, val in multipass_norm_issues.items():
    print(f"  {key}: {val}")

multipass_score = 1.0
if multipass_norm_issues["replacement_chars"] > 0:
    multipass_score -= 0.5
if multipass_norm_issues["multi_spaces"] > 10:
    multipass_score -= 0.2
if multipass_norm_issues["common_words_found"] < 6:
    multipass_score -= 0.3
if multipass_norm_issues["punct_density"] < 5:
    multipass_score -= 0.2

print(f"\n  TTS Score: {multipass_score:.2f}")

# RECOMMENDATION
print("\n" + "=" * 80)
print("🎯 RECOMMENDATION FOR TTS")
print("=" * 80)

if multipass_score > existing_score:
    print("\n✅ USE MULTI-PASS (normalized)")
    print(f"   Score: {multipass_score:.2f} vs {existing_score:.2f}")
    print(
        f"   More complete: +{multipass['length'] - existing['length']:,} chars"
    )
    print(f"   File: {multipass_norm_file}")
    winner = "multipass"
elif existing_score > multipass_score:
    print("\n✅ USE EXISTING (normalized)")
    print(f"   Score: {existing_score:.2f} vs {multipass_score:.2f}")
    print(f"   File: {existing_norm_file}")
    winner = "existing"
else:
    # Tie - pick longer one (more complete)
    if multipass["length"] > existing["length"]:
        print("\n✅ USE MULTI-PASS (normalized) - TIE, but more complete")
        print(f"   Both score: {multipass_score:.2f}")
        print(
            f"   More text: +{multipass['length'] - existing['length']:,} chars"
        )
        print(f"   File: {multipass_norm_file}")
        winner = "multipass"
    else:
        print("\n✅ USE EXISTING (normalized) - TIE")
        print(f"   File: {existing_norm_file}")
        winner = "existing"

# Show text samples
print("\n" + "=" * 80)
print("📄 FINAL TEXT SAMPLES")
print("=" * 80)

if winner == "multipass":
    text = multipass_normalized
else:
    text = existing_normalized

print("\nBeginning (chars 0-500):")
print(text[:500])
print("\nMiddle (around char 100,000):")
print(text[100000:100500])
print("\nEnd (last 500 chars):")
print(text[-500:])

print("\n" + "=" * 80)
print("✅ ANALYSIS COMPLETE")
print("=" * 80)
print("\nRecommended file for Phase 3:")
if winner == "multipass":
    print(f"  {multipass_norm_file}")
else:
    print(f"  {existing_norm_file}")
