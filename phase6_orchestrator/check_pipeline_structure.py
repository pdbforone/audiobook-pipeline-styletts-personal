"""Quick script to check pipeline.json structure for coverage tests."""
import json
from pathlib import Path

pipeline_path = Path("../pipeline.json")

with open(pipeline_path, 'r', encoding='utf-8') as f:
    pipeline = json.load(f)

# Get file IDs
phase2_files = list(pipeline.get('phase2', {}).get('files', {}).keys())
phase3_files = list(pipeline.get('phase3', {}).get('files', {}).keys())
phase4_files = list(pipeline.get('phase4', {}).get('files', {}).keys())

print("=" * 70)
print("PIPELINE STRUCTURE CHECK")
print("=" * 70)
print(f"\nPhase 2 file_ids: {phase2_files}")
print(f"Phase 3 file_ids: {phase3_files}")
print(f"Phase 4 file_ids: {phase4_files}")

if phase2_files:
    file_id = phase2_files[0]
    print(f"\nUsing file_id: {file_id}")
    
    # Phase 2 structure
    phase2_data = pipeline['phase2']['files'][file_id]
    extracted_text_path = phase2_data.get('extracted_text_path') or phase2_data.get('output_file')
    print(f"\nPhase 2 extracted_text_path: {extracted_text_path}")
    
    # Resolve relative path from pipeline root
    if extracted_text_path and not Path(extracted_text_path).is_absolute():
        abs_path = (Path("..") / extracted_text_path).resolve()
        print(f"  Resolved to: {abs_path}")
        print(f"  File exists: {abs_path.exists()}")
    else:
        print(f"  File exists: {Path(extracted_text_path).exists() if extracted_text_path else 'N/A'}")
    
    # Phase 3 structure
    if file_id in pipeline.get('phase3', {}).get('files', {}):
        phase3_data = pipeline['phase3']['files'][file_id]
        chunk_paths_data = phase3_data.get('chunk_paths', [])
        print(f"\nPhase 3 chunks: {len(chunk_paths_data)}")
        
        # Show first chunk structure - handle both list and dict
        if chunk_paths_data:
            if isinstance(chunk_paths_data, list):
                first_chunk_path = chunk_paths_data[0]
                print(f"  Structure type: list")
                print(f"  Sample chunk path: {first_chunk_path}")
                # Resolve relative path
                if not Path(first_chunk_path).is_absolute():
                    abs_chunk = (Path("..") / first_chunk_path).resolve()
                    print(f"    Resolved to: {abs_chunk}")
                    print(f"    File exists: {abs_chunk.exists()}")
                else:
                    print(f"    File exists: {Path(first_chunk_path).exists()}")
            elif isinstance(chunk_paths_data, dict):
                first_chunk_id = list(chunk_paths_data.keys())[0]
                first_chunk_data = chunk_paths_data[first_chunk_id]
                print(f"  Structure type: dict")
                print(f"  Sample chunk ID: {first_chunk_id}")
                if isinstance(first_chunk_data, dict):
                    chunk_path = first_chunk_data.get('path')
                    print(f"    Path: {chunk_path}")
                    print(f"    File exists: {Path(chunk_path).exists() if chunk_path else 'N/A'}")
                else:
                    print(f"    Path: {first_chunk_data}")
                    print(f"    File exists: {Path(first_chunk_data).exists()}")
    
    # Phase 4 structure
    if file_id in pipeline.get('phase4', {}).get('files', {}):
        phase4_data = pipeline['phase4']['files'][file_id]
        audio_paths = phase4_data.get('chunk_audio_paths', [])
        print(f"\nPhase 4 audio files: {len(audio_paths)}")
        print(f"  Phase 4 status: {pipeline.get('phase4', {}).get('status', 'unknown')}")
        
        # Check a sample
        if audio_paths:
            sample_audio = Path(audio_paths[0])
            print(f"  Sample audio: {sample_audio.name}")
            print(f"  File exists: {sample_audio.exists()}")

print("\n" + "=" * 70)
print("Ready to run coverage tests!")
print("=" * 70)
