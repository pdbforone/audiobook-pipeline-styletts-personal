#!/usr/bin/env python3
"""
Debug why File 1 has weird spacing despite normalization.
"""

from pathlib import Path
import re

file1 = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction\extracted_text\Systematic Theology.txt")

print("🔍 Debugging Spacing Issues in File 1")
print("="*60)

with open(file1, 'r', encoding='utf-8') as f:
    text = f.read()

print(f"\n📊 File Stats:")
print(f"   Size: {len(text):,} chars")

# Check for different types of whitespace
spaces = text.count(' ')
tabs = text.count('\t')
newlines = text.count('\n')

print(f"\n🔤 Whitespace Breakdown:")
print(f"   Regular spaces: {spaces:,}")
print(f"   Tabs: {tabs:,}")
print(f"   Newlines: {newlines:,}")

# Check for multiple consecutive spaces (literal)
multi_space = len(re.findall(r' {2,}', text))
print(f"\n⚠️  Multiple consecutive spaces: {multi_space:,}")

# Check for tabs pretending to be spaces
multi_tab = len(re.findall(r'\t+', text))
print(f"⚠️  Tab sequences: {multi_tab:,}")

# Check for mixed space/tab
mixed = len(re.findall(r'[ \t]{2,}', text))
print(f"⚠️  Mixed space/tab sequences: {mixed:,}")

# Show first 500 chars with visible whitespace
print(f"\n📄 First 500 chars (visible whitespace):")
sample = text[:500]
# Replace tabs with [TAB] and spaces with ·
visible = sample.replace('\t', '[TAB]').replace(' ', '·').replace('\n', '↵\n')
print(visible)

# Check if pypdf is adding tabs
print(f"\n🔬 Analysis:")
if tabs > 0:
    print(f"   ❌ PROBLEM: File contains {tabs:,} TAB characters!")
    print(f"   This is why text looks spaced out.")
    print(f"   pypdf is extracting tabs instead of spaces.")
    print(f"\n   💡 Solution: Update TTS normalizer to handle tabs:")
    print(f"      text = text.replace('\\t', ' ')  # Convert tabs to spaces")
    print(f"      text = re.sub(r' {{2,}}', ' ', text)  # Then collapse")
else:
    print(f"   ✅ No tabs found")
    
    if multi_space > 10000:
        print(f"   ❌ But {multi_space:,} multiple-space sequences!")
        print(f"   Normalizer didn't run or failed.")
