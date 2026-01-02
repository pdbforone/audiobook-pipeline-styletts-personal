# Comprehensive Analysis of Data Duplication Artifacts in Document Extraction Pipelines

**Document Version:** 1.0
**Date:** 2026-01-01
**Research Source:** Gemini Deep Research
**Pipeline Context:** Audiobook Production (Phase 1: Validation → Phase 2: Extraction → Phase 3: Chunking → Phase 4: TTS)

---

## Executive Summary

This document provides an exhaustive technical analysis of text duplication bugs in multi-phase document processing pipelines, with specific focus on the "consecutive duplication" pattern where each text segment appears exactly twice (e.g., "Paragraph A. Paragraph A. Paragraph B. Paragraph B.").

**Key Finding from This Pipeline:** The duplication bug was traced to a **control flow fall-through error** in the Phase 2 TXT extractor's line-merging logic, not a retry mechanism or library-specific parsing issue. However, the broader research reveals multiple vectors through which such duplication can occur.

---

## 1. Systemic Anomalies in Multi-Phase Text Ingestion Architectures

### 1.1 The Operational Cost of Redundancy

Text duplication in a pipeline has cascading impacts:

- **TTS Cost Multiplication:** Character-based pricing (Amazon Polly, ElevenLabs) results in 2× operational costs
- **Vector Space Distortion:** Duplicate embeddings in RAG systems dilute retrieval quality
- **Audio Quality Degradation:** Consecutive repetition breaks prosodic flow and listener immersion
- **Storage Inefficiency:** Doubled storage requirements across all pipeline stages

### 1.2 Diagnostic Signature

The specific "A A B B" pattern (as opposed to "A B A B" or "[File][File]") is a critical diagnostic signal that isolates the pathology to **unit-of-processing level errors** rather than stream-level duplication.

---

## 2. Fundamental Mechanics of Python I/O and Stream Management

### 2.1 The "Ghost Read" and Buffer Misalignment

**Mechanism:**
- Python's `TextIOWrapper` employs internal buffering
- File pointer state can become desynchronized from buffer state
- Manual `seek(0)` operations may not reset buffered reads

**Symptom:** First chunk appears twice, but not entire file

**Probability for "A A B B" pattern:** Low (produces localized duplication, not systematic)

### 2.2 The Double-Iterator Anti-Pattern

**Code Pattern:**
```python
# Bug: Chaining tee'd iterators
iter1, iter2 = itertools.tee(file_stream)
combined = itertools.chain(iter1, iter2)  # Yields entire file twice
```

**Symptom:** [File Content][File Content]

**Probability for "A A B B" pattern:** Low (wrong duplication topology)

### 2.3 The "Readlines" Logic Trap

**Code Pattern:**
```python
lines = f.readlines()
for line in lines:
    for x in lines:  # Cartesian product!
        process(line, x)
```

**Symptom:** Explosive duplication (n² items)

**Probability:** Low (creates wrong pattern)

---

## 3. Resilience Engineering: The Retry Side-Effect Anomaly

### 3.1 The Mutable Append Hazard ⚠️ **HIGH PROBABILITY**

**The Toxic Pattern:**
```python
results = []  # DANGER: Mutable outer scope

@retry(stop=stop_after_attempt(2))
def unsafe_extraction(file_path):
    with open(file_path, 'r') as f:
        for line in f:
            processed = process_line(line)
            results.append(processed)  # Side effect!
```

**Failure Sequence:**
1. **Attempt 1:** Reads "Para A", appends → `['Para A']`; Reads "Para B", appends → `['Para A', 'Para B']`; **Error on Para C** → Exception
2. **Tenacity Retry:** Catches exception, re-executes function
3. **Attempt 2:** Re-opens file, reads "Para A", appends to **existing list** → `['Para A', 'Para B', 'Para A']`
4. **Result:** `['Para A', 'Para A', 'Para B', 'Para B', ...]`

**This produces the exact "A A B B" signature.**

### 3.2 Generator Re-entrancy and State

**Issue:** The `@retry` decorator wraps the function call (returns iterator object), not the iteration process itself. If a generator is converted to a list inside a retry block, the Mutable Append hazard applies.

**Probability:** Very High for pipelines using tenacity/retry

---

## 4. Hierarchical Parsing and Format-Specific Artifacts

### 4.1 AWS Textract: Layout vs. Line Duality

**Structure:**
```
LAYOUT_LIST (Text: "Item 1\nItem 2")
  ├─ CHILD: LINE (Text: "Item 1")
  └─ CHILD: LINE (Text: "Item 2")
```

**Naive Extraction:**
```python
for block in response['Blocks']:
    print(block['Text'])  # Prints parent AND children!
```

**Result:** `["Item 1\nItem 2", "Item 1", "Item 2"]` → Partial "A A" pattern

**Mitigation:**
```python
# Strict block filtering
for block in response['Blocks']:
    if block['BlockType'] == 'LINE':  # Ignore LAYOUT blocks
        print(block['Text'])
```

