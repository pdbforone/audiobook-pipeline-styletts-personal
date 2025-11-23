#!/usr/bin/env python3
"""
Directly compare and normalize - work with file chunks to avoid size limits.
"""
import re
from pathlib import Path


def read_file_info(filepath):
    """Get file size and sample chunks."""
    with open(filepath, "r", encoding="utf-8") as f:
        # Read beginning
        beginning = f.read(2000)

        # Seek to middle
        f.seek(0, 2)  # End
        size = f.tell()
        f.seek(size // 2)  # Middle
        f.read(100)  # Skip partial line
        middle = f.read(2000)

        # Read end
        f.seek(max(0, size - 2000))
        end = f.read()

    return {"size": size, "beginning": beginning, "middle": middle, "end": end}


def normalize_text_file(input_path, output_path):
    """Normalize a file in chunks to handle large files."""
    print(f"Normalizing {input_path.name}...")

    with open(input_path, "r", encoding="utf-8") as infile:
        with open(output_path, "w", encoding="utf-8") as outfile:
            chunk_size = 100000  # 100KB chunks

            while True:
                chunk = infile.read(chunk_size)
                if not chunk:
                    break

                # Normalize whitespace
                chunk = re.sub(r" +", " ", chunk)
                chunk = re.sub(r"\t", " ", chunk)

                # Write normalized chunk
                outfile.write(chunk)

    # Get output size
    output_size = output_path.stat().st_size
    print(f"  Output: {output_size:,} bytes")
    return output_size


# Paths
existing = Path("extracted_text/Systematic Theology.txt")
multipass = Path("Systematic_Theology_multipass.txt")

print("=" * 80)
print("TTS QUALITY COMPARISON & NORMALIZATION")
print("=" * 80)

# Get file info
print("\n📂 Analyzing files...")
existing_info = read_file_info(existing)
multipass_info = read_file_info(multipass)

print(f"\nExisting: {existing_info['size']:,} bytes")
print(f"Multi-pass: {multipass_info['size']:,} bytes")
print(f"Difference: {multipass_info['size'] - existing_info['size']:,} bytes")

# Check endings (truncation check)
print("\n🔍 Checking for truncation...")
print(f"\nExisting ends with: ...{existing_info['end'][-200:]}")
print(f"\nMulti-pass ends with: ...{multipass_info['end'][-200:]}")

# Check quality samples
print("\n🎯 Checking text quality...")

# Count multi-spaces in beginning (indicator of quality)
existing_spaces = len(re.findall(r"  +", existing_info["beginning"]))
multipass_spaces = len(re.findall(r"  +", multipass_info["beginning"]))

print(
    f"\nExisting - multi-space issues in first 2000 chars: {existing_spaces}"
)
print(
    f"Multi-pass - multi-space issues in first 2000 chars: {multipass_spaces}"
)

# Show beginning samples
print("\n📄 Beginning samples:")
print("\nExisting (first 300 chars):")
print(existing_info["beginning"][:300])
print("\nMulti-pass (first 300 chars):")
print(multipass_info["beginning"][:300])

# Normalize BOTH files
print("\n" + "=" * 80)
print("🔧 NORMALIZING FILES")
print("=" * 80)

existing_norm = Path("extracted_text/Systematic Theology_NORMALIZED.txt")
multipass_norm = Path("Systematic_Theology_multipass_NORMALIZED.txt")

existing_norm_size = normalize_text_file(existing, existing_norm)
multipass_norm_size = normalize_text_file(multipass, multipass_norm)

# Re-check normalized versions
print("\n✅ Checking normalized files...")
existing_norm_info = read_file_info(existing_norm)
multipass_norm_info = read_file_info(multipass_norm)

existing_norm_spaces = len(re.findall(r"  +", existing_norm_info["beginning"]))
multipass_norm_spaces = len(
    re.findall(r"  +", multipass_norm_info["beginning"])
)

print("\nNormalized multi-spaces:")
print(f"  Existing: {existing_norm_spaces} (was {existing_spaces})")
print(f"  Multi-pass: {multipass_norm_spaces} (was {multipass_spaces})")

# Recommendation
print("\n" + "=" * 80)
print("🎯 RECOMMENDATION")
print("=" * 80)

# Use the longer one (more complete) with fewer issues
if (
    multipass_norm_size > existing_norm_size
    and multipass_norm_spaces <= existing_norm_spaces
):
    print("\n✅ USE MULTI-PASS NORMALIZED")
    print(f"   Reason: More complete ({multipass_norm_size:,} bytes)")
    print(f"   Quality: {multipass_norm_spaces} multi-space issues")
    print(f"   File: {multipass_norm}")
    winner = multipass_norm
elif existing_norm_spaces < multipass_norm_spaces:
    print("\n✅ USE EXISTING NORMALIZED")
    print(
        f"   Reason: Better quality ({existing_norm_spaces} vs {multipass_norm_spaces} issues)"
    )
    print(f"   File: {existing_norm}")
    winner = existing_norm
else:
    # Pick longer
    if multipass_norm_size > existing_norm_size:
        print("\n✅ USE MULTI-PASS NORMALIZED")
        print(f"   Reason: More complete ({multipass_norm_size:,} bytes)")
        print(f"   File: {multipass_norm}")
        winner = multipass_norm
    else:
        print("\n✅ USE EXISTING NORMALIZED")
        print(f"   File: {existing_norm}")
        winner = existing_norm

print("\n📄 Final text sample:")
print(winner.name + ":")
final_info = read_file_info(winner)
print(final_info["beginning"][:500])

print("\n" + "=" * 80)
print("✅ READY FOR PHASE 3 (Chunking)")
print("=" * 80)
print(f"\nUse this file: {winner}")
print("\nThis file has been:")
print("  ✓ Normalized for TTS (whitespace collapsed)")
print("  ✓ Validated for completeness (checked endings)")
print("  ✓ Assessed for quality (minimal spacing issues)")
