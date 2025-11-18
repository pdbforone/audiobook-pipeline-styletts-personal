# Pipeline Architecture Decision: Structure Detection Strategy

## Problem Summary
You correctly identified that detecting document structure (chapters/sections) AFTER text extraction loses all formatting metadata (font sizes, styles, TOC).

## Constraints
1. **Multi-format support**: Phase 2 handles PDF, EPUB, MOBI, TXT
2. **Tool compatibility**: Phase 3 tools (spaCy, embeddings) work on plain text
3. **Timeout risk**: Phase 4 TTS can timeout on large chapters (>10k words)
4. **Processing time**: Phase 4 is slowest (~30s per chunk)

## Recommended Solution: **Hybrid Pragmatic Approach**

### Phase 2: Enhanced Extraction (Minimal Changes)
**Keep current plain text output** but add optional structure metadata:

```python
# Add to Phase 2 for PDFs only:
def extract_toc_if_available(pdf_path):
    """Extract PDF TOC - quick and reliable"""
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()  # Returns [(level, title, page), ...]
    return toc if toc else None

# Output structure:
{
  "extracted_text_path": "file.txt",  # Plain text (current)
  "toc": [...]  # NEW: Optional TOC if detected
}
```

**Why this works:**
- ✅ No breaking changes to Phase 2
- ✅ PDFs get free TOC extraction (fast, reliable)
- ✅ Other formats still work (no TOC = fallback to heuristics)
- ✅ Phase 3 tools still get plain text

---

### Phase 3: Intelligent Chunking (Main Work)
**Decision tree for chunk creation:**

```python
def create_chunks(text, toc=None):
    if toc:
        # Use TOC structure (best case)
        return create_chapter_chunks(text, toc, max_words=5000)
    else:
        # Heuristic detection fallback
        chapters = detect_chapters_heuristic(text)  # Roman numerals, etc.
        if chapters:
            return create_chapter_chunks(text, chapters, max_words=5000)
        else:
            # Last resort: fixed chunking
            return create_fixed_chunks(text, words_per_chunk=350)

def create_chapter_chunks(text, structure, max_words=5000):
    """
    Split text by chapters, but subdivide if chapter > max_words
    """
    chunks = []
    for chapter in structure:
        chapter_text = extract_chapter_text(text, chapter)
        word_count = len(chapter_text.split())
        
        if word_count <= max_words:
            # Chapter fits - use as-is
            chunks.append(chapter_text)
        else:
            # Chapter too big - split by sections or paragraphs
            sub_chunks = split_large_chapter(chapter_text, max_words)
            chunks.extend(sub_chunks)
    
    return chunks
```

**Why max_words=5000?**
- Phase 4 processes ~2-5s per 100 words
- 5000 words = ~3-4 minutes max (safe from 10min timeout)
- Phase 4’s internal splitter handles sentence boundaries within chunk

---

### Phase 4: Timeout Protection (Safety Net)
**Add validation at start of main():**

```python
# In main() after loading text:
word_count = len(text.split())
MAX_WORDS = 10000  # Hard limit

if word_count > MAX_WORDS:
    logger.error(f"Chunk rejected: {word_count} words exceeds {MAX_WORDS} limit")
    logger.error("Phase 3 must split this into smaller chunks")
    return 1

# Auto-enable splitting for medium chunks
if word_count > 500:
    logger.info(f"Auto-enabling text splitting for {word_count}-word chunk")
    enable_splitting = True
```

---

## Implementation Priority

### NOW (While Phase 4 Runs):
1. ✅ **Phase 4 already has `--enable-splitting` enabled** (orchestrator.py fixed)
2. ⏳ **Let current 109-chunk job finish** (monitor for timeouts)

### NEXT (After current job):
1. **Add Phase 4 safety checks** (10k word limit, auto-enable splitting)
2. **Test with one book** end-to-end

### LATER (Future enhancement):
1. **Add TOC extraction to Phase 2** (PDF only, ~10 lines of code)
2. **Upgrade Phase 3 to use TOC** when available
3. **Add heuristic chapter detection** for non-PDF formats

---

## Benefits of This Approach

✅ **No immediate breaking changes** - current job continues
✅ **Progressive enhancement** - add features incrementally
✅ **Format-agnostic** - works for PDF, EPUB, plain text
✅ **Timeout-safe** - hard limits prevent Phase 4 hangs
✅ **Natural structure** - uses actual chapters when available
✅ **Graceful degradation** - falls back to fixed chunking if needed

---

## Current Status
- **Phase 4**: Processing chunk 1/109 with `--enable-splitting` enabled
- **Expected**: Should complete successfully with clear audio
- **Monitor**: Watch for any timeout warnings in logs
