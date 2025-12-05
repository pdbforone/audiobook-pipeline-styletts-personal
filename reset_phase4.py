#!/usr/bin/env python3
"""Reset Phase 4 status to force re-run."""

import json
from pathlib import Path

def reset_phase4(file_id: str) -> None:
    """Reset Phase 4 status for a given file ID."""
    pipeline_json = Path("pipeline.json")

    if not pipeline_json.exists():
        print(f"ERROR: {pipeline_json} not found")
        return

    # Load pipeline data
    with open(pipeline_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Reset Phase 4 status
    p4_files = data.setdefault('phase4', {}).setdefault('files', {})

    if file_id not in p4_files:
        print(f"File ID '{file_id}' not found in Phase 4 data")
        return

    p4_data = p4_files[file_id]

    # Show current status
    print(f"Current Phase 4 status for '{file_id}':")
    print(f"  status: {p4_data.get('status')}")
    print(f"  chunks_completed: {p4_data.get('chunks_completed')}")
    print(f"  chunks_failed: {p4_data.get('chunks_failed')}")
    print(f"  audio_paths: {len(p4_data.get('artifacts', {}).get('chunk_audio_paths', []))}")

    # Reset to pending
    p4_data['status'] = 'pending'
    p4_data['chunks_completed'] = 0
    p4_data['chunks_failed'] = 0
    if 'artifacts' in p4_data:
        p4_data['artifacts']['chunk_audio_paths'] = []

    # Save
    with open(pipeline_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"\nReset Phase 4 to pending for '{file_id}'")
    print("Run the orchestrator with --phases 4 to re-generate audio")


if __name__ == "__main__":
    reset_phase4("376953453-The-World-of-Universals")
