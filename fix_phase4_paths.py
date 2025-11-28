#!/usr/bin/env python3
"""
Fix Phase 4 pipeline.json to include all existing audio files.

This script scans the audio_chunks directory and adds all valid WAV files
to the chunk_audio_paths array, allowing Phase 4 to resume instead of rerun.
"""

import json
from pathlib import Path
import wave

def main():
    # Paths
    pipeline_json = Path("pipeline.json")
    audio_dir = Path("phase4_tts/audio_chunks/A Realist Conception of Truth")

    # Read pipeline.json
    with open(pipeline_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Get Phase 4 entry
    phase4 = data.get("phase4", {})
    files = phase4.get("files", {})
    file_entry = files.get("A Realist Conception of Truth", {})

    print(f"Current state:")
    print(f"  chunk_audio_paths: {len(file_entry.get('chunk_audio_paths', []))} entries")
    print(f"  chunks_completed: {file_entry.get('chunks_completed')}")
    print(f"  chunks_failed: {file_entry.get('chunks_failed')}")
    print()

    # Scan audio directory for all chunks
    if not audio_dir.exists():
        print(f"Error: Audio directory not found: {audio_dir}")
        return

    wav_files = sorted(audio_dir.glob("chunk_*.wav"))
    print(f"Found {len(wav_files)} audio files on disk")
    print()

    # Validate each file and collect paths
    valid_paths = []
    invalid_files = []

    for wav_file in wav_files:
        try:
            # Check if file is valid WAV
            with wave.open(str(wav_file), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)

                # Skip empty or corrupted files
                if duration < 0.1:
                    invalid_files.append((wav_file.name, "too short"))
                    continue

                # Add absolute path
                valid_paths.append(str(wav_file.resolve()))

        except Exception as e:
            invalid_files.append((wav_file.name, str(e)))

    print(f"Valid audio files: {len(valid_paths)}")
    if invalid_files:
        print(f"Invalid files: {len(invalid_files)}")
        for name, reason in invalid_files[:5]:
            print(f"  - {name}: {reason}")
        if len(invalid_files) > 5:
            print(f"  ... and {len(invalid_files) - 5} more")
    print()

    # Update pipeline.json
    file_entry["chunk_audio_paths"] = valid_paths
    file_entry["chunks_completed"] = len(valid_paths)
    file_entry["chunks_failed"] = 296 - len(valid_paths)

    # Update metrics
    if "metrics" not in file_entry:
        file_entry["metrics"] = {}
    file_entry["metrics"]["chunks_completed"] = len(valid_paths)
    file_entry["metrics"]["chunks_failed"] = 296 - len(valid_paths)
    file_entry["metrics"]["total_chunks"] = 296

    # Update status
    if len(valid_paths) == 296:
        file_entry["status"] = "success"
    elif len(valid_paths) > 0:
        file_entry["status"] = "partial"
    else:
        file_entry["status"] = "failed"

    # Write back
    files["A Realist Conception of Truth"] = file_entry
    phase4["files"] = files
    data["phase4"] = phase4

    # Backup original
    backup_path = pipeline_json.with_suffix(".json.backup")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Backed up original to: {backup_path}")

    # Write updated pipeline.json
    with open(pipeline_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Updated pipeline.json:")
    print(f"  chunk_audio_paths: {len(valid_paths)} entries")
    print(f"  chunks_completed: {len(valid_paths)}")
    print(f"  chunks_failed: {296 - len(valid_paths)}")
    print(f"  status: {file_entry['status']}")
    print()
    print("Phase 4 will now resume and only process the missing chunks!")

if __name__ == "__main__":
    main()
