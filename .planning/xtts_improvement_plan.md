# XTTS v2 Improvement Plan: Post-Coqui Era Hardening

**Created:** 2025-12-25
**Based on:** Deep Research - "The Post-Coqui Era" Technical Audit

---

## Executive Summary

Coqui AI shut down in December 2024, leaving XTTS v2 as "legacyware" requiring defensive engineering. This plan implements the verified community fixes and optimizations from the research to maximize reliability for our audiobook pipeline.

**Key Insight:** Kokoro-82M (Apache 2.0, 82M params) is now the superior choice for most use cases. XTTS v2 should only be used when zero-shot voice cloning is required.

---

## Phase 1: Critical XTTS Fixes (High Priority)

### 1.1 The Underscore Trick - Hallucination Prevention
**Problem:** GPT-2 backbone fails to predict EOS token, causing gibberish/breathing at sentence end
**Fix:** Append `_` to input text before synthesis

```python
# xtts_engine.py - _synthesize_single_segment()
# BEFORE tokenization
synthesis_text = text.rstrip()
if not synthesis_text.endswith('_'):
    synthesis_text = synthesis_text + '_'
```

**Impact:** Eliminates end-of-sentence hallucinations
**Risk:** Low - simple text manipulation
**Files:** `phase4_tts/engines/xtts_engine.py`

---

### 1.2 Optimized Repetition + Length Penalties
**Problem:** Current `repetition_penalty=10.0` is too aggressive, causing terse/hallucinated output
**Fix:** Use research-verified sweet spot: `repetition_penalty=2.0-5.0` with `length_penalty=1.2`

```python
# Current (too aggressive)
repetition_penalty=10.0,
length_penalty=1.0,

# Recommended
repetition_penalty=3.5,   # Sweet spot for audiobooks
length_penalty=1.2,       # Encourages longer, natural sequences
```

**Impact:** More natural prosody, fewer terse cutoffs
**Risk:** Medium - may need per-voice tuning
**Files:** `phase4_tts/engines/xtts_engine.py`

---

### 1.3 Deterministic Seed Management
**Problem:** XTTS is non-deterministic - same text produces different audio each time
**Fix:** Set all random seeds before EVERY inference call

```python
import torch
import numpy as np
import random

def _set_synthesis_seed(self, seed: int = 42):
    """Ensure deterministic synthesis for consistent pronunciation."""
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
```

**Impact:** Consistent pronunciation (no "Cave" → "Cavave" variations)
**Risk:** Low - pure improvement
**Files:** `phase4_tts/engines/xtts_engine.py`

---

### 1.4 Memory Leak Prevention
**Problem:** CUDA context corruption and memory leaks in long runs
**Fix:** Explicit garbage collection + cache clearing between batches

```python
import gc
import torch

def _cleanup_synthesis_memory(self):
    """Prevent VRAM creep during long audiobook generation."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
```

**Call after:** Every N chunks (e.g., every 50 chunks or every 10 minutes of audio)
**Impact:** Prevents crashes in 10+ hour audiobook runs
**Risk:** Low - adds minor latency
**Files:** `phase4_tts/engines/xtts_engine.py`, `phase4_tts/src/main_multi_engine.py`

---

## Phase 2: Text Preprocessing Enhancement (Medium Priority)

### 2.1 Number Expansion with num2words
**Problem:** Neural models read "1995" as "one nine nine five" instead of "nineteen ninety-five"
**Fix:** Integrate `num2words` library for proper number verbalization

```python
from num2words import num2words
import re

def expand_numbers(text: str, language: str = "en") -> str:
    """Convert digits to words for proper TTS pronunciation."""
    # Handle years (1900-2099)
    text = re.sub(r'\b(19|20)\d{2}\b', lambda m: num2words(int(m.group()), to='year'), text)
    # Handle ordinals (1st, 2nd, 3rd)
    text = re.sub(r'\b(\d+)(st|nd|rd|th)\b', lambda m: num2words(int(m.group(1)), to='ordinal'), text)
    # Handle cardinals
    text = re.sub(r'\b\d+\b', lambda m: num2words(int(m.group())), text)
    return text
```

**Impact:** Proper pronunciation of dates, numbers, ordinals
**Risk:** Low - text-level change
**Files:** `agents/llama_pre_validator.py`, new utility module

---

### 2.2 Enhanced Punctuation Normalization
**Problem:** Em-dashes (—), semicolons, and complex punctuation cause long pauses/hallucinations
**Fix:** Normalize to TTS-friendly alternatives

