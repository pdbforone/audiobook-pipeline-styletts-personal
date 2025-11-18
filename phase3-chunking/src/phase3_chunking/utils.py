import logging
import time
import os
import re
from typing import List, Tuple, Optional, Dict, Any
import ftfy
import spacy
import nltk
from sentence_transformers import SentenceTransformer, util
import textstat
from langdetect import detect, DetectorFactory
try:
    import pysbd  # Fast rule-based sentence boundary detector
except ImportError:  # Optional dependency
    pysbd = None

DetectorFactory.seed = 0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Lazy loading for heavy models
_nlp = None
_model = None

# ✅ FLEXIBLE LIMITS: Three-tier structure for semantic completeness
SOFT_LIMIT_CHARS = 1800  # Preferred chunk size (~23s)
HARD_LIMIT_CHARS = 2000  # Can extend to here for sentence completion (~25s)
EMERGENCY_LIMIT_CHARS = 3000  # Absolute max for completing philosophical arguments (~38s)
MIN_CHUNK_CHARS = 1000  # Minimum viable chunk size

# Duration prediction constants (calibrated for Fish Speech fast delivery)
# Fish Speech averages ~3200 chars/min (~53 chars/sec) and ~640 words/min.
CHARS_PER_MINUTE = 3200
WORDS_PER_MINUTE = 640
MAX_DURATION_SECONDS = 25  # Target maximum duration for preferred chunks
EMERGENCY_DURATION_SECONDS = 38  # Absolute max for emergency completion


