"""
Auto-classification logic for detecting genre from text patterns.

Uses rule-based heuristics to classify text into genres:
- Philosophy: Long sentences, abstract concepts
- Fiction: Dialogue, narrative past tense
- Academic: Citations, formal language, lists
- Memoir: First-person, anecdotes
- Technical: Instructions, code, formulas
"""

import re
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def detect_genre(
    text: str, metadata: Optional[Dict] = None
) -> Tuple[str, float, Dict[str, float]]:
    """
    Detect genre from text using rule-based heuristics.

    Args:
        text: Full text to analyze
        metadata: Optional metadata dict with 'title', 'author', etc.

    Returns:
        Tuple of (genre_name, confidence, all_scores)

    Example:
        >>> genre, conf, scores = detect_genre(text, {'title': 'Meditations'})
        >>> print(f"{genre} (confidence: {conf:.2f})")
        philosophy (confidence: 0.85)
    """
    if not text or len(text.strip()) < 100:
        logger.warning("Text too short for reliable genre detection")
        return "auto", 0.0, {}

    metadata = metadata or {}

    # Initialize scores
    scores = {
        "philosophy": 0.0,
        "fiction": 0.0,
        "academic": 0.0,
        "memoir": 0.0,
        "technical": 0.0,
    }

    # 1. Metadata-based detection (keywords in title/author)
    meta_text = (
        f"{metadata.get('title', '')} {metadata.get('author', '')}".lower()
    )

    # Philosophy indicators
    if any(
        term in meta_text
        for term in [
            "philosophy",
            "meditations",
            "ethics",
            "metaphysics",
            "epistemology",
        ]
    ):
        scores["philosophy"] += 0.3
        logger.debug("Metadata suggests philosophy")

    # Fiction indicators
    if any(
        term in meta_text
        for term in ["novel", "fiction", "story", "tales", "narrative"]
    ):
        scores["fiction"] += 0.3
        logger.debug("Metadata suggests fiction")

    # Academic indicators
    if any(
        term in meta_text
        for term in [
            "introduction",
            "textbook",
            "studies",
            "research",
            "theory",
        ]
    ):
        scores["academic"] += 0.3
        logger.debug("Metadata suggests academic")

    # Memoir indicators
    if any(
        term in meta_text
        for term in ["memoir", "autobiography", "journal", "diary", "life of"]
    ):
        scores["memoir"] += 0.3
        logger.debug("Metadata suggests memoir")

    # Technical indicators
    if any(
        term in meta_text
        for term in ["manual", "guide", "handbook", "tutorial", "programming"]
    ):
        scores["technical"] += 0.3
        logger.debug("Metadata suggests technical")

    # 2. Text-based analysis
    # Sample text for efficiency (use first 5000 chars)
    sample = text[:5000]
    sentences = sample.split(".")
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        logger.warning("No sentences detected in sample")
        return "auto", 0.0, scores

    # Calculate text statistics
    avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)
    quote_count = sample.count('"') + sample.count('"') + sample.count('"')
    quote_ratio = quote_count / len(sample) if sample else 0

    # Count specific markers
    first_person_count = len(
        re.findall(r"\b(I|my|me|mine)\b", sample, re.IGNORECASE)
    )
    first_person_ratio = (
        first_person_count / len(sample.split()) if sample else 0
    )

    dialogue_tags = len(
        re.findall(
            r"\b(said|replied|asked|answered|exclaimed|whispered)\b",
            sample,
            re.IGNORECASE,
        )
    )
    dialogue_ratio = dialogue_tags / len(sentences) if sentences else 0

    citation_count = len(
        re.findall(r"\([A-Z][a-z]+,?\s+\d{4}\)", sample)
    )  # (Author, YEAR)
    citation_ratio = citation_count / len(sentences) if sentences else 0

    code_markers = len(
        re.findall(r"```|def\s+\w+\(|function\s+\w+|class\s+\w+", sample)
    )
    formula_markers = len(re.findall(r"\$.*?\$|\\[a-z]+{", sample))

    # 3. Apply heuristics

    # Philosophy: Long sentences, abstract concepts
    if avg_sentence_len > 25:
        scores["philosophy"] += 0.2
        logger.debug(
            f"Long sentences ({avg_sentence_len:.1f} avg) suggest philosophy/academic"
        )

        # Distinguish philosophy from academic
        abstract_terms = len(
            re.findall(
                r"\b(being|existence|nature|essence|truth|virtue|wisdom|knowledge|reality)\b",
                sample,
                re.IGNORECASE,
            )
        )
        if abstract_terms > 5:
            scores["philosophy"] += 0.2
            logger.debug("Abstract philosophical terms detected")
        else:
            scores["academic"] += 0.1

    # Fiction: High quote ratio, dialogue tags
    if quote_ratio > 0.05:
        scores["fiction"] += 0.3
        logger.debug(f"High quote ratio ({quote_ratio:.3f}) suggests fiction")

    if dialogue_ratio > 0.1:
        scores["fiction"] += 0.2
        logger.debug(f"Dialogue tags ({dialogue_ratio:.3f}) suggest fiction")

    # Academic: Citations, formal language, numbered lists
    if citation_ratio > 0.05:
        scores["academic"] += 0.3
        logger.debug(f"Citations detected ({citation_ratio:.3f})")

    formal_indicators = len(
        re.findall(
            r"\b(therefore|thus|however|furthermore|moreover|consequently)\b",
            sample,
            re.IGNORECASE,
        )
    )
    if formal_indicators > 3:
        scores["academic"] += 0.15
        logger.debug("Formal academic language detected")

    # Lists/enumerations
    list_markers = len(
        re.findall(r"^\s*\d+\.|^\s*[a-z]\)", sample, re.MULTILINE)
    )
    if list_markers > 3:
        scores["academic"] += 0.1
        scores["technical"] += 0.1
        logger.debug("Enumerated lists detected")

    # Memoir: First-person narrative
    if first_person_ratio > 0.03:
        scores["memoir"] += 0.3
        logger.debug(
            f"First-person narrative ({first_person_ratio:.3f}) suggests memoir"
        )

    # Check for anecdotal style
    anecdote_markers = len(
        re.findall(
            r"\b(remember|recall|once|when I was|looking back)\b",
            sample,
            re.IGNORECASE,
        )
    )
    if anecdote_markers > 2:
        scores["memoir"] += 0.15
        logger.debug("Anecdotal style detected")

    # Technical: Code blocks, formulas, instructional language
    if code_markers > 0 or formula_markers > 2:
        scores["technical"] += 0.4
        logger.debug(
            f"Code/formulas detected (code: {code_markers}, formulas: {formula_markers})"
        )

    instruction_markers = len(
        re.findall(
            r"\b(step|first|next|then|finally|install|configure|run)\b",
            sample,
            re.IGNORECASE,
        )
    )
    if instruction_markers > 5:
        scores["technical"] += 0.2
        logger.debug("Instructional language detected")

    # 4. Determine winner
    if not scores or max(scores.values()) == 0:
        logger.warning("No clear genre detected, defaulting to 'auto'")
        return "auto", 0.0, scores

    winner = max(scores, key=scores.get)
    confidence = scores[winner]

    # Normalize confidence to 0-1 range
    confidence = min(1.0, confidence)

    # If confidence too low, use 'auto'
    if confidence < 0.3:
        logger.warning(
            f"Low genre confidence ({confidence:.2f}), using 'auto' profile"
        )
        return "auto", confidence, scores

    logger.info(f"Detected genre: {winner} (confidence: {confidence:.2f})")
    logger.debug(f"All scores: {scores}")

    return winner, confidence, scores


def get_genre_from_metadata(metadata: Dict) -> Optional[str]:
    """
    Extract genre hint from metadata if explicitly provided.

    Args:
        metadata: Metadata dict from Phase 2

    Returns:
        Genre name if found, None otherwise
    """
    if not metadata:
        return None

    # Check for explicit genre hint
    if "suggested_tts_profile" in metadata:
        profile = metadata["suggested_tts_profile"].lower()
        logger.info(f"Using explicit genre hint from Phase 2: {profile}")
        return profile

    if "detected_genre_hints" in metadata:
        hints = metadata["detected_genre_hints"]
        if hints and isinstance(hints, list) and len(hints) > 0:
            logger.info(f"Using genre hint from Phase 2: {hints[0]}")
            return hints[0]

    return None


def validate_genre(genre: str) -> bool:
    """
    Check if a genre name is valid.

    Args:
        genre: Genre name to validate

    Returns:
        True if valid, False otherwise
    """
    valid_genres = {
        "philosophy",
        "fiction",
        "academic",
        "memoir",
        "technical",
        "auto",
    }
    return genre.lower() in valid_genres


# Export
__all__ = [
    "detect_genre",
    "get_genre_from_metadata",
    "validate_genre",
]
