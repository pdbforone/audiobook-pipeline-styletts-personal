# TTS-Grade Extraction Updates for extraction.py

This document shows what needs to be added to extraction.py for TTS-grade quality.

## 1. Add TTS-specific quality checks after line ~140 (after detect_language function)

```python
def check_tts_quality(text: str) -> Dict:
    """
    Strict TTS-grade quality checks.
    Returns dict with status and issues found.
    """
    issues = []
    warnings = []
    
    # Sample for analysis
    sample = text[:20000] if len(text) > 20000 else text
    sample_words = sample.split()
    sample_word_count = len(sample_words)
    
    # 1. Zero tolerance for encoding errors
    replacement_chars = text.count('�')
    if replacement_chars > 0:
        issues.append(f"CRITICAL: {replacement_chars} replacement characters (encoding error)")
    
    # 2. Check for private use area (font mapping errors)
    private_use = sum(1 for c in text if 0xE000 <= ord(c) <= 0xF8FF)
    if private_use > 0:
        issues.append(f"CRITICAL: {private_use} private use characters (font mapping failed)")
    
    # 3. Character distribution
    alpha_ratio = sum(1 for c in sample if c.isalpha()) / len(sample)
    if alpha_ratio < 0.65:
        issues.append(f"CRITICAL: Low alphabetic ratio {alpha_ratio:.1%} (need 65%+)")
    
    non_ascii_ratio = sum(1 for c in sample if ord(c) > 127) / len(sample)
    if non_ascii_ratio > 0.15:
        issues.append(f"CRITICAL: High non-ASCII ratio {non_ascii_ratio:.1%} (max 15%)")
    elif non_ascii_ratio > 0.05:
        warnings.append(f"Moderate non-ASCII ratio {non_ascii_ratio:.1%}")
    
    # 4. Common English words (must have most of these)
    text_lower = sample.lower()
    common_words = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'that', 'for', 'it']
    found_common = sum(1 for word in common_words if f' {word} ' in text_lower)
    if found_common < 8:
        issues.append(f"CRITICAL: Only {found_common}/10 common English words found")
    
    # 5. Punctuation density (critical for TTS prosody)
    periods = sample.count('.')
    commas = sample.count(',')
    questions = sample.count('?')
    exclamations = sample.count('!')
    total_punct = periods + commas + questions + exclamations
    
    punct_per_100 = (total_punct / sample_word_count * 100) if sample_word_count else 0
    if punct_per_100 < 5:
        issues.append(f"CRITICAL: Low punctuation density {punct_per_100:.1f}/100 words (need 5+)")
    elif punct_per_100 < 10:
        warnings.append(f"Below-average punctuation {punct_per_100:.1f}/100 words")
    
    # 6. Sentence structure
    import re
    sentences = [s.strip() for s in re.split(r'[.!?]+', sample) if s.strip()]
    if len(sentences) < 10:
        issues.append(f"CRITICAL: Only {len(sentences)} sentences in sample")
    else:
        avg_sent_len = sample_word_count / len(sentences)
        if avg_sent_len > 50:
            warnings.append(f"Long sentences (avg {avg_sent_len:.1f} words)")
    
    # 7. TTS-breaking characters
    problem_chars = ['□', '■', '●', '◆', '▯']
    for char in problem_chars:
        count = text.count(char)
        if count > 0:
            issues.append(f"CRITICAL: {count}x '{char}' (TTS-breaking character)")
    
    # Determine overall status
    if issues:
        status = "failed"
    elif warnings:
        status = "partial_success"
    else:
        status = "success"
    
    return {
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "metrics": {
            "alpha_ratio": alpha_ratio,
            "non_ascii_ratio": non_ascii_ratio,
            "punct_per_100": punct_per_100,
            "common_words_found": found_common,
            "replacement_chars": replacement_chars,
            "private_use_chars": private_use
        }
    }
```

## 2. Update main() function around line 200 (after text extraction succeeds)

Replace this section:
```python
else:
    gibberish_score = evaluate_gibberish(text)
    if gibberish_score < config.gibberish_threshold:
        errors.append(f"Gibberish score low: {gibberish_score}; potential retry")
    
    perplexity = evaluate_perplexity(text)
    lang_info = detect_language(text)
    ...
```

