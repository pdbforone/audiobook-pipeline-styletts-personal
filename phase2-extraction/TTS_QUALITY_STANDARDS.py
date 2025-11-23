"""
TTS-GRADE QUALITY THRESHOLDS for Phase 2 Extraction

These stricter thresholds prevent extraction errors that cause TTS hallucinations.
Update your extraction.py or config.yaml with these values:
"""

EXTRACTION_CONFIG_TTS_GRADE = {
    # Gibberish Detection - STRICT
    "gibberish_threshold": 0.2,  # Was 0.5 - now much stricter
    # Anything above 0.2 likely has encoding errors
    # Perplexity (vocabulary diversity) - STRICT
    "perplexity_threshold": 0.92,  # Keep this - good measure
    # Language Confidence - STRICT
    "lang_confidence": 0.95,  # Was 0.9 - now stricter
    # NEW: Encoding Error Tolerance - ZERO
    "max_replacement_chars": 0,  # Zero tolerance for � characters
    "max_private_use_chars": 0,  # Zero tolerance for font mapping errors
    # NEW: Punctuation Density - REQUIRED FOR TTS
    "min_punctuation_per_100_words": 5,  # Need proper sentence breaks
    "min_periods_per_1000_words": 20,  # Need regular sentence endings
    # NEW: Character Distribution - TTS SAFE
    "min_alphabetic_ratio": 0.65,  # Most text should be letters
    "max_non_ascii_ratio": 0.15,  # Limited special characters
    # NEW: Common Words Check - MUST HAVE
    "min_common_words_found": 8,  # Of 10 most common English words
    # NEW: Sentence Structure - REQUIRED
    "min_sentences_per_5000_chars": 20,  # Need proper sentences
    "max_avg_sentence_length": 50,  # Too long = bad TTS phrasing
}

# Quality Status Mapping
# "success" = TTS-ready, no issues
# "partial_success" = Readable but has warnings
# "failed" = Critical issues, will cause TTS problems

"""
CRITICAL CHECKS (any failure = status "failed"):
1. Replacement characters (�) = FAIL
2. Private use area characters = FAIL  
3. Gibberish score > 0.2 = FAIL
4. Alphabetic ratio < 65% = FAIL
5. Common words < 8/10 = FAIL
6. Punctuation density < 5 per 100 words = FAIL

WARNING CHECKS (triggers "partial_success"):
1. Non-ASCII ratio > 5% but < 15%
2. Punctuation density 5-10 per 100 words (marginal)
3. Average sentence length > 40 words
4. Perplexity 0.85-0.92 (slightly low)
"""

# Example config.yaml for TTS-grade extraction:
EXAMPLE_CONFIG_YAML = """
# Phase 2 TTS-Grade Extraction Config
retry_limit: 1
gibberish_threshold: 0.2  # STRICT - TTS-grade
perplexity_threshold: 0.92
lang_confidence: 0.95  # STRICT - must be clearly English
extract_structure: true

# TTS-specific checks (add to extraction.py)
tts_quality_checks:
  max_replacement_chars: 0
  max_private_use_chars: 0
  min_punctuation_per_100_words: 5
  min_alphabetic_ratio: 0.65
  max_non_ascii_ratio: 0.15
  min_common_words: 8
"""

print(__doc__)
print("\n" + "=" * 80)
print("TTS-GRADE QUALITY THRESHOLDS")
print("=" * 80)
for key, value in EXTRACTION_CONFIG_TTS_GRADE.items():
    print(f"{key:.<40} {value}")

print("\n" + "=" * 80)
print("EXAMPLE CONFIG.YAML")
print("=" * 80)
print(EXAMPLE_CONFIG_YAML)