### 4.2 Unstructured Library: The `hi_res` Merge Conflict

**Mechanism:**
- Runs **Object Detection** (Detectron2/YOLOX) and **Text Extraction** (pdfminer) in parallel
- Attempts to merge using bounding box IOU
- **Failure:** If coordinates don't perfectly overlap, same text extracted twice

**Trigger:** PDFs with both text layer and visual layout (hybrid PDFs)

**Symptom:** Text appears as both "Inferred Element" and "Extracted Element"

### 4.3 LangChain Orchestration Issues

**Known Issue:** `SelfQueryRetriever` returns duplicate documents if vector store contains multiple matching chunks

**Relevance:** If Phase 2 conflates extraction with initial indexing/retrieval (common in RAG setups), retriever duplication manifests as duplicate text

---

## 5. Architectural Deep Dive: Phase 2 to Phase 3 Handoff

### 5.1 The Text Normalization Gap

**Sliding Window Extraction:**
- Window size: 500 tokens
- Stride: 250 tokens → 50% overlap
- **Bug:** Stride = 0 or fails to advance → 100% overlap = duplication

**Regex Recursion:**
```python
# Dangerous: Malformed regex can duplicate
text = re.sub(r'(\w+)', r'\1 \1', text)  # Doubles every word!
```

### 5.2 The "List Comprehension" Cartesian Product

**Buggy Pattern:**
```python
# Intended: Flatten
lines = [line for chunk in chunks for line in chunk]

# Buggy: Explicit duplication
lines = [line for line in raw_text for _ in range(2)]
```

**Symptom:** Systematic doubling of all content

---

## 6. Diagnostic Protocols and Debugging Strategy

### Protocol 1: The "Tee" Trace (Stream Verification)

**Implementation:**
```python
with open(file_path, 'r') as f:
    for line in f:
        print(f"Position before read: {f.tell()}")
        data = process(line)
```

**Expected:** Monotonically increasing position (0, 1024, 2048...)

**Bug Signal:** Position jumps backward (0, 1024, 0, 1024...) → Physical file re-read

### Protocol 2: The Identity Check (Object vs. Content)

```python
if id(item_1) == id(item_2):
    print("Reference Duplication - Same object appended twice")
else:
    print("Value Duplication - Data parsed/read twice")
```

**Reference Duplication:** Retry Side-Effect (appending same result object)

**Value Duplication:** Library double-parsing (Textract Layout vs. Line)

### Protocol 3: Library Isolation

Create minimal script bypassing pipeline:

```python
# Clean room test
from unstructured.partition.auto import partition
elements = partition(filename="test.txt")
print([e.text for e in elements])
```

**Result A:** Duplication persists → Library configuration issue

**Result B:** Duplication vanishes → Pipeline orchestration issue (Tenacity, Custom Classes)

---

## 7. Prevention and Architectural Remediation

### 7.1 Enforcing Functional Purity (Idempotency) ✅ **CRITICAL**

**Anti-Pattern:**
```python
def extract(file, results_list):
    # BAD: Modifies argument
    results_list.append(data)
```

**Best Practice:**
```python
def extract(file):
    # GOOD: Returns new data
    local_data_list = []
    # ... processing ...
    return local_data_list

# Integration
final_results = retry_function(file)
```

**Guarantee:** If retry occurs, failed attempt's local list is discarded; new attempt starts fresh

### 7.2 Strict Block Filtering (Textract/Unstructured)

```python
# Allow-list approach
for block in textract_response['Blocks']:
    if block['BlockType'] in ['LINE', 'WORD']:  # Explicit types only
        process(block['Text'])
    # Deny LAYOUT_LIST, LAYOUT_TEXT, PAGE
```

### 7.3 Stream Atomicity and Context Managers

**Anti-Pattern:**
```python
# Phase 1
f = open(file_path, 'r')
validate(f)

# Phase 2
extract(f)  # Handle in dirty state (cursor at EOF)!
```

**Best Practice:**
```python
# Pass file paths, not handles
def extract(file_path):
    with open(file_path, 'r') as f:  # Clean stream, auto-cleanup
        # ... processing ...
```

### 7.4 Semantic Deduplication (Defense in Depth)

```python
import hashlib

def dedupe_consecutive(iterable):
    """Remove adjacent duplicates using content hash."""
    prev_hash = None
    for item in iterable:
        curr_hash = hashlib.sha256(item.encode()).digest()
        if curr_hash != prev_hash:
            yield item
            prev_hash = curr_hash

# Usage: Sanitizes A A B B → A B
clean_text = list(dedupe_consecutive(extracted_paragraphs))
```

**Benefit:** Protects expensive downstream phases (Chunking, TTS) regardless of upstream cause

---

## 8. Case Study: This Pipeline's Actual Bug

### Root Cause Identified

