"""
Deduplication Utilities for Phase 2 Extraction

Defense-in-depth safeguard against consecutive text duplication from any source:
- Control flow bugs in extractors
- Retry side-effects
- Library parsing artifacts (Textract LAYOUT vs LINE)
- Stream management issues

This module provides lightweight deduplication that protects downstream phases
(Chunking, TTS) from redundancy regardless of upstream cause.
"""

import hashlib
import logging
from typing import Iterable, Iterator, List, Optional

logger = logging.getLogger(__name__)


def dedupe_consecutive(
    iterable: Iterable[str],
    min_length: int = 10,
    log_duplicates: bool = True
) -> Iterator[str]:
    """
    Remove adjacent duplicate text blocks using content hash.

    This is a defense-in-depth safety net that sanitizes the pattern:
        ["Para A", "Para A", "Para B", "Para B"] → ["Para A", "Para B"]

    Args:
        iterable: Sequence of text blocks (lines, paragraphs, chunks)
        min_length: Minimum text length to check (skip very short strings)
        log_duplicates: Whether to log when duplicates are detected

    Yields:
        Non-duplicate text blocks in original order

    Example:
        >>> text_blocks = ["Intro.", "Intro.", "Body.", "Body.", "End."]
        >>> clean = list(dedupe_consecutive(text_blocks))
        >>> clean
        ['Intro.', 'Body.', 'End.']

    Note:
        - Uses SHA-256 hash for content comparison (fast, memory-efficient)
        - Only removes *consecutive* duplicates (preserves legitimate repetition)
        - Logs warning if duplicates detected (indicates upstream bug)
    """
    prev_hash: Optional[bytes] = None
    duplicate_count = 0
    total_count = 0

    for item in iterable:
        total_count += 1

        # Skip deduplication for very short strings (empty lines, etc.)
        if len(item) < min_length:
            yield item
            prev_hash = None  # Reset hash chain
            continue

        # Compute content hash
        curr_hash = hashlib.sha256(item.encode('utf-8', errors='ignore')).digest()

        # Yield only if different from previous
        if curr_hash != prev_hash:
            yield item
            prev_hash = curr_hash
        else:
            duplicate_count += 1
            if log_duplicates and duplicate_count == 1:
                # Log first occurrence to avoid spam
                logger.warning(
                    f"Consecutive duplicate detected in text stream. "
                    f"Preview: {item[:100]}..."
                )

    # Summary logging
    if duplicate_count > 0:
        logger.warning(
            f"⚠️  Removed {duplicate_count} consecutive duplicates "
            f"from {total_count} total blocks ({duplicate_count/total_count:.1%})"
        )
        logger.warning(
            "This indicates a bug in upstream extraction. "
            "Check extractors/txt.py, epub.py, etc. for control flow errors."
        )


def dedupe_paragraphs(text: str, min_para_length: int = 20) -> str:
    """
    Remove consecutive duplicate paragraphs from full text.

    Convenience wrapper around dedupe_consecutive for paragraph-level text.

    Args:
        text: Full text with paragraphs separated by double newlines
        min_para_length: Minimum paragraph length to check

    Returns:
        Text with consecutive duplicate paragraphs removed

    Example:
        >>> text = "Para A.\\n\\nPara A.\\n\\nPara B.\\n\\nPara B."
        >>> dedupe_paragraphs(text)
        'Para A.\\n\\nPara B.'
    """
    # Split on double newlines (paragraph breaks)
    paragraphs = text.split('\n\n')

    # Deduplicate
    clean_paragraphs = list(dedupe_consecutive(
        paragraphs,
        min_length=min_para_length,
        log_duplicates=True
    ))

    # Rejoin
    return '\n\n'.join(clean_paragraphs)


def dedupe_lines(text: str, min_line_length: int = 5) -> str:
    """
    Remove consecutive duplicate lines from full text.

    Convenience wrapper around dedupe_consecutive for line-level text.

    Args:
        text: Full text with lines separated by single newlines
        min_line_length: Minimum line length to check

    Returns:
        Text with consecutive duplicate lines removed

    Example:
        >>> text = "Line A\\nLine A\\nLine B\\nLine B"
        >>> dedupe_lines(text)
        'Line A\\nLine B'
    """
    lines = text.split('\n')

    clean_lines = list(dedupe_consecutive(
        lines,
        min_length=min_line_length,
        log_duplicates=True
    ))

    return '\n'.join(clean_lines)


def validate_no_duplicates(
    text_blocks: List[str],
    max_consecutive_duplicates: int = 0
) -> tuple[bool, List[int]]:
    """
    Validate that text stream contains no (or few) consecutive duplicates.

    Useful for testing and quality assurance.

    Args:
        text_blocks: List of text segments to validate
        max_consecutive_duplicates: Maximum allowed consecutive duplicates

    Returns:
        (is_valid, duplicate_indices) where duplicate_indices lists positions
        of detected duplicates

    Example:
        >>> blocks = ["A", "A", "B", "C", "C"]
        >>> is_valid, indices = validate_no_duplicates(blocks, max_consecutive_duplicates=0)
        >>> is_valid
        False
        >>> indices
        [1, 4]  # Positions where duplicates occurred
    """
    duplicate_indices = []
    prev_hash = None

    for i, block in enumerate(text_blocks):
        curr_hash = hashlib.sha256(block.encode('utf-8', errors='ignore')).digest()

        if curr_hash == prev_hash:
            duplicate_indices.append(i)

        prev_hash = curr_hash

    is_valid = len(duplicate_indices) <= max_consecutive_duplicates

    return is_valid, duplicate_indices


__all__ = [
    'dedupe_consecutive',
    'dedupe_paragraphs',
    'dedupe_lines',
    'validate_no_duplicates',
]
