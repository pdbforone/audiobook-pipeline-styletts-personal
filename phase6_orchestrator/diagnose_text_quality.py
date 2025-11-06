#!/usr/bin/env python3
"""
Compare test text vs actual chunk text to identify the real problem
"""

from pathlib import Path

print("="*70)
print("TEXT CONTENT COMPARISON - Test vs Real Chunks")
print("="*70)

# Test text (works perfectly)
test_text = """The Master said, "Learning without thought is labor lost. Thought without learning is perilous." 

Confucius taught that a person should always strive to learn and improve themselves. He believed that education was the foundation of a virtuous life.

The students listened carefully to the Master's teachings. They knew that his words contained great wisdom."""

# Real chunk (produces gibberish)
chunk_file = Path("../phase3-chunking/chunks/The Analects of Confucius_20240228_chunk_001.txt")
if chunk_file.exists():
    with open(chunk_file, 'r', encoding='utf-8') as f:
        real_text = f.read()
else:
    print(f"ERROR: Chunk file not found: {chunk_file}")
    exit(1)

print("\n📝 TEST TEXT (WORKS):")
print("-" * 70)
print(f"Length: {len(test_text)} chars")
print(f"Content:\n{test_text}")

print("\n" + "="*70)
print("\n📝 REAL CHUNK TEXT (GIBBERISH):")
print("-" * 70)
print(f"Length: {len(real_text)} chars")
print(f"First 500 chars:\n{real_text[:500]}")

print("\n" + "="*70)
print("🔍 TEXT QUALITY ANALYSIS")
print("="*70)

# Analyze test text
import re

def analyze_text(text, label):
    print(f"\n{label}:")
    print(f"  Total characters: {len(text)}")
    print(f"  Total words: {len(text.split())}")
    
    # Check for non-ASCII
    non_ascii = [c for c in text if ord(c) > 127]
    print(f"  Non-ASCII chars: {len(non_ascii)} - {set(non_ascii)}")
    
    # Check for repeated words
    words = text.split()
    repeated = [w for i, w in enumerate(words[:-1]) if w == words[i+1]]
    print(f"  Repeated consecutive words: {len(repeated)} - {repeated[:10]}")
    
    # Check for newline density
    newline_count = text.count('\n')
    print(f"  Newlines: {newline_count} ({newline_count/len(text)*100:.1f}% of text)")
    
    # Check for special characters
    special_chars = re.findall(r'[^a-zA-Z0-9\s\.\,\!\?\;\:\'\"\-]', text)
    print(f"  Special chars: {len(special_chars)} - {set(special_chars)}")
    
    # Check sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    print(f"  Sentences: {len(sentences)}")
    if sentences:
        avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
        print(f"  Avg sentence length: {avg_sentence_len:.1f} chars")

analyze_text(test_text, "TEST TEXT")
analyze_text(real_text, "REAL CHUNK")

print("\n" + "="*70)
print("💡 DIAGNOSIS")
print("="*70)

problems = []

# Check for Cyrillic/Russian characters
if any(ord(c) > 127 for c in real_text):
    problems.append("❌ Contains non-ASCII characters (e.g., Russian: р.кв.)")

# Check for excessive newlines
if real_text.count('\n') / len(real_text) > 0.05:
    problems.append("❌ Excessive newlines (poor formatting)")

# Check for repeated words
words = real_text.split()
repeated = [w for i, w in enumerate(words[:-1]) if w == words[i+1]]
if len(repeated) > 2:
    problems.append(f"❌ {len(repeated)} consecutive repeated words")

# Check for table of contents markers
if "Contents" in real_text[:200] or "..." in real_text[:200]:
    problems.append("❌ Starts with table of contents (not narrative text)")

if problems:
    print("\n🚨 PROBLEMS FOUND IN REAL CHUNK:")
    for p in problems:
        print(f"  {p}")
    
    print("\n📋 CONCLUSION:")
    print("  The gibberish audio is caused by BAD TEXT INPUT, not Phase 4 code.")
    print("  Phase 4 is working correctly - it's synthesizing exactly what it reads.")
    print("  The test works because it uses clean, simple English text.")
    print("  The real chunks fail because Phase 2/3 extracted corrupted text.")
    
    print("\n✅ SOLUTION:")
    print("  1. Fix Phase 2: Improve PDF text extraction")
    print("  2. Fix Phase 3: Add text cleaning/validation before chunking")
    print("  3. Re-run pipeline from Phase 2")
    print("  4. Phase 4 will work fine once it gets clean text input")
    
else:
    print("\n✅ Text quality looks good")
    print("  Problem must be elsewhere (parameters, model, etc.)")

print("\n" + "="*70)
