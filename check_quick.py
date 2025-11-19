import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
pipeline_path = PROJECT_ROOT / "pipeline.json"
with open(pipeline_path) as f:
    data = json.load(f)

files = data.get('phase4', {}).get('files', {})
print(f"✓ Phase 4 has {len(files)} file(s)")

if files:
    first_id = list(files.keys())[0]
    chunks = files[first_id].get('chunk_audio_paths', [])
    print(f"✓ First file has {len(chunks)} chunks")
    if chunks:
        print(f"✓ First chunk path: {chunks[0]}")
        print(f"✓ Chunk exists: {Path(chunks[0]).exists()}")
else:
    print("✗ NO PHASE 4 DATA!")
