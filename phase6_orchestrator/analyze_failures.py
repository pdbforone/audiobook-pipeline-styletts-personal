import json

with open("../pipeline.json", "r") as f:
    data = json.load(f)

phase5 = data.get("phase5", {})
chunks = phase5.get("chunks", [])

# Find failed chunks
failed = [c for c in chunks if c.get("status") == "failed"]
successful = [c for c in chunks if c.get("status", "").startswith("complete")]

print(f"Total chunks: {len(chunks)}")
print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")

# Group failures by error message
from collections import Counter

error_counts = Counter(c.get("error_message", "No error") for c in failed)

print("\nFailure reasons:")
for error, count in error_counts.most_common(10):
    print(f"  {count:3d}x: {error[:100]}")

# Show some specific failed chunks
print("\nSample failed chunks:")
for c in failed[:5]:
    print(
        f'  Chunk {c["chunk_id"]}: {c.get("error_message", "No error")[:150]}'
    )
    print(f'    Status: {c.get("status")}')
    print(f'    Input: {c.get("wav_path", "N/A")[:80]}')
