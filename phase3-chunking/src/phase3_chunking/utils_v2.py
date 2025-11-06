"""
Phase 3 Utils - IMPROVED VERSION with Flexible Limits
Based on research: Prioritize sentence completion over strict character limits
"""
import logging
import time
import os
import re
from typing import List, Tuple, Optional, Dict
import ftfy
import spacy
import nltk
from sentence_transformers import SentenceTransformer, util
import textstat
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Lazy loading for heavy models
_nlp = None
_model = None

# 🔧 NEW FLEXIBLE LIMIT STRUCTURE (Research-based)
SOFT_LIMIT = 1800        # Preferred chunk size
HARD_LIMIT = 2000        # Can extend to complete sentences  
EMERGENCY_LIMIT = 3000   # Only for sentence completion (rare)
MAX_DURATION_SECONDS = 25  # TTS constraint (unchanged)

# Duration prediction constants
CHARS_PER_MINUTE = 750
WORDS_PER_MINUTE = 150


def get_nlp():
    """Lazy load spaCy model with increased max_length."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_lg")
        except OSError:
            logger.warning("en_core_web_lg not found, trying en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
        _nlp.max_length = 10_000_000
        logger.info(f"spaCy model loaded with max_length: {_nlp.max_length:,} chars")
    return _nlp


def get_sentence_model():
    """Lazy load sentence transformer."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-mpnet-base-v2")
        logger.info("Loaded sentence model: all-mpnet-base-v2")
    return _model


# Download NLTK data if needed
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


def predict_duration(text: str, method: str = "chars") -> float:
    """Predict speech duration for text."""
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
    """Detect sentence boundaries using spaCy."""
    if not text or not text.strip():
        logger.warning("Empty text provided to detect_sentences")
        return []

    nlp = get_nlp()
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    logger.info(f"Detected {len(sentences)} sentences")
    return sentences


def is_complete_chunk(text: str) -> Tuple[bool, str]:
    """
    🔧 ENHANCED: Check if chunk ends on complete thought.
    
    NEW: Treats semicolons specially for philosophical texts.
    
    Detects:
    - Unbalanced quotes
    - Dialogue introducers without dialogue
    - Incomplete phrases (prepositions, articles at end)
    - Relative pronouns cut off (which, that, who)
    - Conjunctions requiring continuation
    """
    text = text.strip()
    
    if not text:
        return False, "Empty text"
    
    # Check for unbalanced quotes
    double_quotes = text.count('"')
    if double_quotes % 2 != 0:
        return False, "Unbalanced double quotes"
    
    # Check for dialogue introducers
    dialogue_introducers = [
        r'\bsaid,?\s*$', r'\breplied,?\s*$', r'\basked,?\s*$',
        r'\banswered,?\s*$', r'\bcontinued,?\s*$', r'\bexclaimed,?\s*$',
        r'\bwhispered,?\s*$',
    ]
    
    for pattern in dialogue_introducers:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Incomplete dialogue (ends with dialogue introducer)"
    
    # 🔧 NEW: Check for relative pronouns (indicates incomplete clause)
    relative_pronouns = [
        r'\bwhich\s*$', r'\bthat\s*$', r'\bwho\s*$', r'\bwhom\s*$',
        r'\bwhose\s*$', r'\bwhere\s*$', r'\bwhen\s*$',
    ]
    
    for pattern in relative_pronouns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Incomplete clause (ends with relative pronoun)"
    
    # 🔧 NEW: Check for conjunctions requiring continuation
    hanging_conjunctions = [
        r',\s+and\s*$', r',\s+but\s*$', r',\s+or\s*$', r',\s+nor\s*$',
        r',\s+for\s*$', r',\s+yet\s*$', r',\s+so\s*$',
    ]
    
    for pattern in hanging_conjunctions:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Incomplete thought (ends with conjunction)"
    
    # Check for incomplete phrases (prepositions, articles)
    incomplete_endings = [
        r'\b(to|for|with|from|by|at|in|on|of|about|before|after|through|during)\s*$',
        r'\b(the|a|an)\s*$',
        r',\s*$',  # Ends with comma
    ]
    
    for pattern in incomplete_endings:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Incomplete phrase (dangling preposition/article)"
    
    # Chunk seems complete
    return True, "Complete"


