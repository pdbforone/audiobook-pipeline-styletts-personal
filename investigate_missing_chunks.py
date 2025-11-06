import sys
from pathlib import Path
import json

# Find the actual results from the batch run
phase_audio_cleanup = Path("C:/Users/myson/Pipeline/audiobook-pipeline-chatterbox/phase_audio_cleanup")

print("=" * 80)
print("Searching for Audio Cleanup Logs and Results")
print("=" * 80)
print()

# Check various possible log locations
log_locations = [
    phase_audio_cleanup / "audio_cleanup.log",
    phase_audio_cleanup / ".." / "audio_cleanup.log",
    phase_audio_cleanup / "logs" / "audio_cleanup.log",
]

print("Checking log file locations:")
for log_path in log_locations:
    if log_path.exists():
        print(f"  ✓ Found: {log_path}")
        print(f"    Size: {log_path.stat().st_size / 1024:.1f} KB")
        print(f"    Modified: {log_path.stat().st_mtime}")
    else:
        print(f"  ✗ Not found: {log_path}")
print()

# Check for .srt files that might have error info
meditations_cleaned = Path("C:/Users/myson/Pipeline/audiobook-pipeline-chatterbox/phase4_tts/meditations_cleaned")
if meditations_cleaned.exists():
    cleaned_files = list(meditations_cleaned.glob("*.wav"))
    srt_files = list(meditations_cleaned.glob("*.srt"))
    print(f"Cleaned directory contents:")
    print(f"  - {len(cleaned_files)} .wav files")
    print(f"  - {len(srt_files)} .srt transcript files")
    print()

# Check original directory to compare
original = Path("C:/Users/myson/Pipeline/audiobook-pipeline-chatterbox/phase4_tts/audio_chunks")
if original.exists():
    meditations_pattern = "*meditations*.wav"
    all_meditations = list(original.glob(meditations_pattern))
    print(f"Original Meditations chunks: {len(all_meditations)} files")
    print()
    
    # Calculate which files are missing
    if meditations_cleaned.exists():
        original_names = {f.name for f in all_meditations}
        cleaned_names = {f.name for f in cleaned_files}
        missing = original_names - cleaned_names
        
        print(f"Missing from cleaned directory: {len(missing)} files")
        print()
        
        if missing:
            print("Sample of missing files (first 20):")
            for i, filename in enumerate(sorted(missing)[:20]):
                print(f"  {i+1}. {filename}")
            
            if len(missing) > 20:
                print(f"  ... and {len(missing) - 20} more")
            
            # Save full list
            missing_file = Path("C:/Users/myson/Pipeline/audiobook-pipeline-chatterbox/missing_meditations_chunks.txt")
            with open(missing_file, 'w') as f:
                for filename in sorted(missing):
                    f.write(f"{filename}\n")
            print()
            print(f"Full list saved to: {missing_file}")

print()
print("=" * 80)
print("Next Steps:")
print("=" * 80)
print("1. Check if missing files are sequential chunks (indicating content gaps)")
print("2. Try to manually process a few missing files to see what the error is")
print("3. Check file sizes - are they 0 bytes or corrupted?")
print()
