#!/usr/bin/env python3
"""
Deep comparison of two extracted text files.
Compares content, structure, and quality to determine which is better for TTS.
"""

import difflib
import re
from pathlib import Path
from typing import Dict, List, Tuple

def analyze_file(file_path: Path) -> Dict:
    """Comprehensive analysis of a text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    lines = text.splitlines()
    words = text.split()
    
    # Quality metrics
    analysis = {
        'size': len(text),
        'lines': len(lines),
        'words': len(words),
        'avg_line_length': sum(len(l) for l in lines) / len(lines) if lines else 0,
        'avg_word_length': sum(len(w) for w in words) / len(words) if words else 0,
    }
    
    # TTS-critical issues
    analysis['multiple_spaces'] = len(re.findall(r' {2,}', text))
    analysis['non_ascii'] = sum(1 for c in text if ord(c) > 127)
    analysis['non_ascii_pct'] = (analysis['non_ascii'] / len(text) * 100) if text else 0
    
    # Structure
    analysis['empty_lines'] = sum(1 for l in lines if not l.strip())
    analysis['empty_line_pct'] = (analysis['empty_lines'] / len(lines) * 100) if lines else 0
    analysis['short_lines'] = sum(1 for l in lines if 0 < len(l.strip()) < 10)
    
    # Content patterns
    analysis['sentences'] = len(re.split(r'[.!?]+\s+', text))
    analysis['paragraphs'] = len([p for p in text.split('\n\n') if p.strip()])
    
    # Common artifacts
    analysis['page_numbers'] = len(re.findall(r'^\d+$', text, re.MULTILINE))
    analysis['ocean_pdf'] = len(re.findall(r'OceanofPDF\.com', text, re.IGNORECASE))
    
    return analysis

def compare_text_samples(text1: str, text2: str, sample_size: int = 1000) -> Dict:
    """Compare text samples at different points."""
    comparisons = {}
    
    # Beginning
    comparisons['beginning'] = {
        'text1': text1[:sample_size],
        'text2': text2[:sample_size],
        'identical': text1[:sample_size] == text2[:sample_size]
    }
    
    # Middle
    mid1 = len(text1) // 2
    mid2 = len(text2) // 2
    comparisons['middle'] = {
        'text1': text1[mid1:mid1+sample_size],
        'text2': text2[mid2:mid2+sample_size],
        'identical': text1[mid1:mid1+sample_size] == text2[mid2:mid2+sample_size]
    }
    
    # End
    comparisons['end'] = {
        'text1': text1[-sample_size:],
        'text2': text2[-sample_size:],
        'identical': text1[-sample_size:] == text2[-sample_size:]
    }
    
    return comparisons

def find_differences(text1: str, text2: str, max_examples: int = 5) -> List[Dict]:
    """Find specific differences between texts."""
    differences = []
    
    # Use difflib to find differences
    matcher = difflib.SequenceMatcher(None, text1, text2)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal' and len(differences) < max_examples:
            differences.append({
                'type': tag,
                'text1_pos': f"{i1}-{i2}",
                'text2_pos': f"{j1}-{j2}",
                'text1_content': text1[max(0, i1-30):min(len(text1), i2+30)],
                'text2_content': text2[max(0, j1-30):min(len(text2), j2+30)],
            })
    
    return differences

def compare_files(file1: Path, file2: Path):
    """Deep comparison of two files."""
    print("="*80)
    print("📊 DEEP FILE COMPARISON")
    print("="*80)
    
    print(f"\nFile 1: {file1.name}")
    print(f"File 2: {file2.name}")
    
    # Load files
    with open(file1, 'r', encoding='utf-8') as f:
        text1 = f.read()
    with open(file2, 'r', encoding='utf-8') as f:
        text2 = f.read()
    
    # Quick identity check
    print(f"\n{'='*80}")
    print(f"🔍 IDENTITY CHECK")
    print(f"{'='*80}")
    if text1 == text2:
        print("✅ FILES ARE IDENTICAL!")
        return
    else:
        print("⚠️  Files are DIFFERENT - analyzing differences...")
    
    # Analyze both files
    print(f"\n{'='*80}")
    print(f"📈 METRICS COMPARISON")
    print(f"{'='*80}")
    
    a1 = analyze_file(file1)
    a2 = analyze_file(file2)
    
    metrics = [
        ('Total Size', 'size', 'chars'),
        ('Lines', 'lines', ''),
        ('Words', 'words', ''),
        ('Avg Line Length', 'avg_line_length', 'chars'),
        ('Avg Word Length', 'avg_word_length', 'chars'),
        ('Multiple Spaces', 'multiple_spaces', '⚠️'),
        ('Non-ASCII %', 'non_ascii_pct', '%'),
        ('Empty Lines', 'empty_lines', ''),
        ('Short Lines (<10 chars)', 'short_lines', ''),
        ('Sentences', 'sentences', ''),
        ('Paragraphs', 'paragraphs', ''),
        ('Page Numbers', 'page_numbers', ''),
        ('OceanPDF.com', 'ocean_pdf', ''),
    ]
    
    print(f"\n{'Metric':<30} {'File 1':>15} {'File 2':>15} {'Diff':>15}")
    print(f"{'-'*30} {'-'*15} {'-'*15} {'-'*15}")
    
    for label, key, unit in metrics:
        val1 = a1[key]
        val2 = a2[key]
        diff = val2 - val1
        
        # Format values
        if isinstance(val1, float):
            v1_str = f"{val1:.1f}"
            v2_str = f"{val2:.1f}"
            diff_str = f"{diff:+.1f}"
        else:
            v1_str = f"{val1:,}"
            v2_str = f"{val2:,}"
            diff_str = f"{diff:+,}"
        
        # Add unit
        v1_str = f"{v1_str} {unit}".strip()
        v2_str = f"{v2_str} {unit}".strip()
        diff_str = f"{diff_str} {unit}".strip()
        
        # Color code important differences
        marker = ""
        if key == 'multiple_spaces' and diff != 0:
            marker = " ⚠️" if val2 > val1 else " ✅"
        elif key == 'size' and abs(diff) > 10000:
            marker = " ⚠️" if diff < 0 else " ℹ️"
        
        print(f"{label:<30} {v1_str:>15} {v2_str:>15} {diff_str:>15}{marker}")
    
    # Sample comparisons
    print(f"\n{'='*80}")
    print(f"📖 CONTENT SAMPLES")
    print(f"{'='*80}")
    
    samples = compare_text_samples(text1, text2, 500)
    
    for location, data in samples.items():
        print(f"\n{location.upper()}:")
        if data['identical']:
            print(f"  ✅ Identical")
        else:
            print(f"  ⚠️  Different")
            print(f"\n  File 1 sample:")
            print(f"  {data['text1'][:200].replace(chr(10), '↵')[:200]}...")
            print(f"\n  File 2 sample:")
            print(f"  {data['text2'][:200].replace(chr(10), '↵')[:200]}...")
    
    # Find specific differences
    print(f"\n{'='*80}")
    print(f"🔎 SPECIFIC DIFFERENCES (First 5)")
    print(f"{'='*80}")
    
    differences = find_differences(text1, text2, max_examples=5)
    
    if not differences:
        print("✅ No major structural differences found")
    else:
        for i, diff in enumerate(differences, 1):
            print(f"\nDifference #{i} - Type: {diff['type']}")
            print(f"  Position in File 1: {diff['text1_pos']}")
            print(f"  Position in File 2: {diff['text2_pos']}")
            print(f"  File 1: ...{diff['text1_content'][:100].replace(chr(10), '↵')}...")
            print(f"  File 2: ...{diff['text2_content'][:100].replace(chr(10), '↵')}...")
    
    # Recommendation
    print(f"\n{'='*80}")
    print(f"🎯 RECOMMENDATION")
    print(f"{'='*80}")
    
    score1 = 0
    score2 = 0
    reasons = []
    
    # Scoring criteria
    if a1['multiple_spaces'] < a2['multiple_spaces']:
        score1 += 10
        reasons.append(f"File 1 has fewer spacing issues ({a1['multiple_spaces']} vs {a2['multiple_spaces']})")
    elif a2['multiple_spaces'] < a1['multiple_spaces']:
        score2 += 10
        reasons.append(f"File 2 has fewer spacing issues ({a2['multiple_spaces']} vs {a1['multiple_spaces']})")
    
    if a1['size'] > a2['size']:
        score1 += 5
        diff_pct = ((a1['size'] - a2['size']) / a2['size'] * 100)
        reasons.append(f"File 1 is larger by {diff_pct:.1f}% ({a1['size'] - a2['size']:,} chars)")
    elif a2['size'] > a1['size']:
        score2 += 5
        diff_pct = ((a2['size'] - a1['size']) / a1['size'] * 100)
        reasons.append(f"File 2 is larger by {diff_pct:.1f}% ({a2['size'] - a1['size']:,} chars)")
    
    if a1['non_ascii_pct'] < a2['non_ascii_pct']:
        score1 += 3
        reasons.append(f"File 1 has less non-ASCII content")
    elif a2['non_ascii_pct'] < a1['non_ascii_pct']:
        score2 += 3
        reasons.append(f"File 2 has less non-ASCII content")
    
    print(f"\nScores:")
    print(f"  File 1 ({file1.name}): {score1}")
    print(f"  File 2 ({file2.name}): {score2}")
    
    print(f"\nReasons:")
    for reason in reasons:
        print(f"  • {reason}")
    
    if score1 > score2:
        print(f"\n✅ RECOMMENDATION: Use File 1 ({file1.name})")
    elif score2 > score1:
        print(f"\n✅ RECOMMENDATION: Use File 2 ({file2.name})")
    else:
        print(f"\n⚖️  FILES ARE EQUIVALENT - Use either")
    
    print(f"\n{'='*80}")

if __name__ == "__main__":
    file1 = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction\extracted_text\Systematic Theology.txt")
    file2 = Path(r"C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction\extracted_text\Systematic Theology_TTS_READY.txt")
    
    if not file1.exists():
        print(f"❌ File 1 not found: {file1}")
        exit(1)
    
    if not file2.exists():
        print(f"❌ File 2 not found: {file2}")
        exit(1)
    
    compare_files(file1, file2)
