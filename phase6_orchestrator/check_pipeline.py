import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
pipeline_path = PROJECT_ROOT / "pipeline.json"

print(f"Pipeline.json exists: {pipeline_path.exists()}")

if pipeline_path.exists():
    with open(pipeline_path) as f:
        data = json.load(f)
    
    print(f"\nPhase 4 status: {data.get('phase4', {}).get('status')}")
    
    files = data.get('phase4', {}).get('files', {})
    print(f"Phase 4 file IDs: {list(files.keys())}")
    
    if files:
        first_file_id = list(files.keys())[0]
        first_file = files[first_file_id]
        chunks = first_file.get('chunk_audio_paths', [])
        print(f"\nFirst file ID: {first_file_id}")
        print(f"Number of chunks: {len(chunks)}")
        print(f"First 3 chunk paths:")
        for i, path in enumerate(chunks[:3]):
            print(f"  {i}: {path}")
            actual_path = Path(path)
            print(f"     Exists: {actual_path.exists()}")