With:
```python
else:
    # Run all quality checks
    gibberish_score = evaluate_gibberish(text)
    perplexity = evaluate_perplexity(text)
    lang_info = detect_language(text)
    tts_quality = check_tts_quality(text)
    
    # TTS-grade quality thresholds (STRICT)
    if gibberish_score > 0.2:  # Was 0.5, now stricter
        errors.append(f"HIGH GIBBERISH: {gibberish_score:.3f} (TTS threshold: 0.2)")
    
    if perplexity < config.perplexity_threshold:
        errors.append(f"Low perplexity: {perplexity:.3f}")
    
    if lang_info["language"] != "en" or lang_info["confidence"] < 0.95:  # Was 0.9, now stricter
        errors.append(f"Language issue: {lang_info}")
    
    # Add TTS-specific issues
    if tts_quality["issues"]:
        errors.extend(tts_quality["issues"])
    if tts_quality["warnings"]:
        errors.extend([f"WARNING: {w}" for w in tts_quality["warnings"]])
    
    # Override status based on TTS quality
    if tts_quality["status"] == "failed":
        status = "failed"
        errors.append("FAILED TTS-GRADE QUALITY CHECKS - Will cause hallucinations")
    elif tts_quality["status"] == "partial_success" and not errors:
        status = "partial_success"
    
    # Calculate yield
    file_size = os.path.getsize(file_path)
    yield_pct = len(text) / file_size * 100 if file_size else 0.0
    
    # Update status logic - MUCH STRICTER
    if status != "failed":  # Only update if not already failed
        if yield_pct > 98 and perplexity > config.perplexity_threshold and \
           gibberish_score <= 0.2 and not errors:
            status = "success"
        else:
            status = "partial_success"
    
    # Save extracted text
    extracted_path = str(Path(config.extracted_dir) / f"{config.file_id}.txt")
    with open(extracted_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    # Log TTS quality details
    logger.info(f"TTS Quality Check:")
    logger.info(f"  Replacement chars: {tts_quality['metrics']['replacement_chars']}")
    logger.info(f"  Private use chars: {tts_quality['metrics']['private_use_chars']}")
    logger.info(f"  Alphabetic ratio: {tts_quality['metrics']['alpha_ratio']:.1%}")
    logger.info(f"  Non-ASCII ratio: {tts_quality['metrics']['non_ascii_ratio']:.1%}")
    logger.info(f"  Punctuation/100 words: {tts_quality['metrics']['punct_per_100']:.1f}")
    logger.info(f"  Common words: {tts_quality['metrics']['common_words_found']}/10")
    
    if status == "failed":
        logger.error("❌ FAILED TTS-GRADE CHECKS - Text will cause TTS hallucinations")
        logger.error("Issues:")
        for issue in tts_quality["issues"]:
            logger.error(f"  - {issue}")
```

## 3. Update ExtractionRecord model (around line 60) to include TTS metrics

```python
class ExtractionRecord(BaseModel):
    extracted_text_path: str
    tool_used: str
    yield_pct: float
    gibberish_score: float
    perplexity: float
    language: str
    lang_confidence: float
    status: str  # success, partial_success, failed
    errors: List[str] = Field(default_factory=list)
    timestamps: Dict[str, float]
    structure: Optional[List[Dict]] = None
    
    # NEW: TTS-grade metrics
    tts_metrics: Optional[Dict] = None  # Add this line
```

## 4. Update config.yaml with stricter thresholds

```yaml
# Phase 2 TTS-Grade Extraction Config
retry_limit: 1
gibberish_threshold: 0.2  # STRICT - was 0.5
perplexity_threshold: 0.92
lang_confidence: 0.95  # STRICT - was 0.9
extract_structure: true
```

## Summary of Changes

1. **Added `check_tts_quality()` function** with 7 critical checks
2. **Updated quality thresholds** to be much stricter:
   - Gibberish: 0.2 (was 0.5)
   - Lang confidence: 0.95 (was 0.9)
3. **Added zero-tolerance checks** for:
   - Replacement characters (�)
   - Private use area characters
   - TTS-breaking symbols (□■●◆▯)
4. **Added punctuation density check** (critical for TTS prosody)
5. **Added character distribution checks** (alpha ratio, non-ASCII ratio)
6. **Added common words verification** (must have 8/10 most common English words)
7. **Updated status logic** to fail on any critical TTS issue

## Next Steps

1. Run `python TTS_QUALITY_STANDARDS.py` to see all thresholds
2. Apply these changes to extraction.py (or I can create a complete patched version)
3. Re-extract Systematic Theology with the strict checks
4. Only proceed to Phase 3 if extraction passes all TTS-grade checks