**Location:** `phase2-extraction/src/phase2_extraction/extractors/txt.py:107-117`

**Bug Type:** Control Flow Fall-Through (Not retry side-effect!)

**Mechanism:**
```python
# Line ends with sentence-ending punctuation
if line_stripped and line_stripped[-1] in ".!?":
    buffer += " " + line_stripped  # (1) Add line to buffer
    if next_line_stripped and next_line_stripped[0].isupper():
        merged.append(buffer.strip())
        buffer = ""
        continue  # Only continues if NESTED if is true
    # (2) FALLS THROUGH if nested if is false!

# Default: merge with buffer
buffer += " " + line_stripped  # (3) Adds line AGAIN!
```

**Trigger Condition:** Line ends with `.!?` AND next line does NOT start with uppercase

**Fix:**
```python
if line_stripped and line_stripped[-1] in ".!?":
    buffer += " " + line_stripped
    if next_line_stripped and next_line_stripped[0].isupper():
        merged.append(buffer.strip())
        buffer = ""
    continue  # ← CRITICAL: Prevent fall-through
```

### Verification

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Input Size | 2374 bytes | 2374 bytes |
| Extracted Size | 4737 chars | 2368 chars |
| Duplication | Yes (2×) | No |
| First Sentence Count | 2 occurrences | 1 occurrence |

---

## 9. Probability Matrix: Root Cause Candidates

| Domain | Mechanism | "A A B B" Pattern Match | Probability | This Pipeline |
|--------|-----------|------------------------|-------------|---------------|
| **Control Flow** | Fall-through in conditional logic | ✅ Exact | **Very High** | ✅ **CONFIRMED** |
| **Retry Side-Effect** | Mutable list + @retry decorator | ✅ Exact | Very High | ❌ (No retry in txt.py) |
| **Library (Textract)** | LAYOUT vs LINE hierarchy | ⚠️ Partial | Medium | N/A (txt files) |
| **Library (Unstructured)** | hi_res merge conflict | ⚠️ Partial | Medium | N/A (txt files) |
| **Stream Management** | seek(0) + buffer misalignment | ❌ Wrong pattern | Low | ❌ |
| **Iterator Chaining** | itertools.chain(iter1, iter2) | ❌ Wrong pattern | Low | ❌ |
| **Regex Recursion** | Malformed substitution | ⚠️ Variable | Low | ❌ |

---

## 10. Key Takeaways

1. **"A A B B" signature → Unit-level processing error**, not stream-level
2. **Retry Side-Effect** is the most common cause in production pipelines using tenacity
3. **Control Flow Fall-Through** (this case) is subtle but devastating in custom parsers
4. **Library Hierarchy** issues (Textract, Unstructured) primarily affect PDFs, not plain text
5. **Defense in Depth:** Always implement `dedupe_consecutive()` before expensive phases

---

## 11. Recommended Audit Checklist

For any multi-phase extraction pipeline:

- [ ] **Search for `@retry` decorators** → Check if decorated functions modify outer-scope variables
- [ ] **Audit conditional blocks** → Ensure all branches have explicit `continue`/`return` to prevent fall-through
- [ ] **Verify stream handling** → Pass file paths, not open handles between phases
- [ ] **Library block filtering** → For Textract/Unstructured, explicitly filter block types
- [ ] **Implement deduplication** → Add `dedupe_consecutive()` as safety net before Phase 3
- [ ] **Add diagnostic logging** → Log file positions (`f.tell()`) and object IDs for duplicates
- [ ] **Isolation testing** → Test library extraction in clean room (bypass pipeline)

---

## 12. References

### Python I/O
- [io — Core tools for working with streams — Python 3.14.2 documentation](https://docs.python.org/3/library/io.html)
- [Iterating on a file doesn't work the second time - Stack Overflow](https://stackoverflow.com/questions/iterating-file-twice)

### Retry Mechanisms
- [Tenacity — Tenacity documentation](https://tenacity.readthedocs.io/)
- [retries not working in a generator context? #138 - GitHub](https://github.com/jd/tenacity/issues/138)

### Library-Specific
- [List contents are duplicated - Textract Issue #391](https://github.com/aws-samples/amazon-textract-textractor/issues/391)
- [unstructured/CHANGELOG.md - GitHub](https://github.com/Unstructured-IO/unstructured/blob/main/CHANGELOG.md)
- [returning duplicates while retrieving documents - LangChain Issue #17310](https://github.com/langchain-ai/langchain/issues/17310)

### Deduplication Patterns
- [How to remove adjacent duplicate elements - Stack Overflow](https://stackoverflow.com/questions/remove-adjacent-duplicates)
- [Building a Smart RAG System - DEV Community](https://dev.to/smart-rag-system)

---

**Document Status:** ✅ Bug Fixed and Committed
**Commit:** `aa568b9` - Fix critical text duplication bug in Phase 2 TXT extractor
**Branch:** `claude/improve-code-quality-i0HWl`
