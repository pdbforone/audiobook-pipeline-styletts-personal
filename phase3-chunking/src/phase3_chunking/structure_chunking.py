"""
Intelligent Chunking Using Document Structure

Uses structure metadata from Phase 2 to create natural chapter/section-based chunks
instead of arbitrary word-count boundaries.

Falls back to fixed chunking if no structure is available.
"""

import logging
from typing import List, Tuple, Optional

# Smart import: works both as script and as module
try:
    from .models import ValidationConfig
    from .utils import assess_readability
except ImportError:
    pass

logger = logging.getLogger(__name__)


def is_toc_section(node: dict) -> bool:
    """
    Detect if a structure node is a table of contents entry.

    TOC characteristics:
    - Short text (<200 chars)
    - Contains Roman numerals (I., II., III.) or Arabic (1., 2., 3.)
    - Matches pattern: number + period + short text
    - Level 1 or 2 headings with very short text

    Args:
        node: Structure node from Phase 2

    Returns:
        True if node appears to be a TOC entry, False otherwise
    """
    import re

    title = node.get("title", "")
    text = node.get("text", "")
    level = node.get("level", 999)

    # Patterns that indicate TOC entries
    toc_patterns = [
        r"^[IVX]+\.",  # Roman numerals: I., II., III., IV., V.
        r"^\d+\.",  # Arabic numbers: 1., 2., 3.
        r"^Chapter \d+",  # "Chapter 1", "Chapter 2"
        r"Contents?",  # "Content" or "Contents"
        r"^Part [IVX\d]+",  # "Part I", "Part 1"
    ]

    # Check text length
    char_count = len(text) if text else len(title)

    # Check if matches TOC pattern
    text_to_check = title if title else text
    has_toc_pattern = any(
        re.match(pat, text_to_check, re.I) for pat in toc_patterns
    )

    # TOC entries are typically:
    # - Very short (<200 chars)
    # - Have TOC patterns
    # OR
    # - High-level headings (1-2) with minimal text (<150 chars)

    is_toc = (char_count < 200 and has_toc_pattern) or (
        level <= 2 and char_count < 150
    )

    if is_toc:
        logger.debug(
            f"Identified TOC entry: '{text_to_check[:50]}...' ({char_count} chars, level {level})"
        )

    return is_toc