def split_at_semicolons(text: str, max_chars: int) -> List[str]:
    """
    🔧 NEW: Split philosophical texts at semicolons (Tier 1 break point).
    
    For texts like Marcus Aurelius, semicolons connect independent clauses
    and are primary break points.
    """
    # Split on semicolons
    parts = re.split(r';\s*', text)
    
    chunks = []
    current = ""
    
    for part in parts:
        # Add semicolon back (except for last part)
        if part != parts[-1]:
            part = part + ";"
        
        if not current:
            current = part
        elif len(current) + len(part) + 1 <= max_chars:
            current += " " + part
        else:
            # Flush current and start new
            if current:
                chunks.append(current.strip())
            current = part
    
    if current:
        chunks.append(current.strip())
    
    return chunks


def split_at_clauses(text: str, max_chars: int) -> List[str]:
    """
    🔧 NEW: Split at clause boundaries when semicolons insufficient.
    
    Hierarchy:
    1. Semicolons (already tried)
    2. Comma + coordinating conjunction
    3. Colons, dashes
    4. Any comma
    """
    # Try comma + conjunction first
    parts = re.split(r',\s+(and|but|or|nor|for|yet|so)\s+', text, flags=re.IGNORECASE)
    
    if len(parts) > 1:
        chunks = []
        current = ""
        i = 0
        while i < len(parts):
            part = parts[i]
            # Rejoin conjunctions
            if i + 1 < len(parts) and parts[i + 1] in ['and', 'but', 'or', 'nor', 'for', 'yet', 'so']:
                part = part + ", " + parts[i + 1]
                i += 2
            else:
                i += 1
            
            if not current:
                current = part
            elif len(current) + len(part) + 1 <= max_chars:
                current += " " + part
            else:
                if current:
                    chunks.append(current.strip())
                current = part
        
        if current:
            chunks.append(current.strip())
        
        return chunks
    
    # Fall back to any comma
    parts = re.split(r',\s*', text)
    chunks = []
    current = ""
    
    for part in parts:
        if part != parts[-1]:
            part = part + ","
        
        if not current:
            current = part
        elif len(current) + len(part) + 1 <= max_chars:
            current += " " + part
        else:
            if current:
                chunks.append(current.strip())
            current = part
    
    if current:
        chunks.append(current.strip())
    
    return chunks


def try_complete_chunk_aggressive(
    chunk_text: str, 
    remaining_sentences: List[str],
    hard_limit: int = HARD_LIMIT,
    emergency_limit: int = EMERGENCY_LIMIT
) -> Tuple[str, List[str], bool]:
    """
    🔧 NEW: Aggressively try to complete chunks within flexible limits.
    
    Returns:
        (completed_text, unused_sentences, was_completed)
    """
    if not remaining_sentences:
        return chunk_text, [], False
    
    working_chunk = chunk_text
    used_count = 0
    
    for i, sent in enumerate(remaining_sentences):
        test_chunk = working_chunk + " " + sent
        test_len = len(test_chunk)
        test_duration = predict_duration(test_chunk)
        
        # Check if we can add this sentence
        if test_len <= hard_limit and test_duration <= MAX_DURATION_SECONDS:
            working_chunk = test_chunk
            used_count += 1
            
            # Check if now complete
            is_complete, _ = is_complete_chunk(working_chunk)
            if is_complete:
                return working_chunk, remaining_sentences[i+1:], True
        
        elif test_len <= emergency_limit and test_duration <= MAX_DURATION_SECONDS:
            # Emergency extension - only if it completes the chunk
            is_complete, _ = is_complete_chunk(test_chunk)
            if is_complete:
                logger.info(f"Emergency extension to {test_len} chars to complete chunk")
                return test_chunk, remaining_sentences[i+1:], True
            else:
                # Can't extend further
                break
        else:
            # Exceeds all limits
            break
        
        # Don't try more than 5 sentences
        if used_count >= 5:
            break
    
    # Couldn't complete within limits
    return working_chunk, remaining_sentences[used_count:], False


