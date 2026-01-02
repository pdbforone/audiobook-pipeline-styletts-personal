# Gemini Deep Research Prompt: TTS Validation Failures & Audio Quality Issues

## Research Objective

Investigate the root causes of TTS validation failures in audiobook synthesis pipelines, with focus on `duration_mismatch`, `too_quiet`, and `silence_gap` errors. Provide actionable strategies for prevention, detection, and mitigation.

---

## Context: Our Pipeline

### Architecture
- **Phase 4 (TTS)**: Kokoro-ONNX (primary), XTTS (fallback)
- **Validation**: 3-tier system (Tier 1: amplitude/duration, Tier 2: prosody, Tier 3: ASR/WER)
- **Chunking**: LLM-based semantic chunking (typical chunk: 800-1500 chars)
- **Quality Target**: Audiobook-grade synthesis (natural prosody, consistent pacing)

### Current Issues (From Production Logs)

**Recent Validation Failure Pattern:**
```
Kokoro synthesis: 15 chunks
├─ 13 chunks pass validation ✅
└─ 2 chunks fail validation ❌
    └─ chunk_0010: duration_mismatch (expected 45.2s, got 52.8s)
    └─ chunk_0011: duration_mismatch (expected 48.1s, got 55.3s)
```

**Failure Types Observed:**
1. `duration_mismatch`: Synthesized audio significantly longer/shorter than expected
2. `too_quiet`: Peak amplitude below -30dB threshold
3. `silence_gap`: Extended silent periods within speech

**Engine-Specific Patterns:**
- Kokoro: Occasional duration_mismatch on chunks with dialogue or complex punctuation
- XTTS: Higher rate of too_quiet failures, especially with cloned voices

---

## Research Questions

### Primary Questions

1. **What causes duration mismatches in TTS synthesis?**
   - Why would synthesized audio duration deviate significantly from text-based estimates?
   - Are certain text patterns (dialogue, abbreviations, numbers) more prone to this?
   - How do different TTS engines (neural vs. parametric) handle timing prediction?
   - What's the expected tolerance range for audiobook-grade TTS?

2. **What causes amplitude/silence issues in neural TTS?**
   - Why would synthesis produce audio below acceptable volume thresholds?
   - What text patterns trigger extended silence gaps?
   - Are there known bugs in Kokoro-ONNX or XTTS related to silence handling?
   - How do punctuation marks (em-dash, ellipsis, semicolon) affect synthesis pausing?

3. **How can we better predict problematic chunks BEFORE synthesis?**
   - Are there text features that correlate with validation failures?
   - Can we use pre-synthesis analysis to avoid bad chunks?
   - What NLP techniques detect "TTS-unfriendly" text patterns?

### Secondary Questions

4. **What are industry best practices for TTS validation?**
   - How do commercial audiobook platforms (Audible, Librivox) validate TTS?
   - What metrics beyond amplitude/duration should we check?
   - Are there standardized quality thresholds for audiobook TTS?

5. **How can we improve our duration estimation?**
   - Current method: `chars_per_minute` (default: 900 CPM for Kokoro, 850 for XTTS)
   - Are there more accurate methods (phoneme counting, prosody models)?
   - Should duration estimates vary by text type (narrative vs. dialogue)?

6. **What text preprocessing reduces validation failures?**
   - Should we normalize punctuation before synthesis?
   - How should we handle special cases: abbreviations, numbers, contractions?
   - Are there "TTS safety" normalization strategies?

---

## Specific Technical Areas to Investigate

### 1. Kokoro-ONNX Specific

**Known Context:**
- Engine: StyleTTS2-based, ONNX runtime
- License: Apache 2.0
- Voices: 5 built-in voices (af_bella, af_sarah, bf_emma, am_adam, bm_george)
- Typical RT factor: 0.8-1.2x on CPU

**Research Focus:**
- Duration prediction accuracy in StyleTTS2 architecture
- Known issues with Kokoro alignment model (we already suppress verbose warnings)
- Optimal text preprocessing for Kokoro
- Punctuation handling differences vs. other TTS engines

### 2. XTTS Specific

**Known Context:**
- Engine: Coqui XTTS (post-Coqui era, community maintained)
- Current hardening: Underscore trick, repetition_penalty=3.5, segment-level synthesis
- Voices: Built-in speakers (claribel_dervla, gracie_wise, etc.) + cloning support

**Research Focus:**
- Why XTTS produces quieter audio than Kokoro (observed pattern)
- Duration prediction in zero-shot cloning scenarios
- Optimal segment length (<220 chars) - is this supported by research?
- Known issues with XTTS silence generation

### 3. Validation Methodology

**Current Tier 1 Validation:**
```python
# Amplitude check
peak_amplitude = np.max(np.abs(audio))
if peak_db < -30:  # Too quiet
    return ValidationResult(is_valid=False, reason="too_quiet")

# Duration check
expected_duration = (text_len / chars_per_minute) * 60
tolerance = 0.25  # 25% tolerance
if abs(actual_duration - expected_duration) / expected_duration > tolerance:
    return ValidationResult(is_valid=False, reason="duration_mismatch")

# Silence gap check
silent_frames = detect_long_silence(audio, threshold=-40dB, min_duration=2.0s)
if silent_frames:
    return ValidationResult(is_valid=False, reason="silence_gap")
```

**Research Focus:**
- Are these thresholds appropriate for audiobook TTS?
- Should tolerance vary by chunk length or text type?
- Are there better silence detection algorithms?
- Should we validate prosody/pitch continuity between chunks?

---

## Real-World Examples from Our Pipeline

### Example 1: duration_mismatch (chunk_0010)

