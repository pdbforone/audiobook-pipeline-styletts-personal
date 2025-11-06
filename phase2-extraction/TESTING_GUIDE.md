# 🧪 Phase 2 Extraction Testing Guide

## Why Test Extraction Accuracy?

For TTS audiobooks, **extraction accuracy is critical**:
- ❌ Missing text = incomplete audiobook
- ❌ Wrong text = TTS reads incorrect content
- ❌ Garbled text = TTS hallucinates/mispronounces
- ✅ Accurate text = High-quality audiobook

We need to **verify** that what we extract matches what's in the PDF.

---

## 🛠️ Testing Tools Created

### 1. **compare_pdf_to_extracted.py** - Interactive Comparison
**Purpose:** Side-by-side verification of PDF vs extracted text

**Features:**
- Compare beginning, middle, end sections
- Compare specific pages
- Search for text in both files
- Visual verification (human review)

**Usage:**
```bash
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction
python compare_pdf_to_extracted.py
```

**Menu:**
```
1. Compare Beginning (Page 1)
2. Compare Middle
3. Compare End (Last Page)
4. Compare Specific Page
5. Search for Text in Both
6. Quick Overview (All Sections)
7. Exit
```

**Example Session:**
```
Select option (1-7): 1

📄 PDF Page 1 (first 1000 chars):
--------------------------------------------------------------------------------
OVER 250,000 COPIES IN PRINT
SYSTEMATIC THEOLOGY
An Introduction to Biblical Doctrine
WAYNE GRUDEM
...

📝 EXTRACTED (first 1000 chars):
--------------------------------------------------------------------------------
OceanofPDF.com
About Systematic Theology
The Christian church has a long tradition of systematic theology...
```

**What to Check:**
- ✅ Same words appear in both?
- ✅ Spelling correct?
- ✅ Spacing normal?
- ✅ No missing sections?

---

### 2. **test_extraction_accuracy.py** - Method Comparison
**Purpose:** Test which extraction method is most accurate

**Features:**
- Tests pypdf, pdfplumber, pymupdf on same pages
- Shows length, quality score for each
- Recommends best method

**Usage:**
```bash
python test_extraction_accuracy.py
```

**Test Options:**
1. **Quick test** - Beginning, middle, end pages
2. **Custom pages** - Specify which pages to test
3. **First 10 pages** - Thorough sample

**Example Output:**
```
PAGE 1
================================================================================

Extracting with pypdf...
  Length: 1,523 chars
  Quality: 0.85
  Preview: SYSTEMATIC THEOLOGY An Introduction to Biblical Doctrine...

Extracting with pdfplumber...
  Length: 1,234 chars
  Quality: 0.65
  Preview: SYSTEMATIC THEOLOGY     An Introduction     to Biblical...

Extracting with pymupdf...
  Length: 1,456 chars
  Quality: 0.70
  Preview: SYSTEMATIC THEOLOGY An Intro duction to Biblical...

SUMMARY
================================================================================

pypdf:
  Success rate: 3/3
  Avg length: 1,520 chars
  Avg quality: 0.87

RECOMMENDATION
================================================================================

✅ RECOMMENDED: pypdf (best quality & length)
```

---

## 🎯 Testing Workflow

### Step 1: Test Extraction Methods (5 minutes)
```bash
python test_extraction_accuracy.py
```

**Choose Option 1 (Quick test)**

This tests beginning, middle, end pages with all available methods.

**Look for:**
- Which method has highest quality score?
- Which method extracts most text?
- Do they produce similar or different results?

**Decision:**
- If pypdf wins → Use pypdf (already configured)
- If another wins → Update Phase 2 to prioritize that method

---

### Step 2: Verify Accuracy (10 minutes)
```bash
python compare_pdf_to_extracted.py
```

**Select which extracted file:**
1. Existing extraction
2. Multi-pass extraction

**Then test:**

**A. Beginning (Option 1):**
- Does extracted text match PDF page 1?
- Is title/author correct?
- Any missing content?

**B. Middle (Option 2):**
- Does middle section look reasonable?
- Text coherent?
- No weird spacing?

**C. End (Option 3):**
- Does it reach the end of the book?
- Last sentences match?
- Not truncated?

**D. Search Test (Option 5):**
Search for a distinctive phrase like "systematic theology":
- Found in both? ✅ Good
- Only in PDF? ❌ Extraction missed it
- Only in extracted? ❌ Hallucination

---

### Step 3: Spot Check Key Sections (5 minutes)

**Option 4: Compare Specific Page**

Test pages you care about:
- Page 100 (random middle section)
- Page 500 (another spot check)
- Table of Contents page
- Index page (if exists)

**What to look for:**
- Text matches between PDF and extracted
- No replacement characters (�)
- Spacing is normal
- Punctuation preserved

---

## 🔍 Common Issues & What They Mean

### Issue 1: Multi-Space Everywhere
```
"The     Christian       church"
```

