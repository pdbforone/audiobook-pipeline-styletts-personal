"""
Subtitle Validation Script
Compares generated subtitles against Phase 2 source text
"""

import argparse
import srt
from pathlib import Path
import difflib
import re

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def extract_subtitle_text(srt_path: Path) -> str:
    with open(srt_path, 'r', encoding='utf-8') as f:
        subtitles = list(srt.parse(f.read()))
    return ' '.join([sub.content for sub in subtitles])

def load_phase2_text(phase2_path: Path) -> str:
    with open(phase2_path, 'r', encoding='utf-8') as f:
        return f.read()

def compute_metrics(source: str, subtitle: str) -> dict:
    src_words = clean_text(source).split()
    sub_words = clean_text(subtitle).split()
    matcher = difflib.SequenceMatcher(None, src_words, sub_words)
    matches = sum(t[2] for t in matcher.get_matching_blocks())
    return {
        'source_words': len(src_words),
        'subtitle_words': len(sub_words),
        'matches': matches,
        'accuracy': (matches / len(src_words) * 100) if src_words else 0,
        'missing': len(src_words) - matches,
        'extra': len(sub_words) - matches
    }

def find_phrases(text: str, phrases: list) -> list:
    results = []
    for phrase in phrases:
        count = text.lower().count(phrase.lower())
        if count > 0:
            results.append((phrase, count))
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase2-text', required=True)
    parser.add_argument('--subtitle-file', required=True)
    parser.add_argument('--output', default='validation_report.txt')
    args = parser.parse_args()
    
    print("Loading files...")
    source = load_phase2_text(Path(args.phase2_text))
    subtitles = extract_subtitle_text(Path(args.subtitle_file))
    
    print("Computing metrics...")
    metrics = compute_metrics(source, subtitles)
    
    print("Finding unwanted phrases...")
    phrases = find_phrases(subtitles, [
        "You need to add some text for me to talk",
        "You need to add text for me to talk"
    ])
    
    report = []
    report.append("=" * 70)
    report.append("SUBTITLE VALIDATION REPORT")
    report.append("=" * 70)
    report.append(f"Source words:    {metrics['source_words']:,}")
    report.append(f"Subtitle words:  {metrics['subtitle_words']:,}")
    report.append(f"Accuracy:        {metrics['accuracy']:.2f}%")
    report.append(f"Missing words:   {metrics['missing']:,}")
    report.append(f"Extra words:     {metrics['extra']:,}")
    report.append("")
    
    if phrases:
        report.append("UNWANTED PHRASES:")
        for phrase, count in phrases:
            report.append(f"  [{count}x] {phrase}")
    else:
        report.append("✅ No unwanted phrases found")
    
    report.append("")
    if metrics['accuracy'] >= 98:
        report.append("✅ EXCELLENT quality")
    elif metrics['accuracy'] >= 95:
        report.append("✓ GOOD quality")
    else:
        report.append("⚠ Review recommended")
    report.append("=" * 70)
    
    report_text = '\n'.join(report)
    Path(args.output).write_text(report_text, encoding='utf-8')
    print("\n" + report_text)
    print(f"\n📄 Report: {args.output}")

if __name__ == "__main__":
    main()
