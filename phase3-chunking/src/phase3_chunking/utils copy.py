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

# ✅ OPTIMIZED: Chunk size constraints (characters) - Targeting 200-312 chars for <25s duration
MIN_CHUNK_CHARS = 1000 # Lowered to reduce unmergeable shorts
MAX_CHUNK_CHARS = 2000  # ~25s at 750 cpm (MAX_DURATION_SECONDS / 60 * CHARS_PER_MINUTE)
TARGET_CHUNK_CHARS = 1500  # Sweet spot for ~20s

# Duration prediction constants
CHARS_PER_MINUTE = 750  # Average speaking rate (character-based)
WORDS_PER_MINUTE = 150  # Average speaking rate (word-based)
MAX_DURATION_SECONDS = 25  # Target maximum duration to avoid Chatterbox 40s cutoff

def get_nlp():
    """Lazy load spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_lg")
        except OSError:
            logger.warning("en_core_web_lg not found, trying en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
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
    """Detect sentence boundaries using spaCy."""
    if not text or not text.strip():
        logger.warning("Empty text provided to detect_sentences")
        return []

    nlp = get_nlp()
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    logger.info(f"Detected {len(sentences)} sentences")
    return sentences


def split_long_chunk(chunk: str, max_chars: int, max_duration: float) -> List[str]:
    """
    🔧 FIX: Recursively split chunks until ALL sub-chunks are within limits.
    
    Args:
        chunk: Text to split
        max_chars: Maximum characters per chunk
        max_duration: Maximum duration per chunk in seconds
        
    Returns:
        List of sub-chunks, all guaranteed to be <= max_chars and <= max_duration
    """
    def recursive_split(text: str) -> List[str]:
        """Recursively split until within limits."""
        text = text.strip()
        if not text or len(text) < 50:
            return []
        
        current_duration = predict_duration(text)
        
        # Base case: chunk is within limits
        if len(text) <= max_chars and current_duration <= max_duration:
            return [text]
        
        # Recursive case: split and recurse
        words = text.split()
        if len(words) == 1:
            # Single word too long - can't split further, but log warning
            logger.warning(f"Single word exceeds limits: {len(text)} chars, {current_duration:.1f}s")
            return [text]  # Return it anyway as we can't split further
        
        results = []
        current_sub = []
        current_sub_len = 0
        
        for word in words:
            word_len = len(word) + 1  # +1 for space
            test_sub = current_sub + [word]
            test_text = " ".join(test_sub)
            test_duration = predict_duration(test_text)
            
            # Check if adding this word would exceed limits
            if (current_sub_len + word_len > max_chars or test_duration > max_duration) and current_sub:
                # Flush current sub and recurse to ensure it's within limits
                sub_text = " ".join(current_sub)
                results.extend(recursive_split(sub_text))
                current_sub = [word]
                current_sub_len = word_len
            else:
                current_sub.append(word)
                current_sub_len += word_len
        
        # Flush remaining and recurse
        if current_sub:
            sub_text = " ".join(current_sub)
            results.extend(recursive_split(sub_text))
        
        return results
    
    return recursive_split(chunk)


def merge_short_chunks(chunks: List[str], min_chars: int = MIN_CHUNK_CHARS, max_chars: int = MAX_CHUNK_CHARS, max_duration: float = MAX_DURATION_SECONDS) -> List[str]:
    """
    🔧 FIX: Merge short chunks while checking duration to avoid creating oversized chunks.
    
    Args:
        chunks: List of chunks to merge
        min_chars: Minimum characters per chunk
        max_chars: Maximum characters per chunk
        max_duration: Maximum duration per chunk
        
    Returns:
        List of merged chunks
    """
    if not chunks:
        return []
    
    merged = []
    current = ""
    
    for chunk in chunks:
        if not chunk.strip():
            continue
            
        if len(chunk) < min_chars and current:
            # Try merging with current
            test_merged = (current + " " + chunk).strip()
            test_duration = predict_duration(test_merged)
            
            # 🔧 FIX: Check if merge would exceed limits
            if len(test_merged) <= max_chars and test_duration <= max_duration:
                current = test_merged
            else:
                # Can't merge - would exceed limits
                if current:
                    merged.append(current)
                current = chunk
        else:
            # Chunk meets minimum or no current chunk
            if current:
                merged.append(current)
            current = chunk
    
    # Flush final chunk
    if current:
        merged.append(current)
    
    return merged


def _chunk_by_char_count_optimized(
    sentences: List[str], 
    min_chars: int = MIN_CHUNK_CHARS, 
    max_chars: int = MAX_CHUNK_CHARS,
    max_duration: float = MAX_DURATION_SECONDS
) -> List[str]:
    """
    🔧 FIX: Create chunks with STRICT enforcement of max_chars and max_duration limits.
    
    Strategy:
    1. Build chunks by adding sentences while staying below limits
    2. Recursively split ANY chunk that exceeds limits
    3. Drop sub-chunks <50 chars with warnings
    4. Enforce limits at every step
    
    Args:
        sentences: List of sentences to chunk
        min_chars: Minimum characters per chunk (default 200)
        max_chars: Maximum characters per chunk (default 312)
        max_duration: Maximum predicted duration per chunk (default 25s)
        
    Returns:
        List of chunks, ALL guaranteed to be <= max_chars and <= max_duration
    """
    chunks = []
    current_chunk = []
    current_char_count = 0
    
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
            
        sent_len = len(sent)
        sent_duration = predict_duration(sent)
        
        # Handle oversized sentence - split immediately
        if sent_len > max_chars or sent_duration > max_duration:
            logger.warning(
                f"Sentence exceeds limits ({sent_len} chars, {sent_duration:.1f}s), splitting"
            )
            
            # Flush current chunk first
            if current_chunk and current_char_count >= min_chars:
                chunk_text = " ".join(current_chunk)
                chunk_duration = predict_duration(chunk_text)
                
                if len(chunk_text) <= max_chars and chunk_duration <= max_duration:
                    chunks.append(chunk_text)
                else:
                    # 🔧 FIX: Recursively split if still too long
                    chunks.extend(split_long_chunk(chunk_text, max_chars, max_duration))
                
                current_chunk = []
                current_char_count = 0
            
            # Split oversized sentence recursively
            chunks.extend(split_long_chunk(sent, max_chars, max_duration))
            continue
        
        # Try adding sentence to current chunk
        test_chunk = current_chunk + [sent]
        test_text = " ".join(test_chunk)
        test_len = len(test_text)
        test_duration = predict_duration(test_text)
        
        # Check if adding would exceed limits
        if test_len > max_chars or test_duration > max_duration:
            # Flush current chunk if it meets minimum
            if current_chunk and current_char_count >= min_chars:
                chunk_text = " ".join(current_chunk)
                chunk_duration = predict_duration(chunk_text)
                
                # 🔧 FIX: Double-check limits before adding
                if len(chunk_text) <= max_chars and chunk_duration <= max_duration:
                    chunks.append(chunk_text)
                else:
                    chunks.extend(split_long_chunk(chunk_text, max_chars, max_duration))
                
                current_chunk = [sent]
                current_char_count = sent_len
            else:
                # Current chunk too small, but adding sentence exceeds limits
                # 🔧 FIX: Split the combined text
                if current_chunk:
                    test_text = " ".join(current_chunk + [sent])
                    chunks.extend(split_long_chunk(test_text, max_chars, max_duration))
                else:
                    # Just this sentence, already handled above
                    chunks.extend(split_long_chunk(sent, max_chars, max_duration))
                
                current_chunk = []
                current_char_count = 0
        else:
            # Adding sentence keeps us within limits
            current_chunk.append(sent)
            current_char_count = test_len
            
            # 🔧 FIX: Flush if we're in the optimal range (>= min and <= max)
            if current_char_count >= min_chars:
                chunk_text = " ".join(current_chunk)
                chunk_duration = predict_duration(chunk_text)
                
                if chunk_duration <= max_duration and len(chunk_text) <= max_chars:
                    chunks.append(chunk_text)
                    current_chunk = []
                    current_char_count = 0
    
    # Flush final chunk
    if current_chunk and current_char_count >= min_chars:
        final_text = " ".join(current_chunk)
        final_duration = predict_duration(final_text)
        
        if len(final_text) <= max_chars and final_duration <= max_duration:
            chunks.append(final_text)
        else:
            # 🔧 FIX: Split if over limits
            chunks.extend(split_long_chunk(final_text, max_chars, max_duration))
    elif current_chunk:
        # Final chunk is too short but has content
        final_text = " ".join(current_chunk)
        if len(final_text) >= 50:  # Keep if at least 50 chars
            # Try to merge with last chunk if possible
            if chunks:
                test_merged = chunks[-1] + " " + final_text
                test_duration = predict_duration(test_merged)
                
                if len(test_merged) <= max_chars and test_duration <= max_duration:
                    chunks[-1] = test_merged
                else:
                    chunks.append(final_text)  # Add as-is, will be handled in merge
            else:
                chunks.append(final_text)
    
    return chunks


def form_semantic_chunks(
    sentences: List[str], 
    min_chars: int = MIN_CHUNK_CHARS, 
    max_chars: int = MAX_CHUNK_CHARS,
    max_duration: float = MAX_DURATION_SECONDS
) -> Tuple[List[str], List[float], List[List[float]]]:
    """
    Form semantic chunks with STRICT 200-312 char and <=25s duration enforcement.
    
    🔧 FIXES APPLIED:
    - Recursive splitting ensures NO chunks exceed limits
    - Merge function checks duration to avoid creating oversized chunks
    - Better sentence model (all-mpnet-base-v2) for improved coherence
    """
    if not sentences:
        logger.warning("No sentences provided to form_semantic_chunks")
        return [], [], []

    start = time.perf_counter()

    valid_sentences = [s for s in sentences if s.strip() and len(s) >= 3]
    if len(valid_sentences) < len(sentences):
        logger.warning(f"Dropped {len(sentences) - len(valid_sentences)} invalid/empty sentences")

    model = get_sentence_model()
    
    chunks = _chunk_by_char_count_optimized(
        valid_sentences, 
        min_chars, 
        max_chars, 
        max_duration
    )

    # 🔧 FIX: Merge with duration checking
    chunks = merge_short_chunks(chunks, min_chars, max_chars, max_duration)

    valid_chunks = [c for c in chunks if c.strip() and len(c) >= 50]
    if len(chunks) > len(valid_chunks):
        logger.warning(f"Dropped {len(chunks) - len(valid_chunks)} invalid/short chunks after merging")

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
    
    # 🔧 FIX: Verify NO chunks exceed limits
    oversized = [(i, d) for i, d in enumerate(durations) if d > max_duration]
    if oversized:
        logger.error(
            f"❌ CRITICAL: {len(oversized)} chunks STILL exceed {max_duration}s after fixes!"
        )
        for idx, dur in oversized[:3]:
            logger.error(f"   Chunk {idx+1}: {len(valid_chunks[idx])} chars, {dur:.1f}s")
    else:
        logger.info(f"✅ SUCCESS: All {len(valid_chunks)} chunks are <= {max_duration}s")

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

    if avg_coherence < 0.87:
        logger.warning(f"Low coherence ({avg_coherence:.4f}), checking Jaccard fallback")
        jaccard_scores = []
        for i in range(len(valid_chunks) - 1):
            words1 = set(valid_chunks[i].split())
            words2 = set(valid_chunks[i+1].split())
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            jaccard = intersection / union if union else 0
            jaccard_scores.append(jaccard)
        avg_jaccard = sum(jaccard_scores) / len(jaccard_scores) if jaccard_scores else 0

        if avg_jaccard > 0.4:
            logger.info(f"Jaccard similarity ({avg_jaccard:.4f}) acceptable, keeping chunks")
        else:
            logger.warning(f"Both coherence ({avg_coherence:.4f}) and Jaccard ({avg_jaccard:.4f}) are low")

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


def log_chunk_times(chunks: List[str]):
    """
    Log processing time and size metrics for each chunk with duration prediction.
    """
    for i, chunk in enumerate(chunks):
        start = time.perf_counter()
        word_count = len(chunk.split())
        char_count = len(chunk)
        duration = predict_duration(chunk, method="chars")
        elapsed = time.perf_counter() - start
        
        if MIN_CHUNK_CHARS <= char_count <= MAX_CHUNK_CHARS and duration <= MAX_DURATION_SECONDS:
            status = "✓ OPTIMAL"
        elif char_count < MIN_CHUNK_CHARS:
            status = "⚠️  SHORT"
        elif duration > MAX_DURATION_SECONDS:
            status = "❌ TOO LONG"
        else:
            status = "⚠️  OVERSIZED"
        
        logger.debug(
            f"Chunk {i+1}: {word_count} words, {char_count} chars, "
            f"~{duration:.1f}s duration, processed in {elapsed:.4f}s [{status}]"
        )
        
        if duration > MAX_DURATION_SECONDS:
            logger.warning(
                f"Chunk {i+1} duration ({duration:.1f}s) exceeds target ({MAX_DURATION_SECONDS}s)"
            )


def calculate_chunk_metrics(chunks: List[str]) -> Dict[str, any]:
    """
    Calculate detailed metrics for chunks with duration prediction.
    
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
            "chunks_in_target_range": 0,
            "chunks_exceeding_duration": 0,
        }
    
    char_lengths = [len(chunk) for chunk in chunks]
    word_counts = [len(chunk.split()) for chunk in chunks]
    durations = [predict_duration(chunk, method="chars") for chunk in chunks]
    
    chunks_in_target = sum(1 for c, d in zip(char_lengths, durations) 
                          if MIN_CHUNK_CHARS <= c <= MAX_CHUNK_CHARS and d <= MAX_DURATION_SECONDS)
    chunks_exceeding = sum(1 for d in durations if d > MAX_DURATION_SECONDS)
    
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
    }
