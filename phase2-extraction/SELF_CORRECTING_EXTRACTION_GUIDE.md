# Self-Correcting Extraction - Complete Guide

## Philosophy: "Work Harder, Check Your Work, Correct Mistakes"

For TTS audiobooks, **extraction quality is critical**. Even tiny errors cause hallucinations. 
This document explains three levels of self-correcting extraction.

---

## Level 1: Multi-Pass Extraction (Fast, ~30s overhead)

**File:** `multi_pass_extractor.py`

**How it works:**
1. Extract with ALL available methods (pypdf, pdfplumber, PyMuPDF, unstructured)
2. Validate each result with TTS-grade quality checks
3. Compare results and choose the best one
4. Return confidence score

**Usage:**
```bash
python multi_pass_extractor.py "Systematic Theology.pdf"
```

**When to use:**
- Default approach for all files
- Fast enough for regular use
- Catches 90% of extraction problems

**Example output:**
```
EXTRACTION COMPARISON
================================================================================
👑 pypdf            | Score: 0.95 | Length: 1,234,567 | Issues: 0
   pdfplumber       | Score: 0.72 | Length: 1,200,000 | Issues: 2
     - Low punctuation: 3.2/100 words
     - High non-ASCII ratio: 18.5%
   pymupdf          | Score: 0.45 | Length: 50,123 | Issues: 5
     - 234 replacement characters
     - Only 3/10 common words

Cross-method similarity: 89.3%
Best method: pypdf (score: 0.95)

✅ EXCELLENT QUALITY (confidence: 0.85)
```

---

## Level 2: Consensus Voting (Thorough, ~2-5min overhead)

**File:** `consensus_extractor.py`

**How it works:**
1. Extract **page-by-page** with multiple methods
2. For each page, compare all methods
3. Choose best extraction per page (consensus voting)
4. Identify problematic pages
5. OCR fallback for failed pages

**Usage:**
```bash
python consensus_extractor.py "Systematic Theology.pdf" 0.8
```

**When to use:**
- Important books where quality is critical
- When multi-pass shows inconsistent results
- Books with mixed content (text + scanned sections)

**Benefits:**
- Detects which specific pages have problems
- Can mix methods (pypdf for page 1, pdfplumber for page 2, etc.)
- OCR fallback for truly unreadable pages
- Shows exactly where quality drops

**Example output:**
```
CONSENSUS EXTRACTION: Systematic Theology.pdf
Pages: 1234 | Methods: pypdf, pdfplumber, pymupdf
================================================================================

  Page 1: OK (confidence: 0.95) via pypdf
  Page 2: OK (confidence: 0.93) via pypdf
  ...
  Page 47: LOW (confidence: 0.65) via pdfplumber
  Page 48: FAILED (confidence: 0.25)
  ...
  Processed 1234/1234 pages...

EXTRACTION COMPLETE
================================================================================
Status: partial_success
Average confidence: 0.87
Low confidence pages: 23
  Pages: 47, 89, 123, 456...
Failed pages: 5
  Pages: 48, 234, 789...

Attempting OCR fallback for failed pages...
  OCR processing page 48...
    ✓ Extracted 432 chars
  OCR processing page 234...
    ✓ Extracted 567 chars
```

---

## Level 3: Integration with Phase 2 Pipeline

To integrate self-correction into your existing `extraction.py`:

### Option A: Replace extraction logic (Recommended)

In `extraction.py`, replace the extraction section (around line 180) with:

```python
# Import the self-correcting extractor
from multi_pass_extractor import extract_with_self_correction

# In main() function, replace the extraction loop:
if classification == "text" or classification == "mixed":
    # Use multi-pass self-correcting extraction
    logger.info("Using multi-pass self-correcting extraction...")
    text, extraction_metadata = extract_with_self_correction(
        file_path,
        min_confidence=0.7  # Adjust threshold as needed
    )
    tool_used = extraction_metadata["method_used"]
    
    # Add multi-pass metadata to errors
    if extraction_metadata["issues"]:
        errors.extend(extraction_metadata["issues"])
    
    # Log detailed results
    logger.info(f"Multi-pass results:")
    logger.info(f"  Confidence: {extraction_metadata['confidence']:.2f}")
    logger.info(f"  Methods tried: {', '.join(extraction_metadata['methods_tried'])}")
    logger.info(f"  Quality score: {extraction_metadata['quality_score']:.2f}")
    
    if extraction_metadata["status"] == "failed":
        # Try consensus voting as fallback
        logger.warning("Multi-pass failed, trying consensus voting...")
        from consensus_extractor import extract_with_consensus
        text, consensus_metadata = extract_with_consensus(file_path, min_confidence=0.6)
        tool_used = "consensus_voting"
        errors.append(f"Fallback to consensus voting due to quality issues")
```

### Option B: Add as config option

In `config.yaml`:
```yaml
extraction_mode: "multi_pass"  # Options: "simple", "multi_pass", "consensus"
min_confidence: 0.7
enable_ocr_fallback: true
```