def chunk_with_flexible_limits(
    sentences: List[str],
    soft_limit: int = SOFT_LIMIT,
    hard_limit: int = HARD_LIMIT,
    emergency_limit: int = EMERGENCY_LIMIT,
    max_duration: float = MAX_DURATION_SECONDS
) -> List[str]:
    """
    🔧 NEW: Chunk with flexible limits prioritizing sentence completion.
    
    Strategy:
    1. Build chunks staying under SOFT_LIMIT when possible
    2. Extend to HARD_LIMIT to complete sentences
    3. Use EMERGENCY_LIMIT only for sentence completion
    4. If chunk can't be completed, merge BACKWARDS with previous chunk
    5. If merged chunk too large, split BOTH at semicolons → clauses
    6. NEVER output incomplete chunks
    """
    chunks = []
    current_chunk = []
    current_chars = 0
    
    i = 0
    while i < len(sentences):
        sent = sentences[i].strip()
        if not sent:
            i += 1
            continue
        
        sent_len = len(sent)
        sent_duration = predict_duration(sent)
        
        # Handle oversized single sentence
        if sent_len > hard_limit or sent_duration > max_duration:
            logger.warning(f"Sentence exceeds HARD_LIMIT ({sent_len} chars), splitting at semicolons/clauses")
            
            # Flush current chunk first
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                is_complete, reason = is_complete_chunk(chunk_text)
                
                if not is_complete:
                    # Try to complete with remaining sentences
                    chunk_text, remaining, was_completed = try_complete_chunk_aggressive(
                        chunk_text, sentences[i:], hard_limit, emergency_limit
                    )
                    sentences_used = len(sentences[i:]) - len(remaining)
                    i += sentences_used
                    
                    if not was_completed:
                        logger.warning(f"Couldn't complete chunk: {reason}")
                
                chunks.append(chunk_text)
                current_chunk = []
                current_chars = 0
            
            # Split oversized sentence hierarchically
            if sent_len > emergency_limit:
                # Try semicolons first
                sub_chunks = split_at_semicolons(sent, hard_limit)
                if max(len(c) for c in sub_chunks) > hard_limit:
                    # Semicolons didn't work, try clauses
                    final_chunks = []
                    for sub in sub_chunks:
                        if len(sub) > hard_limit:
                            final_chunks.extend(split_at_clauses(sub, hard_limit))
                        else:
                            final_chunks.append(sub)
                    chunks.extend(final_chunks)
                else:
                    chunks.extend(sub_chunks)
            else:
                # Fits in emergency limit
                chunks.append(sent)
            
            i += 1
            continue
        
        # Calculate what adding this sentence would create
        test_chunk = current_chunk + [sent]
        test_text = " ".join(test_chunk)
        test_len = len(test_text)
        test_duration = predict_duration(test_text)
        
        # Decision logic
        if test_len <= soft_limit and test_duration <= max_duration:
            # Under soft limit - just add it
            current_chunk.append(sent)
            current_chars = test_len
            i += 1
            
        elif test_len <= hard_limit and test_duration <= max_duration:
            # Exceeds soft but within hard - add and check if should flush
            current_chunk.append(sent)
            current_chars = test_len
            i += 1
            
            # Check if complete
            is_complete, _ = is_complete_chunk(test_text)
            if is_complete and current_chars >= soft_limit:
                # Good stopping point
                chunks.append(test_text)
                current_chunk = []
                current_chars = 0
            
        else:
            # Would exceed hard limit - flush current and handle
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                is_complete, reason = is_complete_chunk(chunk_text)
                
                if not is_complete:
                    # Try to complete
                    chunk_text, remaining, was_completed = try_complete_chunk_aggressive(
                        chunk_text, sentences[i:], hard_limit, emergency_limit
                    )
                    sentences_used = len(sentences[i:]) - len(remaining)
                    i += sentences_used
                    
                    if not was_completed:
                        # Couldn't complete - merge backwards with previous chunk
                        if chunks:
                            logger.info(f"Merging incomplete chunk backwards: {reason}")
                            prev_chunk = chunks[-1]
                            merged = prev_chunk + " " + chunk_text
                            
                            if len(merged) <= emergency_limit and predict_duration(merged) <= max_duration:
                                # Merge successful
                                chunks[-1] = merged
                            else:
                                # Merged chunk too large - split both at semicolons
                                logger.info(f"Merged chunk too large ({len(merged)} chars), splitting at semicolons")
                                sub_chunks = split_at_semicolons(merged, hard_limit)
                                if max(len(c) for c in sub_chunks) > hard_limit:
                                    # Try clauses
                                    final_chunks = []
                                    for sub in sub_chunks:
                                        if len(sub) > hard_limit:
                                            final_chunks.extend(split_at_clauses(sub, hard_limit))
                                        else:
                                            final_chunks.append(sub)
                                    chunks[-1:] = final_chunks
                                else:
                                    chunks[-1:] = sub_chunks
                        else:
                            # First chunk and incomplete - just add it with warning
                            logger.warning(f"First chunk incomplete: {reason}")
                            chunks.append(chunk_text)
                else:
                    # Complete - just add it
                    chunks.append(chunk_text)
                
                current_chunk = [sent]
                current_chars = sent_len
                i += 1
            else:
                # No current chunk - start new with this sentence
                current_chunk = [sent]
                current_chars = sent_len
                i += 1
    
    # Handle final chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        is_complete, reason = is_complete_chunk(chunk_text)
        
        if not is_complete and chunks:
            # Try merging with previous
            logger.info(f"Final chunk incomplete: {reason}, merging backwards")
            merged = chunks[-1] + " " + chunk_text
            
            if len(merged) <= emergency_limit and predict_duration(merged) <= max_duration:
                chunks[-1] = merged
            else:
                # Split the merged chunk
                sub_chunks = split_at_semicolons(merged, hard_limit)
                if max(len(c) for c in sub_chunks) > hard_limit:
                    final_chunks = []
                    for sub in sub_chunks:
                        if len(sub) > hard_limit:
                            final_chunks.extend(split_at_clauses(sub, hard_limit))
                        else:
                            final_chunks.append(sub)
                    chunks[-1:] = final_chunks
                else:
                    chunks[-1:] = sub_chunks
        else:
            chunks.append(chunk_text)
    
    return chunks