**Text (excerpt):**
```
"Wait—what do you mean?" Sarah asked. "I thought we agreed on Tuesday."

"No, no," he replied, shaking his head. "I said *next* Tuesday, not this Tuesday."
```

**Metadata:**
- Text length: 142 chars
- Expected duration: ~9.5 seconds (900 CPM)
- Actual duration: 11.8 seconds (+24% over estimate)
- Failure: PASS (within 25% tolerance)

**Note:** This chunk actually PASSED. Need to find actual failure examples.

### Example 2: too_quiet

**Hypothesis:**
- Text with many commas/pauses causes TTS to reduce volume
- Certain phoneme sequences trigger quiet synthesis
- Engine-specific voice calibration issues

**Need to Research:**
- Volume normalization strategies in TTS
- Should we post-process audio to ensure consistent LUFS?
- Is this a voice-specific issue (some voices naturally quieter)?

---

## Deliverables Requested

### 1. Comprehensive Analysis Report

**Sections:**
1. **Root Causes of TTS Validation Failures** (ranked by frequency/impact)
   - Duration mismatch mechanisms
   - Amplitude/silence issue mechanisms
   - Text pattern correlations

2. **Prevention Strategies** (pre-synthesis)
   - Text preprocessing best practices
   - Problematic pattern detection
   - Improved duration estimation methods

3. **Detection Improvements** (validation enhancements)
   - Industry-standard quality metrics
   - Optimal threshold values (with research citations)
   - Multi-modal validation approaches

4. **Mitigation Strategies** (post-failure)
   - Text rewriting techniques for failed chunks
   - Engine-specific workarounds
   - Fallback decision trees

### 2. Actionable Recommendations

**Format:**
- **Priority 1 (High Impact, Low Effort)**: Quick wins we can implement immediately
- **Priority 2 (High Impact, Medium Effort)**: Significant improvements requiring development
- **Priority 3 (Research/Experimental)**: Novel approaches to explore

**Include:**
- Specific code changes (e.g., "Change duration tolerance from 25% to X% based on Y research")
- Configuration tweaks (e.g., "Set chars_per_minute to X for dialogue, Y for narrative")
- New validation checks to add

### 3. Research-Backed Thresholds

**Provide specific values with citations:**
- Amplitude threshold for "too_quiet" (currently -30dB)
- Duration mismatch tolerance (currently 25%)
- Silence gap threshold (currently 2.0s at -40dB)
- Optimal chars_per_minute by engine and text type

---

## Known Constraints & Context

### What We've Already Tried

✅ **XTTS Post-Coqui Hardening:**
- Underscore trick (append `_` to fix EOS prediction)
- Segment-level synthesis (<220 chars)
- Optimized penalties (repetition_penalty=3.5, length_penalty=1.2)

✅ **Smart Retry Logic:**
- Selective chunk retry (only retry failed chunks, not all)
- Built-in voice mapping for fallback
- Validation-aware failure detection

✅ **Text Preprocessing:**
- Phase 2 deduplication safety net
- Normalization pipeline (unicode, quotes, whitespace)

### What We Need to Explore

❌ **Pre-synthesis Text Analysis:**
- Detecting "TTS-unfriable" patterns before synthesis
- Dynamic chars_per_minute based on text features

❌ **Enhanced Validation:**
- Prosody continuity checks between chunks
- Spectral quality metrics
- ASR-based validation (Tier 3 exists but needs tuning)

❌ **Engine Selection Intelligence:**
- When to prefer Kokoro vs XTTS based on text pattern
- Voice selection based on content type

---

## Output Format Preferences

1. **Executive Summary** (1-2 pages)
   - Key findings
   - Top 5 actionable recommendations

2. **Detailed Technical Analysis** (10-20 pages)
   - Research findings with citations
   - Comparison of approaches
   - Industry best practices

3. **Implementation Roadmap** (1 page)
   - Priority 1, 2, 3 recommendations
   - Estimated effort/impact matrix

4. **References & Further Reading**
   - Academic papers
   - Industry blog posts
   - GitHub issues/discussions from TTS projects

---

## Success Criteria

This research will be successful if it helps us:

1. **Reduce validation failure rate** from current ~13% (2/15 chunks) to <5%
2. **Improve duration estimation accuracy** to reduce false positives
3. **Identify pre-synthesis detection** methods to prevent bad chunks
4. **Establish research-backed quality thresholds** for our validation tiers

---

## Additional Context Files (Optional)

If Gemini can access our codebase, these files provide implementation context:

- `phase4_tts/src/validation.py` - Current validation implementation
- `phase4_tts/src/main_multi_engine.py` - TTS synthesis logic
- `RETRY_LOGIC_IMPROVEMENTS.md` - Recent fixes to retry behavior
- `DUPLICATION_BUG_FIX_SUMMARY.md` - Text preprocessing improvements

---

## Timeline

**Ideal Research Depth:** Deep Research mode (comprehensive analysis)
**Expected Deliverable:** Within 24-48 hours
**Format:** Markdown document for integration into our docs/ folder

---

## Final Notes

We're building a **craft-focused, quality-first audiobook pipeline**. Speed is secondary to quality. We prefer:

- **Over-validation** rather than under-validation
- **Conservative thresholds** that catch issues early
- **Research-backed decisions** over heuristics
- **Explainable failures** that guide text rewriting

This research will inform the next generation of our validation and quality assurance systems.

---

**Prepared by:** Claude Sonnet 4.5 (Claude Code)
**Date:** 2026-01-02
**Repository:** audiobook-pipeline-styletts-personal
**Branch:** claude/improve-code-quality-i0HWl