Then in `extraction.py`:
```python
if config.extraction_mode == "multi_pass":
    from multi_pass_extractor import extract_with_self_correction
    text, metadata = extract_with_self_correction(file_path, config.min_confidence)
    tool_used = f"multi_pass_{metadata['method_used']}"
    
elif config.extraction_mode == "consensus":
    from consensus_extractor import extract_with_consensus
    text, metadata = extract_with_consensus(
        file_path,
        min_confidence=config.min_confidence,
        use_ocr_fallback=config.enable_ocr_fallback
    )
    tool_used = "consensus_voting"
    
else:  # simple mode - existing extraction
    text = extract_text_pypdf(file_path) or \
           extract_text_pdfplumber(file_path) or \
           extract_text_pymupdf(file_path)
    tool_used = "simple"
```

---

## Comparison: Which Method to Use?

| Feature | Simple | Multi-Pass | Consensus |
|---------|--------|------------|-----------|
| Speed | ⚡ Fast (5-10s) | 🔄 Medium (30-60s) | 🐌 Slow (2-5min) |
| Quality | ⚠️ Varies | ✅ High | 🏆 Excellent |
| Error Detection | ❌ None | ✅ Good | 🏆 Page-level |
| Auto-Correction | ❌ No | ⚠️ Method selection | ✅ Per-page + OCR |
| CPU Usage | Low | Medium | High |
| Best For | Quick tests | Production | Critical books |

**Recommendation:**
- **Development/Testing:** Multi-Pass (good balance)
- **Production Pipeline:** Multi-Pass with Consensus fallback
- **Critical Books:** Consensus from the start

---

## Testing the Extractors

### Test Multi-Pass:
```bash
cd phase2-extraction
python multi_pass_extractor.py "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\input\Systematic Theology.pdf"
```

### Test Consensus:
```bash
python consensus_extractor.py "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\input\Systematic Theology.pdf" 0.8
```

### Compare Methods:
```bash
# Create comparison script
python - <<'EOF'
import sys
sys.path.append('.')
from multi_pass_extractor import extract_with_self_correction
from consensus_extractor import extract_with_consensus
from pathlib import Path

pdf = "C:/Users/myson/Pipeline/audiobook-pipeline-chatterbox/input/Systematic Theology.pdf"

print("Testing Multi-Pass...")
text1, meta1 = extract_with_self_correction(pdf)

print("\nTesting Consensus...")
text2, meta2 = extract_with_consensus(pdf, use_ocr_fallback=False)

print("\n" + "="*80)
print("COMPARISON")
print("="*80)
print(f"Multi-Pass:  Confidence: {meta1['confidence']:.2%} | Length: {len(text1):,}")
print(f"Consensus:   Confidence: {meta2['confidence']:.2%} | Length: {len(text2):,}")
print(f"\nText similarity: {len(set(text1.split()) & set(text2.split())) / len(set(text1.split())):.1%}")
EOF
```

---

## What to Expect

### Good PDF (clean text):
```
Multi-Pass:  ✅ Confidence 95% | All methods agree | 5 seconds
Consensus:   ✅ Confidence 97% | 0 failed pages | 90 seconds
→ Use Multi-Pass (fast, good enough)
```

### Problematic PDF (font issues):
```
Multi-Pass:  ⚠️ Confidence 65% | Methods disagree | pypdf best but marginal
Consensus:   ✅ Confidence 85% | 23 low-conf pages, 5 OCR'd | 180 seconds
→ Use Consensus (worth the time for quality)
```

### Mixed PDF (text + scans):
```
Multi-Pass:  ❌ Confidence 30% | All methods struggle
Consensus:   ⚠️ Confidence 70% | 300 pages OCR'd | 600 seconds
→ Use Consensus with OCR (only option)
```

---

## Next Steps

1. **Test on Systematic Theology:**
   ```bash
   python multi_pass_extractor.py "input/Systematic Theology.pdf"
   ```

2. **If multi-pass fails (confidence < 70%):**
   ```bash
   python consensus_extractor.py "input/Systematic Theology.pdf" 0.7
   ```

3. **Compare with existing extraction:**
   ```bash
   # Compare the _extracted.txt with the existing Systematic Theology.txt
   # See which is better quality
   ```

4. **Integrate into Phase 2:**
   - Update `extraction.py` with multi-pass as default
   - Add consensus as fallback for failed extractions
   - Update `config.yaml` with extraction_mode option

5. **Update Phase 6 orchestrator:**
   - Add `--extraction-mode` flag
   - Add `--min-confidence` flag
   - Show confidence scores in progress output

---

## Configuration Recommendations

### For Most Books (config.yaml):
```yaml
extraction_mode: "multi_pass"
min_confidence: 0.75
gibberish_threshold: 0.2
retry_limit: 0  # Multi-pass handles retries
```

### For Critical Books:
```yaml
extraction_mode: "consensus"
min_confidence: 0.85
enable_ocr_fallback: true
```

### For Speed (Development):
```yaml
extraction_mode: "simple"
min_confidence: 0.6
```

---

## Benefits Summary

✅ **Catches extraction errors automatically**
✅ **No manual intervention needed**
✅ **Provides confidence scores**
✅ **Identifies problematic pages**
✅ **OCR fallback for unreadable sections**
✅ **Prevents TTS hallucinations**
✅ **Follows "quality over speed" principle**
✅ **CPU-only (no GPU required)**

The extractors "work harder" by trying multiple methods, "check their work" by validating quality, and "correct mistakes" by choosing the best result or using OCR fallback.