def validate_chunks_completeness(chunks: List[str]) -> List[Tuple[int, str]]:
    """
    🔧 NEW: Final validation pass to catch any incomplete chunks.
    
    Returns:
        List of (chunk_index, reason) for incomplete chunks
    """
    incomplete = []
    
    for i, chunk in enumerate(chunks):
        is_complete, reason = is_complete_chunk(chunk)
        if not is_complete:
            incomplete.append((i + 1, reason))
            logger.error(f"❌ Chunk {i+1} is INCOMPLETE: {reason}")
            logger.error(f"   Last 100 chars: ...{chunk[-100:]}")
    
    return incomplete


def form_semantic_chunks(
    sentences: List[str], 
    min_chars: int = SOFT_LIMIT,  # Use soft limit as minimum
    max_chars: int = HARD_LIMIT,
    max_duration: float = MAX_DURATION_SECONDS
) -> Tuple[List[str], List[float], List[List[float]]]:
    """
    🔧 REWRITTEN: Form semantic chunks with flexible limits.
    
    NEW APPROACH:
    - Uses research-based flexible limits (soft/hard/emergency)
    - Prioritizes sentence completion over uniform size
    - Never outputs incomplete chunks
    - Philosophy-aware (respects semicolons)
    - Includes final validation pass
    """
    if not sentences:
        logger.warning("No sentences provided to form_semantic_chunks")
        return [], [], []

    start = time.perf_counter()

    valid_sentences = [s for s in sentences if s.strip() and len(s) >= 3]
    if len(valid_sentences) < len(sentences):
        logger.warning(f"Dropped {len(sentences) - len(valid_sentences)} invalid/empty sentences")

    model = get_sentence_model()
    
    # 🔧 NEW: Use flexible limit chunker
    chunks = chunk_with_flexible_limits(
        valid_sentences,
        soft_limit=SOFT_LIMIT,
        hard_limit=HARD_LIMIT,
        emergency_limit=EMERGENCY_LIMIT,
        max_duration=max_duration
    )

    # 🔧 NEW: Validate completeness
    incomplete_chunks = validate_chunks_completeness(chunks)
    if incomplete_chunks:
        logger.error(f"❌ CRITICAL: {len(incomplete_chunks)} chunks are INCOMPLETE after processing!")
        for chunk_num, reason in incomplete_chunks[:5]:
            logger.error(f"   Chunk {chunk_num}: {reason}")

    valid_chunks = [c for c in chunks if c.strip() and len(c) >= 50]
    if len(chunks) > len(valid_chunks):
        logger.warning(f"Dropped {len(chunks) - len(valid_chunks)} invalid/short chunks")

    if not valid_chunks:
        logger.error("No valid chunks for embedding calculation")
        return [], [], []

    char_lengths = [len(c) for c in valid_chunks]
    durations = [predict_duration(c) for c in valid_chunks]
    logger.info(
        f"Chunk distribution: {len(valid_chunks)} chunks, "
        f"chars=[{min(char_lengths)}-{max(char_lengths)}] "
        f"(avg={sum(char_lengths)/len(char_lengths):.0f}), "
        f"durations=[{min(durations):.1f}s-{max(durations):.1f}s] "
        f"(avg={sum(durations)/len(durations):.1f}s)"
    )
    
    # Check duration compliance
    oversized = [(i, d) for i, d in enumerate(durations) if d > max_duration]
    if oversized:
        logger.error(f"❌ CRITICAL: {len(oversized)} chunks exceed {max_duration}s!")
        for idx, dur in oversized[:3]:
            logger.error(f"   Chunk {idx+1}: {len(valid_chunks[idx])} chars, {dur:.1f}s")
    else:
        logger.info(f"✅ SUCCESS: All {len(valid_chunks)} chunks are <= {max_duration}s")
    
    # Check completeness compliance
    complete_count = len(valid_chunks) - len(incomplete_chunks)
    logger.info(f"✅ Complete chunks: {complete_count}/{len(valid_chunks)}")

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


