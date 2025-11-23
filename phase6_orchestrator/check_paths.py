import json
from pathlib import Path

with open("../pipeline.json", "r") as f:
    data = json.load(f)

# Get Phase 4 paths
phase4 = data.get("phase4", {})
files = phase4.get("files", {})

for file_id, file_data in files.items():
    chunk_paths = file_data.get("chunk_audio_paths", [])

    print(f"File ID: {file_id}")
    print(f"Total chunk_audio_paths: {len(chunk_paths)}")
    print()
    print("Sample paths from pipeline.json:")
    for i in [0, 1, 2, -3, -2, -1]:
        if 0 <= i < len(chunk_paths) or -len(chunk_paths) <= i < 0:
            path = chunk_paths[i]
            print(f"  [{i:3d}]: {path}")

            # Check if path exists as-is
            p = Path(path)
            print(f"         Absolute: {p.is_absolute()}")
            print(f"         Exists as-is: {p.exists()}")

            # Try resolving from project root
            from_root = Path("..") / path
            print(
                f"         From root: {from_root.exists()} ({from_root.resolve()})"
            )

            # Try resolving from phase4_tts/audio_chunks
            filename = Path(path).name
            from_phase4 = Path("../phase4_tts/audio_chunks") / filename
            print(
                f"         From phase4: {from_phase4.exists()} ({from_phase4.resolve()})"
            )
            print()