```python
def normalize_punctuation_for_tts(text: str) -> str:
    """Convert hostile punctuation to TTS-friendly alternatives."""
    # Em-dash → comma (preserves pause, prevents hallucination)
    text = re.sub(r'[—–]', ', ', text)
    # Semicolon → period (stronger boundary)
    text = text.replace(';', '.')
    # Ellipsis → period
    text = re.sub(r'\.{2,}', '.', text)
    # Multiple exclamation/question → single
    text = re.sub(r'[!?]{2,}', lambda m: m.group()[0], text)
    return text
```

**Impact:** Fewer mid-sentence artifacts
**Risk:** Low - already partially implemented
**Files:** `agents/llama_pre_validator.py`

---

### 2.3 Strict 250-Character Chunking Validation
**Problem:** "250 char limit" is heuristic for ~400 token GPT-2 context window
**Fix:** Validate segments stay under limit, add token counting

```python
XTTS_SAFE_CHARS = 220      # Current (good)
XTTS_ABSOLUTE_MAX = 250    # Research-verified safe limit

def validate_segment_length(segment: str) -> bool:
    """Ensure segment won't hit GPT-2 context ceiling."""
    # Character check (fast)
    if len(segment) > XTTS_ABSOLUTE_MAX:
        return False
    # Optional: actual token count check
    # token_count = len(tokenizer.encode(segment))
    # return token_count < 400
    return True
```

**Impact:** Prevents truncation from context overflow
**Risk:** Low - validation layer
**Files:** `phase4_tts/engines/xtts_engine.py`

---

## Phase 3: Audiobook Consistency (Medium Priority)

### 3.1 Voice Consistency via Master Reference
**Problem:** Speaker drift across 500+ segments in long books
**Fix:** Use single high-quality "Master Reference" (6-10s) for all segments

```python
class AudiobookSession:
    """Maintains voice consistency across long synthesis runs."""

    def __init__(self, master_reference_path: Path):
        self.master_reference = master_reference_path
        self.gpt_cond_latent = None
        self.speaker_embedding = None

    def precompute_speaker(self, engine: XTTSEngine):
        """Compute speaker embedding once, reuse for all chunks."""
        # Extract conditioning from master reference
        self.gpt_cond_latent, self.speaker_embedding = \
            engine.extract_speaker_embedding(self.master_reference)
```

**Impact:** Consistent voice across entire audiobook
**Risk:** Medium - requires session management
**Files:** `phase4_tts/engines/xtts_engine.py`, `phase4_tts/src/main_multi_engine.py`

---

### 3.2 Context-Aware Prosody (Warm Start)
**Problem:** Each sentence starts with reset prosody, sounds choppy
**Fix:** Feed previous sentence text as context hint (where model supports it)

```python
def synthesize_with_context(
    self,
    text: str,
    previous_text: Optional[str] = None,
    **kwargs
) -> np.ndarray:
    """Synthesize with awareness of previous sentence for prosody continuity."""
    # XTTS doesn't natively support text context, but we can:
    # 1. Use consistent speaker embedding (Phase 3.1)
    # 2. Maintain similar temperature/speed across segments
    # 3. Avoid abrupt parameter changes mid-book
    pass
```

**Impact:** Smoother transitions, more natural flow
**Risk:** Medium - experimental feature
**Files:** `phase4_tts/engines/xtts_engine.py`

---

## Phase 4: Kokoro Optimization (Strategic)

### 4.1 Kokoro as Primary Engine for Non-Cloning
**Rationale:**
- Apache 2.0 (vs CPML license issues with defunct Coqui)
- 5.7x smaller (82M vs 467M params)
- 2-3x faster on CPU
- <1GB VRAM (vs 4-8GB for XTTS)

**Strategy:**
1. Default to Kokoro for all pre-defined voices
2. Only use XTTS when custom voice cloning is required
3. Consider XTTS as "fallback for cloning" rather than primary engine

```yaml
# config.yaml update
engine_selection:
  default: kokoro
  voice_cloning: xtts
  fallback_order: [kokoro, xtts]
```

**Impact:** Faster, more reliable synthesis for majority of use cases
**Risk:** Low - Kokoro already integrated
**Files:** `phase4_tts/config.yaml`, `phase4_tts/src/main_multi_engine.py`

---

### 4.2 Kokoro G2P Quality Assurance
**Problem:** Kokoro depends on espeak-ng for G2P - quality capped by phonemization
**Fix:** Pre-validate G2P output, flag problematic words

