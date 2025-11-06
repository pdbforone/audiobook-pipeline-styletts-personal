#!/usr/bin/env python3
"""
Quick verification of extraction quality
Shows the first 500 chars of each extracted file
"""
from pathlib import Path

files_to_check = [
    "Systematic_Theology_multipass.txt",
    "Systematic_Theology_multipass_TTS_READY.txt",
    "Systematic_Theology_consensus.txt",
]

print("=" * 80)
print("EXTRACTION QUALITY VERIFICATION")
print("=" * 80)

for filename in files_to_check:
    filepath = Path(filename)
    
    if not filepath.exists():
        print(f"\n❌ {filename} - NOT FOUND")
        continue
    
    # Get file size
    size_mb = filepath.stat().st_size / 1024 / 1024
    
    # Read first 500 chars
    with open(filepath, 'r', encoding='utf-8') as f:
        preview = f.read(500)
    
    # Count total chars
    with open(filepath, 'r', encoding='utf-8') as f:
        total_chars = len(f.read())
    
    print(f"\n{'=' * 80}")
    print(f"📄 {filename}")
    print(f"{'=' * 80}")
    print(f"Size: {size_mb:.2f} MB | Total chars: {total_chars:,}\n")
    print("First 500 characters:")
    print("-" * 80)
    print(preview)
    print("-" * 80)
    
    # Quality checks
    issues = []
    if preview.count('�') > 5:
        issues.append("⚠️  Contains replacement characters (�)")
    if preview.count('\x00') > 0:
        issues.append("⚠️  Contains null bytes")
    if len(preview) < 100:
        issues.append("❌ Text too short!")
    if not any(c.isalpha() for c in preview):
        issues.append("❌ No readable text!")
    
    if issues:
        print("\n⚠️  Quality Issues:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ Text looks good!")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print("\nIf all files show readable text, you're ready for Phase 3!")
print("If you see gibberish or issues, check the self-correction logs.")
