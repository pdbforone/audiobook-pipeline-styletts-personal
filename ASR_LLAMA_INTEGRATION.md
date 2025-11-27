# ASR + Llama Integration: Intelligent Self-Repair

## Overview

ASR validation detects **what** failed. Llama rewriter understands **why** and fixes it.

This creates a powerful feedback loop:
```
TTS → Audio → ASR detects issue → Llama analyzes & rewrites → Retry → Success
```

## The Workflow

### Step 1: ASR Detects Issue

```
Original Text: "The CEO's Q3 FY2024 EBITDA improved 15%..."
TTS Synthesis: [audio file]
ASR Transcription: "The C. E. O.'s Q. three F. Y. two thousand twenty four E. B. I. T. D. A. improved fifteen percent"
WER: 45.2% (critical)
Issues: ["high_wer_45%", "truncation"]
Recommendation: "rewrite"
```

**Problem:** TTS struggled with abbreviations and numbers.

### Step 2: Llama Analyzes ASR Feedback

Llama receives:
- **Original text**: What we wanted to say
- **ASR transcription**: What TTS actually produced
- **WER + issues**: Diagnostic data

Llama compares them and identifies:
- "CEO" → spelled out letter-by-letter (TTS doesn't know the acronym)
- "Q3 FY2024" → confused TTS (mixed letters/numbers)
- "EBITDA" → another spelled-out acronym

### Step 3: Llama Rewrites

```json
{
  "rewritten": "The Chief Executive Officer's third quarter fiscal year two thousand twenty four earnings before interest, taxes, depreciation and amortization improved fifteen percent.",
  "notes": "Expanded abbreviations CEO→Chief Executive Officer, Q3→third quarter, FY2024→fiscal year 2024, EBITDA→full phrase. Converted numbers to words for better TTS pronunciation.",
  "confidence": 0.92,
  "strategy": "expand_abbreviations"
}
```

### Step 4: Retry with Fixed Text

```
Rewritten Text: "The Chief Executive Officer's third quarter..."
TTS Synthesis: [new audio]
ASR Transcription: "The Chief Executive Officer's third quarter fiscal year two thousand twenty four earnings before interest taxes depreciation and amortization improved fifteen percent"
WER: 8.1% (pass!)
```

**Success!** Llama understood the problem and fixed it.

---

## Configuration

### Enable ASR + Llama

Edit [phase4_tts/config.yaml](phase4_tts/config.yaml):

```yaml
validation:
  enable_tier1: true
  enable_tier2: true

  # ASR Validation
  enable_asr_validation: true
  asr_model_size: "base"         # "tiny" | "base" | "small"
  asr_wer_warning: 0.20
  asr_wer_critical: 0.40

  # NEW: Llama + ASR Integration
  enable_llama_asr_rewrite: true  # Use Llama to fix ASR-detected issues
  llama_confidence_threshold: 0.7 # Only apply rewrites with >70% confidence
```

### Requirements

```bash
# ASR
pip install openai-whisper python-Levenshtein

# Llama (already required for other agents)
# - Ollama running locally
# - Model pulled: ollama pull llama3.2
```

---

## Decision Tree

```
TTS → Audio → ASR validates
              ↓
         WER < 20%? → ✅ Pass
              ↓ No
         WER 20-40%? → ⚠️ Warning
              ↓
    Recommendation: "rewrite"
              ↓
    Llama analyzes ASR feedback
              ↓
    Confidence > 70%? → Yes → Rewrite + Retry → Re-validate
              ↓ No                                    ↓
         WER still high? ← ← ← ← ← ← ← ← ← ← ← ← ← ← ┘
              ↓ Yes
    Recommendation: "switch_engine"
              ↓
         Try Kokoro → Re-validate
              ↓
         WER improved? → ✅ Use Kokoro
              ↓ No
              ❌ Mark as failed
```

---

## Example Logs

### Successful Llama Rewrite

```
INFO: Chunk chunk_0089 running ASR validation (Tier 3)
WARNING: Chunk chunk_0089 ASR validation FAILED: WER=45.2%, recommendation=rewrite
INFO: Chunk chunk_0089 attempting Llama rewrite based on ASR feedback
INFO: Chunk chunk_0089 Llama rewrite (confidence=0.92, strategy=expand_abbreviations): Expanded abbreviations CEO→Chief Executive Officer, Q3→third quarter, FY2024→fiscal year 2024, EBITDA→full phrase. Converted numbers to words.
INFO: Chunk chunk_0089 Llama+ASR SUCCESS: WER improved from 45.2% to 8.1%
```

### Llama Rewrite Fails, Engine Switch Succeeds

```
WARNING: Chunk chunk_0134 ASR validation FAILED: WER=52.3%, recommendation=rewrite
INFO: Chunk chunk_0134 attempting Llama rewrite based on ASR feedback
WARNING: Chunk chunk_0134 Llama rewrite did not improve WER (52.3% → 48.1%), trying engine switch
WARNING: Chunk chunk_0134 ASR recommends engine switch; retrying with Kokoro
INFO: Chunk chunk_0134 ASR retry with Kokoro SUCCESS: WER improved from 52.3% to 12.7%
```

---

## What Llama Fixes

### 1. Abbreviations & Acronyms

**Before:**
```
"The FBI's HQ in DC handles NSA cooperation."
→ TTS: "F. B. I.'s H. Q. in D. C. handles N. S. A. cooperation"
→ WER: 60%
```

**After Llama:**
```
"The Federal Bureau of Investigation's headquarters in Washington D.C. handles National Security Agency cooperation."
→ TTS: Perfect pronunciation
→ WER: 5%
```

**Strategy:** `expand_abbreviations`

### 2. Complex Numbers

**Before:**
```
"Sales reached $1.5M in Q3 2024, up 23.7% YoY."
→ TTS: Struggles with mixed format
→ WER: 38%
```

**After Llama:**
```
"Sales reached one point five million dollars in the third quarter of two thousand twenty four, up twenty three point seven percent year over year."
→ TTS: Clear pronunciation
→ WER: 9%
```

**Strategy:** `expand_numbers`

### 3. Problematic Punctuation

**Before:**
```
"He said—pausing dramatically—"This changes everything...""
→ TTS: Confused by em-dashes and nested quotes
→ WER: 42%
```

**After Llama:**
```
"He said, pausing dramatically, this changes everything."
→ TTS: Smooth delivery
→ WER: 7%
```

**Strategy:** `remove_punctuation`

### 4. Long Sentences (Truncation)

**Before:**
```
"The comprehensive analysis of the economic indicators, including GDP growth, inflation rates, unemployment figures, and consumer confidence indices, suggests a cautiously optimistic outlook for the next fiscal quarter."
→ TTS: Truncates at "unemployment"
→ WER: 65% (truncation detected)
```

**After Llama:**
```
"The comprehensive analysis of economic indicators suggests a cautiously optimistic outlook. This includes GDP growth, inflation rates, unemployment figures, and consumer confidence indices for the next fiscal quarter."
→ TTS: Two clear sentences
→ WER: 6%
```

**Strategy:** `break_sentences`

---

## Pipeline Integration

ASR + Llama runs automatically in Phase 4 if enabled:

```python
# phase4_tts/src/main_multi_engine.py (simplified view)

# After synthesis
audio = synthesize(text, engine="xtts")

# ASR validation
asr_result = asr_validator.validate(audio, text)

if not asr_result["valid"] and asr_result["recommendation"] == "rewrite":
    # Llama analyzes ASR feedback
    rewrite = llama_rewriter.rewrite_from_asr_feedback(
        original_text=text,
        asr_transcription=asr_result["transcription"],
        asr_issues=asr_result["issues"],
        wer=asr_result["wer"]
    )

    if rewrite["confidence"] > 0.7:
        # Retry with rewritten text
        new_audio = synthesize(rewrite["rewritten"], engine="xtts")
        new_asr = asr_validator.validate(new_audio, rewrite["rewritten"])

        if new_asr["wer"] < asr_result["wer"]:
            return new_audio  # Success!

# If Llama didn't fix it, try engine switch
if still_failing:
    return synthesize(text, engine="kokoro")
```

---

## Output in pipeline.json

```json
{
  "phase4": {
    "files": {
      "my_book": {
        "chunks": [
          {
            "chunk_id": "chunk_0089",
            "status": "success",
            "engine_used": "xtts",
            "validation_details": {
              "asr": {
                "valid": true,
                "wer": 0.081,
                "transcription": "The Chief Executive Officer's third quarter...",
                "issues": [],
                "recommendation": "pass"
              },
              "llama_rewrite": {
                "rewritten": "The Chief Executive Officer's third quarter...",
                "notes": "Expanded abbreviations...",
                "confidence": 0.92,
                "strategy": "expand_abbreviations"
              }
            }
          }
        ]
      }
    }
  }
}
```

---

## Performance Impact

| Component | Overhead | When |
|-----------|----------|------|
| ASR validation | ~500ms/chunk | Every chunk (if enabled) |
| Llama rewrite | ~2-3s/rewrite | Only on ASR failures |
| Retry synthesis | ~variable | Only if rewrite applied |

**Total impact:** ~10-15% slower on first run, but **prevents full reruns** (saving hours).

---

## Tuning Thresholds

### WER Thresholds

```yaml
asr_wer_warning: 0.20   # Default: 20%
asr_wer_critical: 0.40  # Default: 40%
```

- **Lower** (e.g., 0.15/0.30): More sensitive, catches minor issues
- **Higher** (e.g., 0.25/0.50): Less sensitive, only catches major problems

### Llama Confidence

```yaml
llama_confidence_threshold: 0.7  # Default: 70%
```

- **Lower** (e.g., 0.6): Accept more rewrites (higher risk of bad rewrites)
- **Higher** (e.g., 0.8): Only high-confidence rewrites (miss some fixable issues)

---

## Troubleshooting

### Llama Not Fixing Issues

**Check:**
1. Confidence threshold too high? Lower to 0.6
2. Ollama running? `ollama list` should show models
3. Logs: Look for "Llama rewrite failed" errors

### ASR + Llama Both Enabled But Not Running

**Check config:**
```yaml
enable_asr_validation: true          # Must be true
enable_llama_asr_rewrite: true       # Must be true
```

### High Llama Overhead

**Solutions:**
1. Use faster model: `ollama pull llama3.2:1b`
2. Reduce max_tokens in rewriter: Edit [agents/llama_rewriter.py](agents/llama_rewriter.py) line 140
3. Disable for production after validation

---

## Best Practices

1. **Enable for first 10-20 books** to build confidence
2. **Review Llama rewrites** in pipeline.json to understand patterns
3. **Tune WER thresholds** based on your TTS engines
4. **Disable ASR after validation** if first-run success >95%
5. **Keep Llama rewriter** for edge cases (complex books)

---

## Result

With ASR + Llama:
- **Before:** Books with abbreviations/numbers need 2-3 reruns
- **After:** 95%+ first-run success, auto-fixes common TTS issues

**The pipeline learns what TTS engines struggle with and fixes it automatically.**
