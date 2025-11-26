"""
DOCX Text Extractor

Extracts text from Microsoft Word documents while preserving:
- Heading structure (for potential chapter detection)
- Paragraph hierarchy
- Document metadata (title, author)

Reason: Preserving document structure helps with later chunking decisions
and maintaining narrative flow for TTS.
"""

from pathlib import Path
from typing import Tuple, Dict
import logging

try:
    from docx import Document

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract(path: Path) -> Tuple[str, Dict]:
    """
    Extract text from DOCX file with structure preservation.

    Args:
        path: Path to DOCX file

    Returns:
        (text, metadata) where text includes heading tags and metadata
        contains document properties

    Reason: Heading tags (<HEADING:1>, etc.) allow chunker to respect
    document structure and avoid splitting mid-section.
    """
    if not DOCX_AVAILABLE:
        error_msg = "python-docx library not available. Install with: poetry add python-docx"
        logger.error(error_msg)
        return "", {
            "title": path.stem,
            "error": error_msg,
            "quality_score": 0.0,
        }

    logger.info(f"Extracting DOCX: {path.name}")

    try:
        doc = Document(str(path))
        text_parts = []
        heading_count = 0
        paragraph_count = 0

        # Extract paragraphs with structure markers
        for para in doc.paragraphs:
            para_text = para.text.strip()

            if not para_text:
                # Preserve paragraph breaks for readability
                continue

            # Check if this is a heading
            if para.style.name.startswith("Heading"):
                # Extract heading level (Heading 1 -> 1, Heading 2 -> 2, etc.)
                try:
                    level = para.style.name.split()[-1]
                    if level.isdigit():
                        text_parts.append(f"<HEADING:{level}> {para_text}")
                        heading_count += 1
                        logger.debug(
                            f"Found heading level {level}: {para_text[:50]}..."
                        )
                    else:
                        text_parts.append(para_text)
                except Exception as exc:
                    logger.debug("Failed to parse heading level: %s", exc)
                    text_parts.append(para_text)
            else:
                text_parts.append(para_text)
                paragraph_count += 1

        text = "\n".join(filter(None, text_parts))

        # Extract document metadata
        metadata = {
            "title": doc.core_properties.title or path.stem,
            "author": doc.core_properties.author or "Unknown",
            "char_count": len(text),
            "heading_count": heading_count,
            "paragraph_count": paragraph_count,
        }

        # Optional metadata if available
        if doc.core_properties.subject:
            metadata["subject"] = doc.core_properties.subject
        if doc.core_properties.keywords:
            metadata["keywords"] = doc.core_properties.keywords

        # Quality assessment
        if not text.strip():
            logger.warning("No text extracted from DOCX")
            metadata["quality_score"] = 0.0
            metadata["error"] = "Empty document"
        elif len(text) < 100:
            logger.warning(f"Very short document: {len(text)} chars")
            metadata["quality_score"] = 0.5
        else:
            metadata["quality_score"] = 1.0
            logger.info(
                f"✓ Extracted {len(text):,} chars, {heading_count} headings, {paragraph_count} paragraphs"
            )

        return text, metadata

    except Exception as e:
        logger.error(f"DOCX extraction failed: {type(e).__name__}: {e}")
        return "", {
            "title": path.stem,
            "error": f"Extraction failed: {type(e).__name__}: {str(e)}",
            "quality_score": 0.0,
        }
