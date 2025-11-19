#!/usr/bin/env python3
import re
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
existing = PROJECT_ROOT / "phase2-extraction" / "extracted_text" / "Systematic Theology.txt"
multipass = PROJECT_ROOT / "phase2-extraction" / "Systematic_Theology_multipass.txt"

print("Normalizing files for TTS...")

# Normalize existing
print(f"\n1. Normalizing {existing.name}...")
with open(existing, 'r', encoding='utf-8') as f:
    text1 = f.read()

# Normalize: collapse spaces, clean lines
text1 = re.sub(r' +', ' ', text1)
text1 = re.sub(r'\n\n\n+', '\n\n', text1)
text1 = '\n'.join(line.rstrip() for line in text1.split('\n'))

output1 = existing.parent / "Systematic Theology_TTS_READY.txt"
with open(output1, 'w', encoding='utf-8') as f:
    f.write(text1)

print(f"   Original: {existing.stat().st_size:,} bytes")
print(f"   Normalized: {len(text1.encode('utf-8')):,} bytes")
print(f"   Saved: {output1.name}")

# Normalize multipass
print(f"\n2. Normalizing {multipass.name}...")
with open(multipass, 'r', encoding='utf-8') as f:
    text2 = f.read()

text2 = re.sub(r' +', ' ', text2)
text2 = re.sub(r'\n\n\n+', '\n\n', text2)
text2 = '\n'.join(line.rstrip() for line in text2.split('\n'))

output2 = multipass.parent / "Systematic_Theology_multipass_TTS_READY.txt"
with open(output2, 'w', encoding='utf-8') as f:
    f.write(text2)

print(f"   Original: {multipass.stat().st_size:,} bytes")
print(f"   Normalized: {len(text2.encode('utf-8')):,} bytes")
print(f"   Saved: {output2.name}")

# Compare
print(f"\n{'='*80}")
print("COMPARISON")
print(f"{'='*80}")
print(f"\nFile 1 (existing): {len(text1):,} chars")
print(f"File 2 (multipass): {len(text2):,} chars")
print(f"Difference: {abs(len(text2) - len(text1)):,} chars")

# Check endings
print(f"\nFile 1 ends: ...{text1[-100:]}")
print(f"\nFile 2 ends: ...{text2[-100:]}")

# Pick winner (longer = more complete)
if len(text2) > len(text1):
    winner = output2
    print(f"\n✅ WINNER: {output2.name} (more complete)")
else:
    winner = output1
    print(f"\n✅ WINNER: {output1.name}")

print(f"\nThis file is TTS-ready and should be used for Phase 3.")
