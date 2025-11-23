"""
EPUB Text Extractor

Extracts text from EPUB ebooks while preserving:
- Chapter structure
- HTML formatting removal
- Reading order

Reason: EPUBs are structured HTML; preserving chapter boundaries
helps create natural TTS chunks that align with the book's structure.
"""

from pathlib import Path
from typing import Tuple, Dict
import logging

try:
    from ebooklib import epub

    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract(path: Path) -> Tuple[str, Dict]:
    """
    Extract text from EPUB file with chapter preservation.

    Args:
        path: Path to EPUB file

    Returns:
        (text, metadata) where text includes chapter markers and metadata
        contains book information

    Reason: Chapter markers (<CHAPTER:id>) allow the chunker to avoid
    splitting across chapter boundaries, maintaining narrative coherence.
    """
    if not EPUB_AVAILABLE:
        error_msg = (
            "ebooklib library not available. Install with: poetry add ebooklib"
        )
        logger.error(error_msg)
        return "", {
            "title": path.stem,
            "error": error_msg,
            "quality_score": 0.0,
        }

    if not BS4_AVAILABLE:
        error_msg = "beautifulsoup4 library not available. Install with: poetry add beautifulsoup4"
        logger.error(error_msg)
        return "", {
            "title": path.stem,
            "error": error_msg,
            "quality_score": 0.0,
        }

    logger.info(f"Extracting EPUB: {path.name}")

    try:
        book = epub.read_epub(str(path))
        chapters = []
        chapter_count = 0

        # Extract all document items (chapters, sections, etc.)
        for item in book.get_items_of_type(epub.ITEM_DOCUMENT):
            # Parse HTML content
            content = item.get_body_content()
            if not content:
                continue

            try:
                soup = BeautifulSoup(content, "html.parser")

                # Remove script and style tags
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get text
                chapter_text = soup.get_text(separator="\n", strip=True)

                if chapter_text.strip():
                    # Add chapter marker with item ID for reference
                    item_id = item.get_id() or f"chapter_{chapter_count}"
                    chapters.append(f"<CHAPTER:{item_id}>\n{chapter_text}")
                    chapter_count += 1
                    logger.debug(
                        f"Extracted chapter {chapter_count}: {item_id} ({len(chapter_text)} chars)"
                    )

            except Exception as e:
                logger.warning(f"Failed to parse chapter {item.get_id()}: {e}")
                continue

        text = "\n\n".join(chapters)

        # Extract metadata from EPUB
        metadata = {
            "title": path.stem,  # Default to filename
            "author": "Unknown",
            "char_count": len(text),
            "chapter_count": chapter_count,
        }

        # Try to get Dublin Core metadata
        try:
            title_meta = book.get_metadata("DC", "title")
            if title_meta:
                metadata["title"] = title_meta[0][0]
        except:
            logger.debug("No title metadata found")

        try:
            author_meta = book.get_metadata("DC", "creator")
            if author_meta:
                metadata["author"] = author_meta[0][0]
        except:
            logger.debug("No author metadata found")

        try:
            language_meta = book.get_metadata("DC", "language")
            if language_meta:
                metadata["language"] = language_meta[0][0]
        except:
            logger.debug("No language metadata found")

        try:
            publisher_meta = book.get_metadata("DC", "publisher")
            if publisher_meta:
                metadata["publisher"] = publisher_meta[0][0]
        except:
            logger.debug("No publisher metadata found")

        # Quality assessment
        if not text.strip():
            logger.warning("No text extracted from EPUB")
            metadata["quality_score"] = 0.0
            metadata["error"] = "Empty EPUB or no readable content"
        elif len(text) < 100:
            logger.warning(f"Very short EPUB: {len(text)} chars")
            metadata["quality_score"] = 0.5
        elif chapter_count == 0:
            logger.warning(
                "No chapters detected - EPUB may have unusual structure"
            )
            metadata["quality_score"] = 0.7
        else:
            metadata["quality_score"] = 1.0
            logger.info(
                f"✓ Extracted {len(text):,} chars across {chapter_count} chapters"
            )

        return text, metadata

    except Exception as e:
        logger.error(f"EPUB extraction failed: {type(e).__name__}: {e}")
        return "", {
            "title": path.stem,
            "error": f"Extraction failed: {type(e).__name__}: {str(e)}",
            "quality_score": 0.0,
        }
