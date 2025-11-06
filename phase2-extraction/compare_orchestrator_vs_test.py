#!/usr/bin/env python3
"""
Compare orchestrator output vs test output to find quality differences.
"""

import sys
from pathlib import Path
from difflib import SequenceMatcher

def read_sample(file_path, start=0, length=5000):
    """Read a sample from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        f.seek(start)
        return f.read(length)

def analyze_file(file_path):
    """Analyze file quality metrics."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {file_path.name}")
    print(f"{'='*80}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Basic stats
    print(f"\n📊 Basic Stats:")
    print(f"  Size: {len(content):,} characters ({len(content)/1024/1024:.2f} MB)")
    print(f"  Lines: {content.count(chr(10)):,}")
    print(f"  Paragraphs (double newline): {content.count(chr(10)+chr(10)):,}")
    
    # Quality indicators
    print(f"\n🔍 Quality Indicators:")
    print(f"  Multiple spaces (should be 0): {content.count('  '):,}")
    print(f"  Triple+ spaces: {content.count('   '):,}")
    print(f"  Tabs: {content.count(chr(9)):,}")
    print(f"  Form feeds: {content.count(chr(12)):,}")
    print(f"  Weird unicode: {sum(1 for c in content if ord(c) > 127):,}")
    
    # TTS problems
    print(f"\n⚠️  TTS Problem Indicators:")
    print(f"  Very long lines (>500 chars): {sum(1 for line in content.split(chr(10)) if len(line) > 500):,}")
    print(f"  Very short lines (<10 chars): {sum(1 for line in content.split(chr(10)) if 0 < len(line) < 10):,}")
    print(f"  Lines with only numbers: {sum(1 for line in content.split(chr(10)) if line.strip().isdigit()):,}")
    
    # Content check
    print(f"\n📖 Content Check:")
    words = content.split()
    print(f"  Total words: {len(words):,}")
    print(f"  Unique words: {len(set(words)):,}")
    print(f"  Avg word length: {sum(len(w) for w in words) / len(words) if words else 0:.1f}")
    
    # Show first 1000 chars
    print(f"\n📝 First 1000 characters:")
    print("-" * 80)
    print(content[:1000])
    print("-" * 80)
    
    # Show last 1000 chars
    print(f"\n📝 Last 1000 characters:")
    print("-" * 80)
    print(content[-1000:])
    print("-" * 80)
    
    return content

def find_differences(content1, content2, name1, name2):
    """Find where the files differ."""
    print(f"\n{'='*80}")
    print(f"COMPARING: {name1} vs {name2}")
    print(f"{'='*80}")
    
    # Overall similarity
    ratio = SequenceMatcher(None, content1[:100000], content2[:100000]).ratio()
    print(f"\n📊 Overall Similarity (first 100K): {ratio*100:.2f}%")
    
    # Find first difference
    print(f"\n🔍 Finding first difference...")
    for i, (c1, c2) in enumerate(zip(content1, content2)):
        if c1 != c2:
            start = max(0, i - 200)
            end = min(len(content1), i + 200)
            print(f"\n⚠️  First difference at position {i:,}")
            print(f"\n{name1} context:")
            print("-" * 80)
            print(repr(content1[start:end]))
            print("-" * 80)
            print(f"\n{name2} context:")
            print("-" * 80)
            print(repr(content2[start:end]))
            print("-" * 80)
            break
    else:
        if len(content1) != len(content2):
            print(f"\n⚠️  Files are identical until one ends")
            print(f"  {name1}: {len(content1):,} chars")
            print(f"  {name2}: {len(content2):,} chars")
        else:
            print(f"\n✅ Files are identical!")

def main():
    test_file = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction\extracted_text\Systematic Theology_TTS_READY.txt")
    orch_file = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction\extracted_text\Systematic Theology.txt")
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return 1
    
    if not orch_file.exists():
        print(f"❌ Orchestrator file not found: {orch_file}")
        return 1
    
    # Analyze each file
    print("=" * 80)
    print("FILE COMPARISON: Orchestrator vs Test Output")
    print("=" * 80)
    
    test_content = analyze_file(test_file)
    orch_content = analyze_file(orch_file)
    
    # Compare them
    find_differences(test_content, orch_content, "TEST (TTS_READY)", "ORCHESTRATOR")
    
    # Recommendations
    print(f"\n{'='*80}")
    print("🎯 RECOMMENDATIONS")
    print(f"{'='*80}")
    
    test_score = (
        (100 if test_content.count('  ') < 100 else 0) +
        (100 if len(test_content) > 3700000 else 0) +
        (100 if 'Systematic Theology' in test_content[:1000] else 0)
    )
    
    orch_score = (
        (100 if orch_content.count('  ') < 100 else 0) +
        (100 if len(orch_content) > 3700000 else 0) +
        (100 if 'Systematic Theology' in orch_content[:1000] else 0)
    )
    
    print(f"\nTest file quality score: {test_score}/300")
    print(f"Orchestrator file quality score: {orch_score}/300")
    
    if test_score > orch_score:
        print(f"\n✅ TEST FILE IS BETTER - Use TTS_READY.txt for Phase 3")
    elif orch_score > test_score:
        print(f"\n✅ ORCHESTRATOR FILE IS BETTER - Use Systematic Theology.txt for Phase 3")
    else:
        print(f"\n⚠️  Files are similar - Investigate further")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
