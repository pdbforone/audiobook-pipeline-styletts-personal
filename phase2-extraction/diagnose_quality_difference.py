#!/usr/bin/env python3
"""
Diagnose why test output is better quality than orchestrator output.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def analyze_text_quality(file_path, label):
    """Analyze text quality metrics."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {label}")
    print(f"{'='*60}")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Basic stats
    print("\n📊 Basic Stats:")
    print(f"  Total size: {len(text):,} chars")
    print(f"  Total lines: {len(text.splitlines()):,}")
    print(f"  Total words: {len(text.split()):,}")

    # Quality issues
    print("\n🔍 Quality Issues:")

    # Multiple spaces (TTS killer)
    multiple_spaces = len(re.findall(r" {2,}", text))
    print(f"  Multiple spaces: {multiple_spaces:,} instances")
    if multiple_spaces > 0:
        print("    ❌ BAD - Will cause TTS pauses")
        # Show example
        matches = list(re.finditer(r" {2,}", text))[:3]
        for match in matches:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end].replace("\n", "↵")
            print(f"       Example: ...{context}...")
    else:
        print("    ✅ GOOD - Clean spacing")

    # Weird unicode
    weird_chars = len(re.findall(r"[^\x00-\x7F]", text))
    print(
        f"  Non-ASCII chars: {weird_chars:,} ({weird_chars/len(text)*100:.2f}%)"
    )

    # PDF artifacts
    artifacts = [
        ("OceanofPDF.com", len(re.findall(r"OceanofPDF\.com", text))),
        ("Page numbers alone", len(re.findall(r"^\d+$", text, re.MULTILINE))),
        (
            "Header repetition",
            len(re.findall(r"^(.*)\n\1$", text, re.MULTILINE)),
        ),
    ]
    print("\n📄 PDF Artifacts:")
    for artifact_name, count in artifacts:
        print(f"  {artifact_name}: {count:,}")

    # Sentence structure
    print("\n📝 Sentence Structure:")
    sentences = re.split(r"[.!?]+\s+", text)
    avg_sentence_len = (
        sum(len(s.split()) for s in sentences) / len(sentences)
        if sentences
        else 0
    )
    print(f"  Avg sentence length: {avg_sentence_len:.1f} words")

    # Very short lines (possible extraction errors)
    lines = text.splitlines()
    short_lines = [l for l in lines if 0 < len(l.strip()) < 10]
    print(f"  Very short lines (<10 chars): {len(short_lines):,}")
    if len(short_lines) > 100:
        print("    ⚠️  Many short lines might indicate poor extraction")

    # Empty lines ratio
    empty_lines = sum(1 for l in lines if not l.strip())
    print(
        f"  Empty lines: {empty_lines:,} ({empty_lines/len(lines)*100:.1f}%)"
    )

    # Paragraph detection
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    print(f"  Paragraphs: {len(paragraphs):,}")
    avg_para_len = (
        sum(len(p.split()) for p in paragraphs) / len(paragraphs)
        if paragraphs
        else 0
    )
    print(f"  Avg paragraph length: {avg_para_len:.1f} words")

    return {
        "multiple_spaces": multiple_spaces,
        "weird_chars": weird_chars,
        "avg_sentence_len": avg_sentence_len,
        "short_lines": len(short_lines),
        "paragraphs": len(paragraphs),
    }


def compare_sample_pages(file1, file2):
    """Compare specific text samples."""
    print(f"\n{'='*60}")
    print("Sample Comparison (first 1000 chars)")
    print(f"{'='*60}")

    with open(file1, "r", encoding="utf-8") as f:
        text1 = f.read(1000)
    with open(file2, "r", encoding="utf-8") as f:
        text2 = f.read(1000)

    print("\n📄 TEST Output (first 500 chars):")
    print(f"{text1[:500]}")

    print("\n📄 ORCHESTRATOR Output (first 500 chars):")
    print(f"{text2[:500]}")

    # Check if they're identical
    if text1 == text2:
        print("\n✅ First 1000 chars are IDENTICAL")
    else:
        print("\n⚠️  First 1000 chars are DIFFERENT")
        # Find first difference
        for i, (c1, c2) in enumerate(zip(text1, text2)):
            if c1 != c2:
                print(f"   First difference at position {i}:")
                print(f"   TEST: '{text1[max(0,i-20):i+20]}'")
                print(f"   ORCH: '{text2[max(0,i-20):i+20]}'")
                break


def main():
    test_file = (
        PROJECT_ROOT
        / "phase2-extraction"
        / "extracted_text"
        / "Systematic Theology_TTS_READY.txt"
    )
    orch_file = (
        PROJECT_ROOT
        / "phase2-extraction"
        / "extracted_text"
        / "Systematic Theology.txt"
    )

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    if not orch_file.exists():
        print(f"❌ Orchestrator file not found: {orch_file}")
        return

    print("🔬 Diagnostic Analysis: Test vs Orchestrator Output")
    print(f"\nTest File: {test_file.name}")
    print(f"Orch File: {orch_file.name}")

    # Analyze both
    test_metrics = analyze_text_quality(test_file, "TEST OUTPUT (Quick Run)")
    orch_metrics = analyze_text_quality(
        orch_file, "ORCHESTRATOR OUTPUT (Hours Run)"
    )

    # Compare samples
    compare_sample_pages(test_file, orch_file)

    # Summary
    print(f"\n{'='*60}")
    print("🎯 DIAGNOSIS SUMMARY")
    print(f"{'='*60}")

    issues = []

    if orch_metrics["multiple_spaces"] > test_metrics["multiple_spaces"]:
        diff = (
            orch_metrics["multiple_spaces"] - test_metrics["multiple_spaces"]
        )
        issues.append(
            f"❌ Orchestrator has {diff:,} MORE multiple-space issues"
        )
        issues.append("   → This will cause bad TTS pauses!")

    if test_metrics["multiple_spaces"] > orch_metrics["multiple_spaces"]:
        diff = (
            test_metrics["multiple_spaces"] - orch_metrics["multiple_spaces"]
        )
        issues.append(f"❌ Test has {diff:,} MORE multiple-space issues")

    if abs(test_metrics["paragraphs"] - orch_metrics["paragraphs"]) > 100:
        issues.append(
            f"⚠️  Different paragraph counts: Test={test_metrics['paragraphs']}, Orch={orch_metrics['paragraphs']}"
        )

    if issues:
        print("\n🚨 Issues Found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ Both files seem similar in quality")

    print("\n💡 Recommendation:")
    if test_metrics["multiple_spaces"] < orch_metrics["multiple_spaces"]:
        print("  → Use TEST output (fewer spacing issues)")
        print(f"  → File: {test_file.name}")
    elif orch_metrics["multiple_spaces"] < test_metrics["multiple_spaces"]:
        print("  → Use ORCHESTRATOR output (fewer spacing issues)")
        print(f"  → File: {orch_file.name}")
    else:
        print("  → Both files have similar quality - use either")
        print(f"  → Prefer TEST output for consistency: {test_file.name}")


if __name__ == "__main__":
    main()