**Cause:** PDF uses custom spacing, extractor preserves it

**Fix:** TTS normalization (already in tts_normalizer.py)

**Impact:** Medium - causes awkward TTS pauses

---

### Issue 2: Missing Sections
```
PDF has 5 paragraphs, extracted has 2
```

**Cause:** Extraction method failed on those paragraphs

**Fix:** Try different extraction method

**Impact:** CRITICAL - incomplete audiobook

---

### Issue 3: Wrong Words
```
PDF: "theology"
Extracted: "the0logy" or "theo1ogy"
```

**Cause:** OCR or font mapping error

**Fix:** Use different extraction method, or it's a bad PDF scan

**Impact:** HIGH - TTS will mispronounce

---

### Issue 4: Garbled Text
```
PDF: "Introduction to Theology"
Extracted: "▯▯▯▯▯▯▯▯ to ▯▯▯▯▯▯▯"
```

**Cause:** Custom fonts, no character mapping

**Fix:** PDF is problematic, may need OCR or manual extraction

**Impact:** CRITICAL - TTS unusable

---

### Issue 5: Missing Punctuation
```
PDF: "theology. The study of God"
Extracted: "theology The study of God"
```

**Cause:** Extraction method lost punctuation

**Fix:** Try different method, or normalize with best-effort punctuation

**Impact:** MEDIUM - affects TTS prosody

---

## 📊 Quality Checklist

Use this checklist after testing:

**Completeness:**
- [ ] Beginning matches
- [ ] Middle section reasonable
- [ ] Ending matches (not truncated)
- [ ] Searched text found in both

**Accuracy:**
- [ ] Words spelled correctly
- [ ] No replacement characters (�)
- [ ] Punctuation preserved
- [ ] Spacing reasonable

**Quality:**
- [ ] Common English words present
- [ ] Sentences make sense
- [ ] No obvious garbling
- [ ] Readability is good

**TTS-Ready:**
- [ ] No multi-spacing issues (or will normalize)
- [ ] Punctuation density adequate
- [ ] No artifacts (URLs, headers)
- [ ] Length matches expected (~98% of PDF size)

---

## 🎯 Decision Matrix

After testing, use this to decide:

### ✅ All Checks Pass
→ **Proceed to Phase 3**
→ Use the extraction with highest quality score

### ⚠️ Minor Issues (spacing, artifacts)
→ **Apply TTS normalization**
→ Use `normalize_now.py`
→ Then proceed to Phase 3

### ❌ Major Issues (missing text, garbled)
→ **Try different extraction method**
→ Test with `test_extraction_accuracy.py`
→ Use method with highest quality

### ❌ All Methods Fail
→ **PDF might be:**
   - Encrypted/protected
   - Scanned (needs OCR)
   - Corrupted
→ Check PDF in Adobe Reader
→ Consider OCR extraction
→ May need manual extraction

---

## 💡 Pro Tips

**1. Test Before Full Extraction**
Don't extract the entire 1200-page book without testing first.
Test 3-5 pages, verify quality, THEN extract all.

**2. Trust Your Eyes**
Quality scores are helpful, but **visual inspection is critical**.
If text looks wrong, it probably is.

**3. Search for Distinctive Phrases**
Don't just compare first page. Search for phrases from middle/end:
- "chapter 10"
- Distinctive words from middle of book
- Last sentence of book

**4. Check Page Count Math**
If PDF has 1200 pages and extraction only has content for ~200 pages worth,
something is wrong (truncation or massive text loss).

**5. Multi-Method Consensus**
If 2+ methods produce similar results, they're probably correct.
If one method produces very different text, it's probably wrong.

---

## 🚀 Quick Start

**Just run these two commands:**

```bash
# Test which method is best
python test_extraction_accuracy.py
# Choose option 1 (Quick test)

# Verify accuracy visually
python compare_pdf_to_extracted.py
# Choose option 6 (Quick Overview)
```

**Total time: ~5 minutes**
**Confidence: Know your extraction is accurate before Phase 3**

---

## 📝 What to Report

After testing, you should know:

1. **Which extraction method wins:** pypdf, pdfplumber, or pymupdf
2. **Quality score:** 0.0-1.0 (aim for >0.8)
3. **Issues found:** Missing text, garbled sections, spacing problems
4. **Recommendation:** Proceed / Normalize / Re-extract / Manual review

**Example:**
```
Tested: Systematic Theology.pdf
Winner: pypdf (quality: 0.87)
Issues: Multi-spacing (fixable with normalization)
Recommendation: Normalize then proceed to Phase 3
```

---

## Next Steps After Testing

**If tests pass:**
1. Run `normalize_now.py` to clean text
2. Proceed to Phase 3 (Chunking)
3. Update extraction.py to use winning method

**If tests fail:**
1. Check PDF in Adobe Reader
2. Try different extraction parameters
3. Consider OCR for scanned PDFs
4. Report findings for troubleshooting
