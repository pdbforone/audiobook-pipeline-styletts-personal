#!/usr/bin/env python3
"""
TTS Text Normalizer - Prepares extracted text for high-quality TTS synthesis.

Fixes issues that cause poor TTS quality:
- Multiple spaces (causes unnatural pauses)
- PDF artifacts (OceanofPDF.com, etc.)
- Unicode normalization (fancy quotes → regular)
- Punctuation spacing (critical for prosody)
"""

import re
import unicodedata
from typing import Tuple


def normalize_spaces(text: str) -> str:
    """Collapse multiple spaces and tabs into single space."""
    # First convert tabs to spaces
    text = text.replace("\t", " ")
    # Then collapse any multiple spaces (the winning formula from normalize_now.py)
    text = re.sub(r" +", " ", text)
    # Clean up excessive newlines
    text = re.sub(r"\n\n\n+", "\n\n", text)
    # Trim trailing whitespace from lines
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters (fancy quotes, etc.)."""
    # Normalize to NFKC (canonical decomposition + composition)
    text = unicodedata.normalize("NFKC", text)

    # Replace common problematic characters
    replacements = {
        "\u2018": "'",  # Left single quote
        "\u2019": "'",  # Right single quote
        "\u201c": '"',  # Left double quote
        "\u201d": '"',  # Right double quote
        "\u2013": "-",  # En dash
        "\u2014": "--",  # Em dash
        "\u2026": "...",  # Ellipsis
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def remove_pdf_artifacts(text: str) -> str:
    """Remove common PDF extraction artifacts."""
    artifacts = [
        r"OceanofPDF\.com",
        r"Downloaded from.*\.com",
        r"Visit us at.*\.com",
    ]

    for pattern in artifacts:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text


def fix_punctuation_spacing(text: str) -> str:
    """Fix spacing around punctuation for better TTS prosody."""
    # Remove space before punctuation
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)

    # Ensure space after punctuation (unless end of line)
    text = re.sub(r"([.,!?;:])([^\s\n])", r"\1 \2", text)

    return text


def normalize_for_tts(text: str) -> Tuple[str, dict]:
    """
    Apply all TTS normalizations.

    Returns:
        (normalized_text, stats_dict)
    """
    original_len = len(text)

    # Track changes
    stats = {"original_length": original_len, "changes": []}

    # 1. Normalize spaces
    before = len(re.findall(r" {2,}", text))
    text = normalize_spaces(text)
    after = len(re.findall(r" {2,}", text))
    if before > after:
        stats["changes"].append(
            f"Collapsed {before - after} multiple-space instances"
        )

    # 2. Normalize unicode
    text = normalize_unicode(text)
    stats["changes"].append("Normalized unicode characters")

    # 3. Remove PDF artifacts
    text = remove_pdf_artifacts(text)
    stats["changes"].append("Removed PDF artifacts")

    # 4. Fix punctuation spacing
    text = fix_punctuation_spacing(text)
    stats["changes"].append("Fixed punctuation spacing")

    stats["final_length"] = len(text)
    stats["size_change"] = len(text) - original_len

    return text, stats


def validate_tts_readiness(text: str) -> Tuple[bool, list]:
    """
    Validate text is ready for TTS.

    Returns:
        (is_ready: bool, issues: list[str])
    """
    issues = []

    # Check for multiple spaces
    multiple_spaces = len(re.findall(r" {2,}", text))
    if multiple_spaces > 0:
        issues.append(
            f"Found {multiple_spaces} multiple-space instances (will cause TTS pauses)"
        )

    # Check for excessive non-ASCII
    non_ascii = len([c for c in text if ord(c) > 127])
    non_ascii_pct = (non_ascii / len(text) * 100) if text else 0
    if non_ascii_pct > 5:
        issues.append(
            f"High non-ASCII content ({non_ascii_pct:.1f}%) - may affect TTS"
        )

    # Check for common artifacts
    artifacts = [
        ("OceanofPDF.com", r"OceanofPDF\.com"),
        ("Multiple consecutive newlines", r"\n{4,}"),
    ]

    for name, pattern in artifacts:
        if re.search(pattern, text):
            issues.append(f"Found artifact: {name}")

    is_ready = len(issues) == 0
    return is_ready, issues


# CLI for standalone testing
if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python tts_normalizer.py <input_file> [output_file]")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else input_file.with_stem(f"{input_file.stem}_TTS_READY")
    )

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        sys.exit(1)

    print(f"Normalizing {input_file.name}...")

    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    normalized, stats = normalize_for_tts(text)
    is_ready, issues = validate_tts_readiness(normalized)

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(normalized)

    # Print report
    print(f"\n{'='*60}")
    print("TTS Normalization Complete")
    print(f"{'='*60}")
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print("\nChanges:")
    for change in stats["changes"]:
        print(f"  - {change}")
    print(
        f"\nSize: {stats['original_length']:,} → {stats['final_length']:,} chars ({stats['size_change']:+,})"
    )

    print(f"\n{'='*60}")
    if is_ready:
        print("✅ Text is TTS-ready!")
    else:
        print("⚠️  Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    print(f"{'='*60}")
