import re

def extract_chunk_number(filename: str) -> int:
    """Extract chunk number from filename like 'Gift of the Magi_chunk_001.wav'"""
    match = re.search(r'_chunk_(\d+)', filename)
    if match:
        return int(match.group(1))
    # Fallback: try to find any number
    match = re.search(r'(\d+)', filename)
    if match:
        return int(match.group(1))
    return 0  # Default if no number found

# Test it
test_files = [
    "Gift of the Magi_chunk_001.wav",
    "Gift of the Magi_chunk_010.wav",
    "Gift of the Magi_chunk_002.wav",
    "Gift of the Magi_chunk_041.wav",
]

print("Testing chunk number extraction:")
for f in test_files:
    num = extract_chunk_number(f)
    print(f"{f} → {num}")

# Sort test
sorted_files = sorted(test_files, key=extract_chunk_number)
print("\nSorted:")
for f in sorted_files:
    print(f)
