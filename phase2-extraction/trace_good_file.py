#!/usr/bin/env python3
"""
Figure out HOW Systematic Theology_TTS_READY.txt was actually created.
Check the timestamps and file history.
"""

from pathlib import Path
import os
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
files_dir = PROJECT_ROOT / "phase2-extraction" / "extracted_text"

print("🔍 File History Investigation")
print("="*60)

# Get all Systematic Theology files
systematic_files = [
    files_dir / "Systematic Theology.txt",
    files_dir / "Systematic Theology_TTS_READY.txt"
]

# Add parent directory files
parent_files = [
    files_dir.parent / "Systematic_Theology_multipass.txt",
    files_dir.parent / "Systematic_Theology_multipass_TTS_READY.txt"
]

all_files = [(f, "extracted_text") for f in systematic_files if f.exists()] + \
            [(f, "parent") for f in parent_files if f.exists()]

print(f"\n📁 Found {len(all_files)} Systematic Theology files:")

for file_path, location in sorted(all_files, key=lambda x: os.path.getmtime(x[0])):
    stat = file_path.stat()
    created = time.ctime(stat.st_ctime)
    modified = time.ctime(stat.st_mtime)
    size = stat.st_size
    
    print(f"\n  {file_path.name} ({location}/)")
    print(f"    Created:  {created}")
    print(f"    Modified: {modified}")
    print(f"    Size:     {size:,} bytes")
    
    # Read first 200 chars
    with open(file_path, 'r', encoding='utf-8') as f:
        first_200 = f.read(200)
    print(f"    Starts:   {first_200[:100].replace(chr(10), '↵')}")

print(f"\n{'='*60}")
print("💡 Analysis:")
print("="*60)

# The _TTS_READY file was created Oct 16 00:03:33
# Let's check what script could have created it
print("""
Based on timestamps, Systematic Theology_TTS_READY.txt was created on:
  Oct 16, 2025 at 00:03:33

This was likely created by one of these scripts:
  1. normalize_now.py (normalizes existing files)
  2. multi_pass_extractor.py (multi-method extraction)
  3. Some manual test script

To recreate the GOOD output, we need to find which extraction
method was used BEFORE normalization.

Let me check the multipass file...
""")

multipass = files_dir.parent / "Systematic_Theology_multipass.txt"
if multipass.exists():
    with open(multipass, 'r', encoding='utf-8') as f:
        mp_text = f.read()
    
    tts_ready = files_dir / "Systematic Theology_TTS_READY.txt"
    with open(tts_ready, 'r', encoding='utf-8') as f:
        tts_text = f.read()
    
    # Check if they start the same way (before normalization)
    if mp_text[:100] == tts_text[:100]:
        print("✅ TTS_READY was normalized from multipass!")
        print("   The multipass extraction is the BETTER method!")
    else:
        print("⚠️  TTS_READY came from a different source")
        print(f"\n  Multipass starts: {mp_text[:100].replace(chr(10), '↵')}")
        print(f"\n  TTS_READY starts: {tts_text[:100].replace(chr(10), '↵')}")
