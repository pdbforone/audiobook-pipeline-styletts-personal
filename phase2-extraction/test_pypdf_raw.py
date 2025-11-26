#!/usr/bin/env python3
"""
Test pypdf extraction directly to see what it produces.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PdfReader = pytest.importorskip("pypdf", reason="pypdf not available").PdfReader

pdf_path = PROJECT_ROOT / "input" / "Systematic Theology.pdf"

print("?? Testing pypdf Raw Output")
print("=" * 60)

# Extract with pypdf
reader = PdfReader(str(pdf_path))
text = []
for i, page in enumerate(reader.pages[:3]):  # First 3 pages only
    page_text = page.extract_text()
    text.append(page_text)

    if i == 0:  # Analyze first page
        print("\n?? First Page Analysis:")
        print(f"   Length: {len(page_text)} chars")
        print(f"   Tabs: {page_text.count(chr(9))}")
        print(f"   Spaces: {page_text.count(' ')}")
        print(f"   Lines: {len(page_text.splitlines())}")

        # Show first 500 chars with visible whitespace
        print("\n   First 500 chars (tabs=[TAB], spaces=�):")
        sample = page_text[:500]
        visible = (
            sample.replace("\t", "[TAB]")
            .replace(" ", "�")
            .replace("\n", "?\n")
        )
        print(f"   {visible}")

full_text = "\n".join(text)

print("\n?? First 3 Pages Combined:")
print(f"   Total length: {len(full_text)} chars")
print(f"   Total tabs: {full_text.count(chr(9))}")
print(f"   Total spaces: {full_text.count(' ')}")

# Compare to File 2 (the good one)
file2 = (
    PROJECT_ROOT
    / "phase2-extraction"
    / "extracted_text"
    / "Systematic Theology_TTS_READY.txt"
)
with open(file2, "r", encoding="utf-8") as f:
    good_text = f.read()

good_first_500 = good_text[:500]
pypdf_first_500 = full_text[:500]

print("\n?? Comparison (First 500 chars):")
print("\npypdf output:")
print(f"   {pypdf_first_500[:200]}")

print("\nGood file (TTS_READY):")
print(f"   {good_first_500[:200]}")

if "OVER 250,000" in good_first_500 and "OVER 250,000" not in pypdf_first_500:
    print("\n??  PROBLEM FOUND!")
    print("   pypdf is missing the title page!")
    print("   Good file has: 'OVER 250,000 CoPiES IN Print'")
    print(f"   pypdf starts with: '{pypdf_first_500[:50]}...'")
    print("\n?? The 'good' file was extracted with a DIFFERENT method!")
elif "About Systematic Theology" in pypdf_first_500:
    print("\n? pypdf output matches File 1")
    print("   The 'good' file must have been extracted differently")
