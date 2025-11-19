import sys
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent
phase4_dir = PROJECT_ROOT / "phase4_tts"
original = phase4_dir / "audio_chunks"
cleaned = phase4_dir / "meditations_cleaned"

print("=" * 80)
print("Analyzing Missing Meditations Chunks")
print("=" * 80)
print()

# Get all meditations files
all_meditations = list(original.glob("*meditations*.wav"))
cleaned_files = list(cleaned.glob("*.wav")) if cleaned.exists() else []

original_names = {f.name for f in all_meditations}
cleaned_names = {f.name for f in cleaned_files}
missing = original_names - cleaned_names

print(f"Total Meditations files: {len(all_meditations)}")
print(f"Successfully processed: {len(cleaned_files)}")
print(f"Missing: {len(missing)}")
print()

if not missing:
    print("No missing files!")
    sys.exit(0)

# Extract chunk numbers to see if they're sequential
def extract_chunk_number(filename):
    """Extract chunk number from filename."""
    match = re.search(r'chunk[_\s](\d+)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # Try just finding a number
    match = re.search(r'(\d+)', filename)
    if match:
        return int(match.group(1))
    return None

# Analyze missing files
missing_with_chunks = []
missing_without_chunks = []

for filename in missing:
    chunk_num = extract_chunk_number(filename)
    original_path = original / filename
    
    file_size = original_path.stat().st_size if original_path.exists() else 0
    
    if chunk_num is not None:
        missing_with_chunks.append((chunk_num, filename, file_size))
    else:
        missing_without_chunks.append((filename, file_size))

# Sort by chunk number
missing_with_chunks.sort()

print("=" * 80)
print("Analysis of Missing Files:")
print("=" * 80)
print()

# Check for sequential gaps
if missing_with_chunks:
    chunk_numbers = [c[0] for c in missing_with_chunks]
    
    # Find gaps
    gaps = []
    for i in range(len(chunk_numbers) - 1):
        if chunk_numbers[i+1] - chunk_numbers[i] > 1:
            gap_size = chunk_numbers[i+1] - chunk_numbers[i] - 1
            gaps.append((chunk_numbers[i], chunk_numbers[i+1], gap_size))
    
    print(f"Missing chunks with numbers: {len(missing_with_chunks)}")
    print(f"Chunk number range: {min(chunk_numbers)} to {max(chunk_numbers)}")
    print()
    
    # Check file sizes
    zero_byte = [m for m in missing_with_chunks if m[2] == 0]
    small = [m for m in missing_with_chunks if 0 < m[2] < 1000]
    normal = [m for m in missing_with_chunks if m[2] >= 1000]
    
    print("File Size Analysis:")
    print(f"  - Zero bytes: {len(zero_byte)} files (CORRUPT)")
    print(f"  - < 1KB: {len(small)} files (likely corrupt)")
    print(f"  - >= 1KB: {len(normal)} files (may be valid)")
    print()
    
    if zero_byte:
        print("Zero-byte files (first 10):")
        for chunk, name, size in zero_byte[:10]:
            print(f"  Chunk {chunk}: {name}")
        if len(zero_byte) > 10:
            print(f"  ... and {len(zero_byte) - 10} more")
        print()
    
    if normal:
        print("Normal-sized missing files (first 10):")
        for chunk, name, size in normal[:10]:
            print(f"  Chunk {chunk}: {name} ({size:,} bytes)")
        if len(normal) > 10:
            print(f"  ... and {len(normal) - 10} more")
        print()

print("=" * 80)
print("CRITICAL QUESTION:")
print("=" * 80)
print()
print("Are the missing chunks SEQUENTIAL or SCATTERED?")
print()

if missing_with_chunks:
    # Check if missing chunks are sequential
    consecutive_runs = []
    current_run = [chunk_numbers[0]]
    
    for i in range(1, len(chunk_numbers)):
        if chunk_numbers[i] == current_run[-1] + 1:
            current_run.append(chunk_numbers[i])
        else:
            if len(current_run) >= 3:  # Only report runs of 3+
                consecutive_runs.append(current_run)
            current_run = [chunk_numbers[i]]
    
    if len(current_run) >= 3:
        consecutive_runs.append(current_run)
    
    if consecutive_runs:
        print(f"⚠️  WARNING: Found {len(consecutive_runs)} runs of consecutive missing chunks:")
        print()
        for run in consecutive_runs:
            print(f"  Chunks {run[0]} to {run[-1]} ({len(run)} consecutive chunks)")
        print()
        print("This suggests MISSING CONTENT, not just corrupted files!")
        print("These gaps need to be filled by re-processing the original chunks.")
    else:
        print("✓ Missing chunks are SCATTERED (not sequential)")
        print("This suggests they're likely corrupted files, not missing content.")

print()
print("=" * 80)
print("Recommendation:")
print("=" * 80)
print()

# Calculate total duration of missing files
if normal:
    print(f"You have {len(normal)} normal-sized files that failed to process.")
    print("These might contain important content.")
    print()
    print("NEXT STEP: Try to process these files individually to see the actual error.")
else:
    print("Most missing files are zero-byte or corrupt.")
    print("Safe to proceed with the 805 successfully processed files.")

print()