```python
def validate_g2p_output(text: str, phonemes: str) -> List[str]:
    """Check for G2P conversion issues before synthesis."""
    issues = []
    # Check for unknown phoneme markers
    if '?' in phonemes or '<unk>' in phonemes:
        issues.append(f"Unknown phoneme in: {text[:50]}")
    # Check for suspicious length ratio
    if len(phonemes) < len(text) * 0.3:
        issues.append(f"Phoneme output suspiciously short")
    return issues
```

**Impact:** Catches pronunciation issues before synthesis
**Risk:** Low - validation only
**Files:** `phase4_tts/engines/kokoro_engine.py`

---

## Phase 5: Infrastructure Hardening (Low Priority)

### 5.1 Process Recycling for Batch Jobs
**Problem:** CUDA context corruption in long multiprocessing runs
**Fix:** Use `maxtasksperchild=1` for batch processing

```python
from multiprocessing import Pool

def batch_synthesize_with_recycling(chunks: List[str]):
    """Recycle worker processes to prevent CUDA memory corruption."""
    with Pool(processes=1, maxtasksperchild=1) as pool:
        results = pool.map(synthesize_chunk, chunks)
    return results
```

**Impact:** Prevents crashes in very long runs
**Risk:** Low - adds startup overhead
**Files:** `phase4_tts/src/main_multi_engine.py`

---

### 5.2 Silent Start Buffer
**Problem:** First 100-300ms of streaming output may be silent/garbled
**Fix:** Add audio priming buffer before first chunk

```python
AUDIO_PRIME_MS = 200  # Silence buffer

def get_audio_prime(sample_rate: int) -> np.ndarray:
    """Generate silence buffer to prime audio output."""
    samples = int(sample_rate * AUDIO_PRIME_MS / 1000)
    return np.zeros(samples, dtype=np.float32)
```

**Impact:** Cleaner audio start for streaming applications
**Risk:** Low - applies to streaming use case only
**Files:** `phase4_tts/engines/xtts_engine.py`

---

## Implementation Order

| Priority | Phase | Items | Est. Effort | Impact |
|----------|-------|-------|-------------|--------|
| 🔴 CRITICAL | 1.1 | Underscore trick | 1 hour | High |
| 🔴 CRITICAL | 1.2 | Repetition/length penalties | 1 hour | High |
| 🔴 CRITICAL | 1.3 | Seed management | 1 hour | High |
| 🟡 HIGH | 1.4 | Memory leak prevention | 2 hours | High |
| 🟡 HIGH | 2.1 | num2words integration | 2 hours | Medium |
| 🟡 HIGH | 2.2 | Punctuation normalization | 1 hour | Medium |
| 🟢 MEDIUM | 3.1 | Master reference session | 3 hours | Medium |
| 🟢 MEDIUM | 4.1 | Kokoro as default engine | 2 hours | High |
| 🔵 LOW | 2.3 | Token count validation | 1 hour | Low |
| 🔵 LOW | 4.2 | Kokoro G2P validation | 2 hours | Low |
| 🔵 LOW | 5.1 | Process recycling | 2 hours | Low |
| 🔵 LOW | 5.2 | Silent start buffer | 1 hour | Low |

---

## Dependencies to Add

```txt
# requirements.txt additions
num2words>=0.5.12      # Number verbalization
```

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| End-of-sentence hallucinations | ~5% | <0.5% | ASR validation |
| Pronunciation consistency | Variable | Deterministic | Seed-based testing |
| Memory stability (10hr run) | Crashes | Stable | Long-run testing |
| Default engine speed (CPU) | 3.2 RTF | 1.3 RTF | Switch to Kokoro |

---

## Key Quotes from Research

> "The 'Underscore Trick': Appending a simple underscore (_) to the end of the input text string has been empirically proven to 'smarten up' the model."

> "For long-form content, a repetition_penalty in the range of 2.0 - 5.0 is recommended. Crucially, this must be balanced with a length_penalty greater than 1.0 (e.g., 1.2)."

> "XTTS v2 is non-deterministic by default... the random seed must be fixed globally before every inference call."

> "Kokoro-82M signals a definitive 'Small Model' inversion in audio synthesis... For 90% of commercial applications—where zero-shot cloning is not strictly required—Kokoro-82M is the superior choice."

---

## Next Steps

1. Implement Phase 1 (Critical Fixes) immediately
2. Add num2words to dependencies
3. Update engine selection to prefer Kokoro
4. Create test suite for hallucination detection
5. Document voice cloning workflow with XTTS as specialized tool