def chunk_by_structure(
    text: str,
    structure: List[dict],
    profile,
    max_chunk_words: Optional[int] = None,  # Tuned for ~12–18s CPU chunks
    target_sec: float = 15.0,
    soft_merge_sec: float = 8.0,
    words_per_minute: float = 150.0,
    use_embeddings: bool = False,
) -> Tuple[List[str], List[float], List]:
    """
    Create chunks based on document structure (chapters/sections).

    Strategy:
    1. Use chapter/section boundaries from Phase 2 structure detection
    2. If a section is small (<max_chunk_words), use it as-is
    3. If a section is large (>max_chunk_words), split it into subsections
    4. Target: Natural boundaries while preventing Phase 4 timeouts

    Args:
        text: Full document text
        structure: List of structure nodes from Phase 2
        config: Validation config with thresholds
        max_chunk_words: Maximum words per chunk (default 70)

    Returns:
        Tuple of (chunks, coherence_scores, embeddings)
    """
    chunks = []
    coherence_scores = []
    target_profile = getattr(profile, "name", "structure")
    profile_overrides = getattr(profile, "genre_duration_overrides", {}) or {}

    # Apply duration overrides when available
    if target_profile in profile_overrides:
        overrides = profile_overrides[target_profile]
        target_sec = overrides.get("target_duration", target_sec)
        soft_merge_sec = min(soft_merge_sec, max(4.0, target_sec / 2))
        logger.info(
            f"Applying duration overrides for {target_profile}: "
            f"target={target_sec}s, max={overrides.get('max_duration', 'n/a')}s"
        )

    # Filter out TOC entries to prevent tiny chunks
    filtered_structure = [
        node for node in structure if not is_toc_section(node)
    ]
    toc_count = len(structure) - len(filtered_structure)

    if toc_count > 0:
        logger.info(
            f"Filtered out {toc_count} TOC entries (preventing tiny chunks)"
        )

    logger.info(
        f"Creating chunks from {len(filtered_structure)} structure nodes"
    )
    logger.info(f"Max words per chunk: {max_chunk_words}")

    def estimate_duration(text_value: str) -> float:
        words = len(text_value.split())
        return (words / words_per_minute) * 60.0

    # Load embedding model for coherence calculation (optional)
    model = None
    if use_embeddings:
        try:
            from sentence_transformers import (
                SentenceTransformer,
            )  # Lazy import
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Could not load embedding model: {exc}")
            model = None
        else:
            model = SentenceTransformer("all-MiniLM-L6-v2")

    for i, node in enumerate(filtered_structure):
        # Extract section text
        start = node.get("char_offset", 0)
        end = node.get("char_end", len(text))
        section_text = text[start:end].strip()

        if not section_text:
            logger.warning(
                f"Empty section at node {i}: {node.get('title', 'Unknown')}"
            )
            continue

        word_count = len(section_text.split())
        title = node.get("title", f"Section {i+1}")
        level = node.get("level", 1)

        logger.info(f"Processing: {title} (Level {level}, {word_count} words)")
        dynamic_max_words = max_chunk_words or getattr(
            profile, "max_words", 70
        )

        if (
            word_count <= dynamic_max_words
            and estimate_duration(section_text) <= target_sec * 1.3
        ):
            # Section is small enough - use as-is
            chunks.append(section_text)

            # Calculate coherence (simplified - just check if it's a reasonable chunk)
            if model:
                try:
                    embedding = model.encode([section_text])
                    coherence = (
                        0.9  # Assume high coherence for natural sections
                    )
                except:
                    coherence = 0.85
            else:
                coherence = 0.85

            coherence_scores.append(coherence)
            logger.info(f"  → Created 1 chunk ({word_count} words)")

        else:
            # Section is too large - split by paragraphs
            logger.info(
                f"  → Section exceeds {max_chunk_words} words, splitting..."
            )

            paragraphs = section_text.split("\n\n")
            current_chunk = ""
            sub_chunk_count = 0

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # Check if adding this paragraph exceeds limit
                test_chunk = (current_chunk + "\n\n" + para).strip()
                test_word_count = len(test_chunk.split())

                if test_word_count <= max_chunk_words:
                    # Add to current chunk
                    current_chunk = test_chunk
                else:
                    # Save current chunk and start new one
                    if current_chunk:
                        chunks.append(current_chunk)
                        coherence_scores.append(0.85)  # Assumed coherence
                        sub_chunk_count += 1
                        logger.info(
                            f"    → Sub-chunk {sub_chunk_count}: {len(current_chunk.split())} words"
                        )

                    current_chunk = para

            # Add final chunk
            if current_chunk:
                chunks.append(current_chunk)
                coherence_scores.append(0.85)
                sub_chunk_count += 1
                logger.info(
                    f"    → Sub-chunk {sub_chunk_count}: {len(current_chunk.split())} words"
                )

            logger.info(f"  → Split into {sub_chunk_count} chunks")

    # Softening: merge very short chunks to reduce seams
    softened_chunks = []
    softened_coherence = []
    i = 0
    while i < len(chunks):
        current = chunks[i]
        current_dur = estimate_duration(current)
        if i + 1 < len(chunks) and current_dur < soft_merge_sec:
            merged_text = current + " " + chunks[i + 1]
            merged_dur = current_dur + estimate_duration(chunks[i + 1])
            softened_chunks.append(merged_text.strip())
            softened_coherence.append(0.85)
            i += 2
        else:
            softened_chunks.append(current)
            softened_coherence.append(
                coherence_scores[i] if i < len(coherence_scores) else 0.85
            )
            i += 1

    chunks = softened_chunks
    coherence_scores = softened_coherence

    # Generate embeddings
    embeddings = []
    if model:
        try:
            import numpy as np  # Lazy import to avoid overhead when not needed
        except Exception:  # noqa: BLE001
            np = None

        try:
            embeddings = [model.encode([chunk])[0] for chunk in chunks]
            logger.info(f"Generated embeddings for {len(chunks)} chunks")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Could not generate embeddings: {e}")
            embeddings = (
                [np.zeros(384) for _ in chunks] if np is not None else []
            )
    else:
        embeddings = []

    logger.info(f"Final result: {len(chunks)} chunks created from structure")
    if not use_embeddings:
        coherence_scores = []
    if embeddings and hasattr(embeddings[0], "tolist"):
        embeddings = [emb.tolist() for emb in embeddings]

    return chunks, coherence_scores, embeddings


def should_use_structure_chunking(
    structure: List[dict], min_sections: int = 3
) -> bool:
    """
    Determine if structure data is good enough to use for chunking.

    Args:
        structure: Structure metadata from Phase 2
        min_sections: Minimum number of sections required

    Returns:
        True if structure should be used, False to fall back to fixed chunking
    """
    if not structure or len(structure) < min_sections:
        logger.info(
            f"Not enough structure data ({len(structure) if structure else 0} sections), using fixed chunking"
        )
        return False

    # Filter out TOC entries before validation
    non_toc_structure = [
        node for node in structure if not is_toc_section(node)
    ]

    if len(non_toc_structure) < min_sections:
        logger.info(
            f"After filtering TOC, only {len(non_toc_structure)} sections remain "
            f"(need {min_sections}), using fixed chunking"
        )
        return False

    # Check if sections have reasonable boundaries
    valid_sections = sum(
        1
        for node in non_toc_structure
        if node.get("char_offset", 0) < node.get("char_end", 0)
    )

    if valid_sections < min_sections:
        logger.info(
            f"Only {valid_sections} valid sections found (after TOC filtering), "
            f"using fixed chunking"
        )
        return False

    logger.info(
        f"Structure data looks good ({valid_sections} valid sections after filtering "
        f"{len(structure) - len(non_toc_structure)} TOC entries), "
        f"will use structure-based chunking"
    )
    return True
