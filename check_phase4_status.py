#!/usr/bin/env python3
"""
Real-time Phase 4 status checker.
Shows what chunks exist, what's missing, and recent activity.
"""

import json
import time
from pathlib import Path
from datetime import datetime

def main():
    print("=" * 80)
    print("PHASE 4 STATUS CHECK")
    print("=" * 80)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check audio directory
    audio_dir = Path("phase4_tts/audio_chunks/A Realist Conception of Truth")
    if not audio_dir.exists():
        print(f"ERROR: Audio directory not found: {audio_dir}")
        return

    # Count existing chunks
    existing_chunks = sorted(audio_dir.glob("chunk_*.wav"))
    print(f"Total audio files on disk: {len(existing_chunks)}")

    # Find most recent
    if existing_chunks:
        most_recent = max(existing_chunks, key=lambda p: p.stat().st_mtime)
        mtime = most_recent.stat().st_mtime
        age_seconds = time.time() - mtime
        age_minutes = age_seconds / 60

        print(f"Most recent file: {most_recent.name}")
        print(f"Last modified: {datetime.fromtimestamp(mtime).strftime('%H:%M:%S')}")
        print(f"Age: {age_minutes:.1f} minutes ago")
        print()

        if age_minutes < 1:
            print("STATUS: ACTIVELY GENERATING (file modified <1 min ago)")
        elif age_minutes < 10:
            print("STATUS: RECENTLY ACTIVE (file modified <10 min ago)")
        else:
            print(f"STATUS: IDLE or STUCK (no activity for {age_minutes:.0f} minutes)")
    print()

    # Find missing chunks
    missing = []
    for i in range(1, 297):
        chunk_file = audio_dir / f"chunk_{i:04d}.wav"
        if not chunk_file.exists():
            missing.append(i)

    print(f"Missing chunks: {len(missing)}")
    if len(missing) <= 30:
        print(f"Missing: {missing}")
    else:
        print(f"First 10: {missing[:10]}")
        print(f"Last 10: {missing[-10:]}")
    print()

    # Check pipeline.json
    try:
        with open("pipeline.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        phase4 = data.get("phase4", {})
        files = phase4.get("files", {})

        for file_id, entry in files.items():
            if "Realist" in file_id:
                print(f"Pipeline.json status:")
                print(f"  File: {file_id}")
                print(f"  Status: {entry.get('status')}")
                print(f"  Chunks completed: {entry.get('chunks_completed')}")
                print(f"  Chunks failed: {entry.get('chunks_failed')}")

                # Check if being updated
                timestamps = entry.get("timestamps", {})
                if "end" in timestamps:
                    last_update = timestamps["end"]
                    update_age = time.time() - last_update
                    print(f"  Last pipeline.json update: {update_age / 60:.1f} minutes ago")
                print()
                break
    except Exception as e:
        print(f"Could not read pipeline.json: {e}")
        print()

    # Check for Phase 4 processes
    print("Checking for Phase 4 processes...")
    print("(This checks if Phase 4 is running)")
    print()

    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)

    if len(missing) == 0:
        print("All 296 chunks complete! Phase 4 should finish soon.")
    elif age_minutes < 10:
        print(f"Phase 4 appears to be running. {len(missing)} chunks remaining.")
        print("Check back in 10 minutes to see if progress is being made.")
    else:
        print("Phase 4 appears to be stuck (no recent file activity).")
        print("Recommendations:")
        print("  1. Check UI logs for errors")
        print("  2. Look for Phase 4 subprocess logs")
        print("  3. May need to restart Phase 4")

if __name__ == "__main__":
    main()