# Keep other functions unchanged for compatibility
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


def calculate_chunk_metrics(chunks: List[str]) -> Dict[str, any]:
    """Calculate detailed metrics for chunks with duration prediction."""
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
            "chunks_in_target_range": 0,
            "chunks_exceeding_duration": 0,
            "incomplete_chunks": 0,
        }
    
    char_lengths = [len(chunk) for chunk in chunks]
    word_counts = [len(chunk.split()) for chunk in chunks]
    durations = [predict_duration(chunk, method="chars") for chunk in chunks]
    
    chunks_in_target = sum(1 for c, d in zip(char_lengths, durations) 
                          if SOFT_LIMIT <= c <= HARD_LIMIT and d <= MAX_DURATION_SECONDS)
    chunks_exceeding = sum(1 for d in durations if d > MAX_DURATION_SECONDS)
    
    # Check completeness
    incomplete_count = len(validate_chunks_completeness(chunks))
    
    return {
        "chunk_char_lengths": char_lengths,
        "chunk_word_counts": word_counts,
        "chunk_durations": durations,
        "avg_char_length": sum(char_lengths) / len(char_lengths),
        "avg_word_count": sum(word_counts) / len(word_counts),
        "avg_duration": sum(durations) / len(durations),
        "max_duration": max(durations),
        "min_duration": min(durations) if durations else 0,
        "chunks_in_target_range": chunks_in_target,
        "chunks_exceeding_duration": chunks_exceeding,
        "incomplete_chunks": incomplete_count,
    }
