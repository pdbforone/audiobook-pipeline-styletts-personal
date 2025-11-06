import json
import sys
from pathlib import Path

# Read the last run results from audio cleanup
log_file = Path("C:/Users/myson/Pipeline/audiobook-pipeline-chatterbox/phase_audio_cleanup/audio_cleanup.log")

if not log_file.exists():
    print("Log file not found. The tool may not have created detailed logs.")
    sys.exit(1)

# Read last 500 lines to find error messages
with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
    
error_lines = [line for line in lines[-1000:] if 'ERROR' in line or 'Error' in line or 'failed' in line]

print("=" * 60)
print("Audio Cleanup Error Summary")
print("=" * 60)
print()

if error_lines:
    print(f"Found {len(error_lines)} error messages:")
    print()
    for line in error_lines[-50:]:  # Last 50 errors
        print(line.strip())
else:
    print("No explicit error messages found in logs.")
    print()
    print("The 94 errors might be from:")
    print("- Corrupted audio files")
    print("- Files too short for Whisper to process")
    print("- Transcription timeouts")
    print("- Missing dependencies")

print()
print("=" * 60)