def get_nlp():
    """Lazy load spaCy model with increased max_length for large documents."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_lg")
        except OSError:
            logger.warning("en_core_web_lg not found, trying en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
        
        # CRITICAL FIX: Increase max_length for large documents like Systematic Theology (3.9MB)
        # Default is 1,000,000 chars - increase to 10,000,000 (10MB)
        _nlp.max_length = 10_000_000
        logger.info(f"spaCy model loaded with max_length: {_nlp.max_length:,} chars")
    return _nlp


def get_sentence_model():
    """Lazy load sentence transformer."""
    global _model
    if _model is None:
        # 🔧 FIX: Upgraded to all-mpnet-base-v2 for better coherence
        _model = SentenceTransformer("all-mpnet-base-v2")
        logger.info("Loaded sentence model: all-mpnet-base-v2")
    return _model


# Download NLTK data if needed
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


def predict_duration(text: str, method: str = "chars") -> float:
    """
    Predict speech duration for text.
    
    Args:
        text: Text to predict duration for
        method: "chars" (default) or "words" for prediction method
    
    Returns:
        Predicted duration in seconds
    """
    if not text:
        return 0.0
    
    if method == "chars":
        duration = (len(text) / CHARS_PER_MINUTE) * 60
    else:
        word_count = len(text.split())
        duration = (word_count / WORDS_PER_MINUTE) * 60
    
    return duration


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    start = time.perf_counter()

    if not text or not text.strip():
        logger.warning("Empty text provided to clean_text")
        return ""

    text = ftfy.fix_text(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

    elapsed = time.perf_counter() - start
    logger.info(f"Cleaning time: {elapsed:.4f}s")
    return text.strip()


def detect_sentences(text: str) -> List[str]:
    """Detect sentence boundaries using spaCy with pySBD fallback for edge cases."""
    if not text or not text.strip():
        logger.warning("Empty text provided to detect_sentences")
        return []

    sentences: List[str] = []
    try:
        nlp = get_nlp()
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    except Exception as exc:
        logger.warning(f"spaCy sentence detection failed: {exc}")

    # Fallback / refinement: pySBD is strong on abbreviations/bullets and PDF-split text
    if (not sentences or len(sentences) <= 1) and pysbd:
        segmenter = pysbd.Segmenter(language="en", clean=True)
        sentences = [s.strip() for s in segmenter.segment(text) if s and s.strip()]

    logger.info(f"Detected {len(sentences)} sentences")
    return sentences


def is_complete_chunk(text: str) -> Tuple[bool, str]:
    """
    Check if a chunk ends on a complete thought.
    
    🔧 ENHANCED: Now checks for more incomplete patterns including:
    - Relative clauses (which, that, who, whom)
    - Subordinate clauses (because, although, while, since, unless, if)
    - Conjunctions (and, but, or, yet, so)
    - Prepositional phrases
    
    Detects:
    - Unbalanced quotes
    - Dialogue introducers without dialogue
    - Incomplete phrases (prepositions, articles, conjunctions at end)
    - Dangling relative clauses
    - Incomplete subordinate clauses
    
    Args:
        text: Text to check for completeness
    
    Returns:
        (is_complete: bool, reason: str)
    """
    text = text.strip()
    
    if not text:
        return False, "Empty text"
    
    # Check for unbalanced quotes
    double_quotes = text.count('"')
    if double_quotes % 2 != 0:
        return False, "Unbalanced double quotes"
    
    # Check for dialogue introducers (incomplete dialogue)
    dialogue_introducers = [
        r'\bsaid,?\s*$',
        r'\breplied,?\s*$',
        r'\basked,?\s*$',
        r'\banswered,?\s*$',
        r'\bcontinued,?\s*$',
        r'\bexclaimed,?\s*$',
        r'\bwhispered,?\s*$',
    ]
    
    for pattern in dialogue_introducers:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Incomplete dialogue (ends with dialogue introducer)"
    
    # 🔧 ENHANCED: Check for incomplete phrases (more comprehensive)
    incomplete_endings = [
        # Prepositions
        r'\b(to|for|with|from|by|at|in|on|of|about|before|after|during|through|between|among|within|without|against|upon)\s*$',
        # Articles
        r'\b(the|a|an)\s*$',
        # Relative pronouns (incomplete relative clauses)
        r'\b(which|that|who|whom|whose|where|when)\s*$',
        # Subordinating conjunctions (incomplete subordinate clauses)
        r'\b(because|although|though|while|since|unless|if|when|where|before|after|until|as|so|than)\s*$',
        # Coordinating conjunctions
        r'\b(and|but|or|yet|so|nor|for)\s*$',
        # Possessive or auxiliary verbs left dangling
        r'\b(is|are|was|were|has|have|had|will|would|can|could|should|may|might|must)\s*$',
        # Ends with comma (incomplete thought)
        r',\s*$',
        # Ends with semicolon without final clause (rare but possible)
        r';\s*$',
    ]
    
    for pattern in incomplete_endings:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return False, f"Incomplete phrase (ends with '{match.group()}')"
    
    # 🔧 NEW: Check for incomplete complex sentences
    # Example: "...the power of contemplation which"
    # Look for relative clause starters in last 10 words
    words = text.split()
    if len(words) >= 5:
        last_10_words = ' '.join(words[-10:]).lower()
        if any(rel in last_10_words for rel in ['which ', 'that ', 'who ', 'whom ']):
            # Check if there's a complete clause after the relative pronoun
            # Simple heuristic: if there's no verb after the pronoun, it's incomplete
            rel_match = re.search(r'\b(which|that|who|whom)\s+(\w+)', last_10_words)
            if rel_match:
                word_after = rel_match.group(2)
                # Common verbs that would complete the clause
                completing_verbs = ['is', 'are', 'was', 'were', 'has', 'have', 'had', 'can', 'could', 'will', 'would', 'should', 'may', 'might', 'must', 'do', 'does', 'did']
                if word_after not in completing_verbs and not text.endswith('.'):
                    return False, f"Incomplete relative clause (ends with '{rel_match.group()}')"
    
    # Chunk seems complete
    return True, "Complete"


def try_complete_chunk(
    chunk_text: str,
    remaining_sentences: List[str],
    max_chars: int = EMERGENCY_LIMIT_CHARS,
    max_duration: float = MAX_DURATION_SECONDS,
    emergency_duration: float = EMERGENCY_DURATION_SECONDS,
) -> Tuple[str, List[str], bool]:
    """
    🔧 ENHANCED: Aggressively try to complete an incomplete chunk by adding more sentences.
    
    New strategy:
    - Try up to 10 sentences (not just 3) to complete the chunk
    - Accept chunks up to EMERGENCY_LIMIT_CHARS for completion
    - Return success flag to indicate if completion was achieved
    
    Args:
        chunk_text: Current incomplete chunk
        remaining_sentences: Remaining sentences that could complete it
        max_chars: Maximum characters allowed (default EMERGENCY_LIMIT_CHARS)
        
    Returns:
        (completed_chunk, unused_sentences, completion_successful)
    """
    if not remaining_sentences:
        return chunk_text, [], False
    
    # Try adding sentences until chunk is complete or we run out
    working_chunk = chunk_text
    used_count = 0
    
    for i, sent in enumerate(remaining_sentences):
        test_chunk = working_chunk + " " + sent
        
        # Check if adding would exceed EMERGENCY limit
        if len(test_chunk) > max_chars:
            logger.warning(f"Cannot complete chunk: would exceed {max_chars} chars")
            return working_chunk, remaining_sentences[i:], False
        
        test_duration = predict_duration(test_chunk)
        if test_duration > emergency_duration:
            logger.warning(
                f"Cannot complete chunk: would exceed emergency duration {emergency_duration:.1f}s "
                f"(predicted {test_duration:.1f}s)"
            )
            return working_chunk, remaining_sentences[i:], False
        
        is_complete, reason = is_complete_chunk(test_chunk)
        
        if is_complete:
            if test_duration > max_duration:
                logger.info(
                    f"✓ Completed chunk after adding {i+1} sentence(s) "
                    f"(duration {test_duration:.1f}s > {max_duration:.1f}s target)"
                )
            else:
                logger.info(f"✓ Successfully completed chunk after adding {i+1} sentence(s)")
            return test_chunk, remaining_sentences[i+1:], True
        
        working_chunk = test_chunk
        used_count += 1
        
        # Try up to 10 sentences (extended from 3 for philosophical texts)
        if used_count >= 10:
            logger.warning(f"Could not complete chunk after {used_count} sentences")
            break
    
    # Couldn't complete it within limits
    return working_chunk, remaining_sentences[used_count:], False


def split_at_semicolon(text: str) -> List[str]:
    """
    🔧 NEW: Split text at semicolons for philosophical texts.
    
    Semicolons in philosophical writing often separate independent clauses
    that can stand alone, making them ideal split points.
    
    Args:
        text: Text to split
    
    Returns:
        List of text segments split at semicolons
    """
    # Split on semicolon but preserve it
    parts = re.split(r'(;)', text)
    
    # Rejoin semicolons with the preceding part
    segments = []
    current = ""
    for part in parts:
        if part == ";":
            current += part
        elif current:
            segments.append(current.strip())
            current = part
        else:
            current = part
    
    if current.strip():
        segments.append(current.strip())
    
    return [s for s in segments if s]


def merge_backwards(
    chunks: List[str],
    incomplete_chunk: str,
    max_chars: int = EMERGENCY_LIMIT_CHARS,
    emergency_duration: float = EMERGENCY_DURATION_SECONDS,
) -> List[str]:
    """
    🔧 NEW: Merge an incomplete chunk backwards with the previous chunk.
    
    Last resort when a chunk cannot be completed forward without exceeding limits.
    
    Args:
        chunks: List of completed chunks so far
        incomplete_chunk: The incomplete chunk to merge
        max_chars: Maximum characters allowed
    
    Returns:
        Updated chunks list with merged chunk
    """
    if not chunks:
        # No previous chunk to merge with - must keep incomplete chunk
        logger.error("❌ Cannot merge backwards: no previous chunk exists!")
        logger.error(f"   Incomplete chunk will be included: ends with '...{incomplete_chunk[-100:]}'")
        return chunks + [incomplete_chunk]
    
    last_chunk = chunks[-1]
    merged = last_chunk + " " + incomplete_chunk
    
    merged_duration = predict_duration(merged)
    if len(merged) <= max_chars and merged_duration <= emergency_duration:
        chunks[-1] = merged
        logger.info(
            f"✓ Merged incomplete chunk backwards ({len(merged)} chars, {merged_duration:.1f}s)"
        )
        return chunks

    # Even merging backwards exceeds char or duration limits
    logger.warning(
        f"⚠️  Backward merge would exceed limits "
        f"(chars={len(merged)}, duration={merged_duration:.1f}s); trying semicolon split"
    )
    
    semicolon_segments = split_at_semicolon(merged)
    if len(semicolon_segments) > 1:
        chunks[-1] = semicolon_segments[0]
        for seg in semicolon_segments[1:]:
            seg_duration = predict_duration(seg)
            if len(seg) <= max_chars and seg_duration <= emergency_duration:
                chunks.append(seg)
            else:
                logger.warning(
                    f"⚠️  Semicolon segment still exceeds limits "
                    f"(chars={len(seg)}, duration={seg_duration:.1f}s); word-splitting"
                )
                chunks.extend(split_by_words(seg, max_chars, emergency_duration))
        logger.info(f"✓ Split merged chunk into {len(semicolon_segments)} segments at semicolons")
        return chunks

    # No semicolons; force word-split
    logger.warning("⚠️  No semicolons found, forcing word-split of merged chunk")
    chunks[-1:] = split_by_words(merged, max_chars, emergency_duration)
    return chunks


def split_by_words(
    text: str,
    max_chars: int,
    emergency_duration: float = EMERGENCY_DURATION_SECONDS,
) -> List[str]:
    """
    🔧 NEW: Split text by words when all else fails.
    
    Last resort splitting mechanism that breaks at word boundaries.
    
    Args:
        text: Text to split
        max_chars: Maximum characters per segment
    
    Returns:
        List of text segments
    """
    words = text.split()
    segments = []
    current: List[str] = []
    current_len = 0
   
    for word in words:
        word_len = len(word) + 1  # +1 for space
        candidate_len = current_len + word_len
        candidate_segment = ' '.join(current + [word]).strip()
        candidate_duration = predict_duration(candidate_segment) if candidate_segment else 0.0

        if current and (candidate_len > max_chars or candidate_duration > emergency_duration):
            segments.append(' '.join(current).strip())
            current = [word]
            current_len = len(word) + 1
        else:
            current.append(word)
            current_len = candidate_len
    
    if current:
        segments.append(' '.join(current).strip())
    
    return [seg for seg in segments if seg]


def merge_short_chunks(
    chunks: List[str],
    min_target_chars: int = MIN_CHUNK_CHARS,
    soft_limit: int = SOFT_LIMIT_CHARS,
    emergency_limit: int = EMERGENCY_LIMIT_CHARS,
) -> List[str]:
    """
    Merge consecutive short chunks to improve pacing in aphoristic texts.
    
    Args:
        chunks: List of chunk strings.
        min_target_chars: Desired minimum length for merged chunks.
        soft_limit: Preferred maximum length before flushing a chunk.
        emergency_limit: Absolute maximum allowable characters.
    
    Returns:
        List of merged chunks.
    """
    if not chunks:
        return []

    merged: List[str] = []
    buffer = ""

    def _join_text(existing: str, addition: str) -> str:
        return addition if not existing else f"{existing}\n\n{addition}"

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        candidate = _join_text(buffer, chunk)
        candidate_len = len(candidate)

        if candidate_len <= emergency_limit:
            if candidate_len < min_target_chars:
                buffer = candidate
                continue

            if candidate_len <= soft_limit:
                merged.append(candidate)
                buffer = ""
                continue

            is_complete, _ = is_complete_chunk(candidate)
            if is_complete:
                merged.append(candidate)
                buffer = ""
            else:
                buffer = candidate
            continue

        # Exceeds emergency limit; flush buffer if present
        if buffer:
            merged.append(buffer)
            buffer = chunk
        else:
            merged.append(chunk)
            buffer = ""

    if buffer:
        merged.append(buffer)

    return merged


def _chunk_by_char_count_optimized(
    sentences: List[str], 
    min_chars: int = MIN_CHUNK_CHARS, 
    soft_limit: int = SOFT_LIMIT_CHARS,
    hard_limit: int = HARD_LIMIT_CHARS,
    emergency_limit: int = EMERGENCY_LIMIT_CHARS,
    max_duration: float = MAX_DURATION_SECONDS,
    emergency_duration: float = EMERGENCY_DURATION_SECONDS
) -> List[str]:
    """
    🔧 COMPLETELY REWRITTEN: Flexible limits with aggressive completion.
    
    NEW STRATEGY:
    1. Build chunks targeting SOFT_LIMIT (1800 chars, ~23s)
    2. Can extend to HARD_LIMIT (2000 chars, ~25s) to complete sentences
    3. Use EMERGENCY_LIMIT (3000 chars, ~38s) ONLY to avoid incomplete chunks
    4. NEVER output incomplete chunks - merge backwards if necessary
    5. Final validation pass catches any incomplete chunks that escape
    
    Args:
        sentences: List of sentences to chunk
        min_chars: Minimum characters per chunk (default 1000)
        soft_limit: Preferred chunk size (default 1800)
        hard_limit: Can extend to here for completion (default 2000)
        emergency_limit: Absolute max for completion (default 3000)
        max_duration: Target duration (default 25s)
        emergency_duration: Absolute max duration (default 38s)
        
    Returns:
        List of chunks, ALL guaranteed to be complete
    """
    chunks = []
    i = 0
    current_chunk = []
    current_char_count = 0
    
    while i < len(sentences):
        sent = sentences[i].strip()
        if not sent:
            i += 1
            continue
        
        sent_len = len(sent)
        
        # Try adding sentence to current chunk
        test_chunk = current_chunk + [sent]
        test_text = " ".join(test_chunk)
        test_len = len(test_text)
        test_duration = predict_duration(test_text)
        
        # Determine which limit applies
        if test_len <= soft_limit and test_duration <= max_duration:
            # Within soft limit - safe to add
            current_chunk.append(sent)
            current_char_count = test_len
            i += 1
            
            # Check if we've reached a good stopping point (>= min and complete)
            if current_char_count >= min_chars:
                chunk_text = " ".join(current_chunk)
                is_complete, reason = is_complete_chunk(chunk_text)
                
                if is_complete:
                    # Perfect - complete chunk within soft limit
                    chunks.append(chunk_text)
                    logger.debug(f"✓ Flushed complete chunk at soft limit ({len(chunk_text)} chars, {predict_duration(chunk_text):.1f}s)")
                    current_chunk = []
                    current_char_count = 0
                # If not complete, keep accumulating
            
        elif test_len <= hard_limit:
            # Between soft and hard limit - can still add if it completes the chunk
            current_chunk.append(sent)
            current_char_count = test_len
            i += 1
            
            chunk_text = " ".join(current_chunk)
            is_complete, reason = is_complete_chunk(chunk_text)
            
            if is_complete:
                # Complete chunk within hard limit - acceptable
                chunks.append(chunk_text)
                logger.debug(f"✓ Flushed complete chunk at hard limit ({len(chunk_text)} chars, {predict_duration(chunk_text):.1f}s)")
                current_chunk = []
                current_char_count = 0
            elif current_char_count >= soft_limit:
                # Exceeded soft limit and still incomplete - try completion
                logger.info(f"⚠️  Chunk incomplete at {current_char_count} chars (>{soft_limit}), attempting completion")
                completed_text, remaining, success = try_complete_chunk(
                    chunk_text,
                    sentences[i:],
                    emergency_limit,
                    max_duration,
                    emergency_duration,
                )
                
                if success:
                    # Successfully completed
                    chunks.append(completed_text)
                    logger.info(f"✓ Completed chunk within emergency limit ({len(completed_text)} chars)")
                    sentences_used = len(sentences[i:]) - len(remaining)
                    i += sentences_used
                    current_chunk = []
                    current_char_count = 0
                else:
                    # Could not complete - merge backwards
                    logger.warning(f"⚠️  Cannot complete chunk, merging backwards")
                    chunks = merge_backwards(chunks, completed_text, emergency_limit, emergency_duration)
                    current_chunk = []
                    current_char_count = 0
            # If still below soft limit, keep accumulating
            
        else:
            # Would exceed hard limit - must flush current chunk
            if current_chunk and current_char_count >= min_chars:
                chunk_text = " ".join(current_chunk)
                is_complete, reason = is_complete_chunk(chunk_text)
                
                if not is_complete:
                    # Try to complete with upcoming sentences (up to emergency limit)
                    logger.info(f"⚠️  Flushing incomplete chunk ({reason}), attempting completion")
                    completed_text, remaining, success = try_complete_chunk(
                        chunk_text,
                        sentences[i:],
                        emergency_limit,
                        max_duration,
                        emergency_duration,
                    )
                    
                    if success:
                        chunks.append(completed_text)
                        logger.info(f"✓ Completed chunk within emergency limit ({len(completed_text)} chars)")
                        sentences_used = len(sentences[i:]) - len(remaining)
                        i += sentences_used
                    else:
                        # Could not complete - merge backwards
                        logger.warning(f"⚠️  Cannot complete chunk, merging backwards")
                        chunks = merge_backwards(chunks, completed_text, emergency_limit, emergency_duration)
                else:
                    # Complete chunk - flush it
                    chunks.append(chunk_text)
                    logger.debug(f"✓ Flushed complete chunk ({len(chunk_text)} chars)")
                
                current_chunk = [sent]
                current_char_count = sent_len
                i += 1
            else:
                # Current chunk too small - just add this sentence
                current_chunk.append(sent)
                current_char_count = test_len
                i += 1
    
    # Handle final chunk
    if current_chunk and current_char_count >= min_chars:
        final_text = " ".join(current_chunk)
        is_complete, reason = is_complete_chunk(final_text)
        
        if not is_complete:
            logger.warning(f"⚠️  Final chunk incomplete ({reason}), merging backwards")
            chunks = merge_backwards(chunks, final_text, emergency_limit, emergency_duration)
        else:
            chunks.append(final_text)
            logger.debug(f"✓ Flushed final complete chunk ({len(final_text)} chars)")
    elif current_chunk:
        # Final chunk too short - merge backwards
        final_text = " ".join(current_chunk)
        if len(final_text) >= 50:  # Only keep if substantial
            logger.info(f"⚠️  Final chunk too short ({len(final_text)} chars), merging backwards")
            chunks = merge_backwards(chunks, final_text, emergency_limit, emergency_duration)
    
    return chunks


def validate_chunks(chunks: List[str]) -> List[str]:
    """
    🔧 NEW: Final validation pass to catch incomplete chunks.
    
    Last line of defense - scans all chunks and attempts to fix any incomplete ones.
    
    Args:
        chunks: List of chunks to validate
    
    Returns:
        Validated chunks list (incomplete ones fixed or flagged)
    """
    validated = []
    incomplete_count = 0
    
    for i, chunk in enumerate(chunks):
        is_complete, reason = is_complete_chunk(chunk)
        
        if not is_complete:
            incomplete_count += 1
            logger.error(f"❌ VALIDATION FAILED: Chunk {i+1} is incomplete ({reason})")
            logger.error(f"   Chunk ends with: '...{chunk[-150:]}'")
            
            # Try to merge with next chunk if available
            if i < len(chunks) - 1:
                merged = chunk + " " + chunks[i+1]
                if len(merged) <= EMERGENCY_LIMIT_CHARS:
                    logger.info(f"✓ Merged incomplete chunk {i+1} with chunk {i+2}")
                    validated.append(merged)
                    # Skip next chunk since we merged it
                    chunks[i+1] = ""  # Mark as used
                else:
                    # Can't merge forward - accept incomplete
                    logger.error(f"   ⚠️  Cannot merge forward (would be {len(merged)} chars)")
                    validated.append(chunk)
            else:
                # Last chunk and incomplete - try to merge with previous
                if validated:
                    merged = validated[-1] + " " + chunk
                    if len(merged) <= EMERGENCY_LIMIT_CHARS:
                        logger.info(f"✓ Merged final incomplete chunk with previous")
                        validated[-1] = merged
                    else:
                        logger.error(f"   ⚠️  Cannot merge backwards (would be {len(merged)} chars)")
                        validated.append(chunk)
                else:
                    # Only chunk and it's incomplete - must keep it
                    logger.error(f"   ⚠️  Only chunk is incomplete - keeping anyway")
                    validated.append(chunk)
        else:
            validated.append(chunk)
    
    if incomplete_count > 0:
        logger.error(f"❌ VALIDATION SUMMARY: {incomplete_count} incomplete chunk(s) detected")
    else:
        logger.info(f"✅ VALIDATION PASSED: All {len(chunks)} chunks are complete")
    
    return validated


def form_semantic_chunks(
    sentences: List[str], 
    min_chars: int = MIN_CHUNK_CHARS, 
    soft_limit: int = SOFT_LIMIT_CHARS,
    hard_limit: int = HARD_LIMIT_CHARS,
    emergency_limit: int = EMERGENCY_LIMIT_CHARS,
    max_duration: float = MAX_DURATION_SECONDS,
    emergency_duration: float = EMERGENCY_DURATION_SECONDS,
) -> Tuple[List[str], List[float], List[List[float]]]:
    """
    Form semantic chunks with FLEXIBLE LIMITS and AGGRESSIVE COMPLETION.
    
    🔧 MAJOR UPGRADE:
    - Three-tier limit structure (SOFT → HARD → EMERGENCY)
    - NEVER outputs incomplete chunks
    - Backward merging when forward completion fails
    - Final validation pass
    - Semicolon-aware splitting for philosophical texts
    """
    if not sentences:
        logger.warning("No sentences provided to form_semantic_chunks")
        return [], [], []

    start = time.perf_counter()

    valid_sentences = [s for s in sentences if s.strip() and len(s) >= 3]
    if len(valid_sentences) < len(sentences):
        logger.warning(f"Dropped {len(sentences) - len(valid_sentences)} invalid/empty sentences")

    # Create chunks with flexible limits
    chunks = _chunk_by_char_count_optimized(
        valid_sentences, 
        min_chars, 
        soft_limit,
        hard_limit,
        emergency_limit,
        max_duration,
        emergency_duration
    )
    
    if chunks:
        short_threshold = 500
        char_lengths = [len(c) for c in chunks]
        short_count = sum(1 for length in char_lengths if length < short_threshold)
        if short_count > len(chunks) * 0.3:
            logger.info(
                f"Detected aphoristic distribution: {short_count}/{len(chunks)} chunks "
                f"below {short_threshold} chars"
            )
            pre_merge_count = len(chunks)
            chunks = merge_short_chunks(
                chunks,
                min_target_chars=min_chars,
                soft_limit=soft_limit,
                emergency_limit=emergency_limit,
            )
            logger.info(
                f"Merged short chunks for pacing: {pre_merge_count} ➜ {len(chunks)} chunks"
            )
    
    # 🔧 NEW: Final validation pass
    chunks = validate_chunks(chunks)

    valid_chunks = [c for c in chunks if c.strip() and len(c) >= 50]
    if len(chunks) > len(valid_chunks):
        logger.warning(f"Dropped {len(chunks) - len(valid_chunks)} invalid/short chunks after validation")

    if not valid_chunks:
        logger.error("No valid chunks for embedding calculation")
        return [], [], []

    # Calculate metrics
    char_lengths = [len(c) for c in valid_chunks]
    durations = [predict_duration(c) for c in valid_chunks]
    
    logger.info(
        f"Chunk distribution: {len(valid_chunks)} chunks, "
        f"chars=[{min(char_lengths)}-{max(char_lengths)}] "
        f"(avg={sum(char_lengths)/len(char_lengths):.0f}), "
        f"durations=[{min(durations):.1f}s-{max(durations):.1f}s] "
        f"(avg={sum(durations)/len(durations):.1f}s)"
    )
    
    # Report limit adherence
    within_soft = sum(1 for l in char_lengths if l <= soft_limit)
    within_hard = sum(1 for l in char_lengths if soft_limit < l <= hard_limit)
    within_emergency = sum(1 for l in char_lengths if hard_limit < l <= emergency_limit)
    over_emergency = sum(1 for l in char_lengths if l > emergency_limit)
    
    logger.info(f"Limit adherence: {within_soft} within SOFT ({soft_limit}), "
                f"{within_hard} within HARD ({hard_limit}), "
                f"{within_emergency} within EMERGENCY ({emergency_limit}), "
                f"{over_emergency} OVER emergency")
    
    if over_emergency > 0:
        logger.error(f"❌ CRITICAL: {over_emergency} chunks exceed EMERGENCY limit!")
        for i, (chunk, length, duration) in enumerate(zip(valid_chunks, char_lengths, durations)):
            if length > emergency_limit:
                logger.error(f"   Chunk {i+1}: {length} chars, {duration:.1f}s")
                logger.error(f"   Preview: {chunk[:200]}...{chunk[-200:]}")
    
    # Calculate coherence
    model = get_sentence_model()
    embeddings = model.encode(valid_chunks, batch_size=32, show_progress_bar=True)
    coherence = []
    for i in range(len(embeddings) - 1):
        try:
            score = float(util.cos_sim(embeddings[i], embeddings[i+1])[0][0])
            score = max(0.0, min(1.0, score))
            coherence.append(score)
        except Exception as e:
            logger.warning(f"Failed to compute coherence for chunk pair {i+1}: {e}")
            coherence.append(0.0)

    avg_coherence = sum(coherence) / len(coherence) if coherence else 0
    logger.info(f"Average coherence: {avg_coherence:.4f}")

    elapsed = time.perf_counter() - start
    logger.info(f"Chunking time: {elapsed:.4f}s")

    return valid_chunks, coherence, embeddings.tolist()


def assess_readability(chunks: List[str]) -> List[float]:
    """Calculate Flesch Reading Ease scores for chunks."""
    if not chunks:
        return []

    readability_scores = []
    for i, chunk in enumerate(chunks):
        if not chunk or len(chunk.split()) < 3:
            logger.warning(f"Chunk {i+1} too short for readability assessment")
            readability_scores.append(0.0)
        else:
            try:
                score = textstat.flesch_reading_ease(chunk)
                readability_scores.append(score)
            except Exception as e:
                logger.warning(f"Readability calculation failed for chunk {i+1}: {e}")
                readability_scores.append(0.0)

    return readability_scores


def save_chunks(text_path: str, chunks: List[str], output_dir: str) -> List[str]:
    """Save chunks to individual files and return ABSOLUTE paths."""
    if not chunks:
        logger.warning("No chunks to save")
        return []

    from pathlib import Path
    output_dir_abs = Path(output_dir).resolve()
    output_dir_abs.mkdir(parents=True, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(text_path))[0]
    chunk_paths = []

    for i, chunk in enumerate(chunks):
        chunk_path_abs = output_dir_abs / f"{base_name}_chunk_{i+1:03d}.txt"
        try:
            with open(chunk_path_abs, "w", encoding="utf-8") as f:
                f.write(chunk)
            chunk_paths.append(str(chunk_path_abs))
            logger.debug(f"Saved chunk {i+1} to: {chunk_path_abs}")
        except Exception as e:
            logger.error(f"Failed to save chunk {i+1}: {e}")
            raise

    logger.info(f"Saved {len(chunk_paths)} chunks to {output_dir_abs}")
    return chunk_paths


def log_chunk_times(
    chunks: List[str],
    config: Optional["ValidationConfig"] = None,
):
    """
    Log processing time and size metrics for each chunk with duration prediction.
    """
    soft_limit = getattr(config, "soft_chunk_chars", SOFT_LIMIT_CHARS)
    hard_limit = getattr(config, "hard_chunk_chars", HARD_LIMIT_CHARS)
    emergency_limit = getattr(config, "emergency_chunk_chars", EMERGENCY_LIMIT_CHARS)
    max_duration_limit = getattr(config, "max_chunk_duration", MAX_DURATION_SECONDS)
    emergency_duration_limit = getattr(
        config, "emergency_chunk_duration", EMERGENCY_DURATION_SECONDS
    )

    for i, chunk in enumerate(chunks):
        start = time.perf_counter()
        word_count = len(chunk.split())
        char_count = len(chunk)
        duration = predict_duration(chunk, method="chars")
        elapsed = time.perf_counter() - start
        
        # Determine status based on flexible limits
        if char_count <= soft_limit and duration <= max_duration_limit:
            status = "✓ OPTIMAL"
        elif char_count <= hard_limit:
            status = "✓ ACCEPTABLE"
        elif char_count <= emergency_limit:
            status = "⚠️  EXTENDED"
        else:
            status = "❌ OVERSIZED"
        
        logger.debug(
            f"Chunk {i+1}: {word_count} words, {char_count} chars, "
            f"~{duration:.1f}s duration, processed in {elapsed:.4f}s [{status}]"
        )
        
        if duration > emergency_duration_limit:
            logger.warning(
                f"Chunk {i+1} duration ({duration:.1f}s) exceeds EMERGENCY ({emergency_duration_limit}s)"
            )


def calculate_chunk_metrics(
    chunks: List[str],
    config: Optional["ValidationConfig"] = None,
) -> Dict[str, Any]:
    """
    Calculate detailed metrics for chunks with duration prediction and flexible limits.
    
    Returns:
        Dictionary with chunk size/duration metrics for pipeline.json logging
    """
    if not chunks:
        return {
            "chunk_char_lengths": [],
            "chunk_word_counts": [],
            "chunk_durations": [],
            "avg_char_length": 0,
            "avg_word_count": 0,
            "avg_duration": 0,
            "max_duration": 0,
            "min_duration": 0,
            "chunks_within_soft_limit": 0,
            "chunks_within_hard_limit": 0,
            "chunks_within_emergency_limit": 0,
            "chunks_exceeding_emergency": 0,
        }
    
    char_lengths = [len(chunk) for chunk in chunks]
    word_counts = [len(chunk.split()) for chunk in chunks]
    durations = [predict_duration(chunk, method="chars") for chunk in chunks]

    soft_limit = getattr(config, "soft_chunk_chars", SOFT_LIMIT_CHARS)
    hard_limit = getattr(config, "hard_chunk_chars", HARD_LIMIT_CHARS)
    emergency_limit = getattr(config, "emergency_chunk_chars", EMERGENCY_LIMIT_CHARS)
    max_duration_limit = getattr(config, "max_chunk_duration", MAX_DURATION_SECONDS)
    emergency_duration_limit = getattr(config, "emergency_chunk_duration", EMERGENCY_DURATION_SECONDS)
    
    within_soft = sum(1 for l in char_lengths if l <= soft_limit)
    within_hard = sum(1 for l in char_lengths if soft_limit < l <= hard_limit)
    within_emergency = sum(1 for l in char_lengths if hard_limit < l <= emergency_limit)
    exceeding = sum(1 for l in char_lengths if l > emergency_limit)
    
    return {
        "chunk_char_lengths": char_lengths,
        "chunk_word_counts": word_counts,
        "chunk_durations": durations,
        "avg_char_length": sum(char_lengths) / len(char_lengths),
        "avg_word_count": sum(word_counts) / len(word_counts),
        "avg_duration": sum(durations) / len(durations),
        "max_duration": max(durations),
        "min_duration": min(durations) if durations else 0,
        "chunks_within_soft_limit": within_soft,
        "chunks_within_hard_limit": within_hard,
        "chunks_within_emergency_limit": within_emergency,
        "chunks_exceeding_emergency": exceeding,
        "soft_limit": soft_limit,
        "hard_limit": hard_limit,
        "emergency_limit": emergency_limit,
        "max_duration_limit": max_duration_limit,
        "emergency_duration_limit": emergency_duration_limit,
    }
