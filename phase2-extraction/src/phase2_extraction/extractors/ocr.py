"""
OCR Text Extractor

Extracts text from scanned PDFs using EasyOCR (CPU-only).

Strategy:
- Batch processing to stay within 4GB memory limit
- Quality confidence tracking per page
- Progress logging for long documents

Reason: Scanned PDFs require OCR. EasyOCR is CPU-only and works
well for English text. Batching prevents memory exhaustion on large files.
"""

from pathlib import Path
from typing import Tuple, Dict
import logging

try:
    import easyocr

    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from pdf2image import convert_from_path

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract(path: Path, batch_size: int = 10) -> Tuple[str, Dict]:
    """
    Extract text from scanned PDF using OCR.

    Args:
        path: Path to PDF file
        batch_size: Number of pages to process at once (default: 10)
                   Lower values use less memory but take longer

    Returns:
        (text, metadata) with OCR confidence scores

    Strategy:
    1. Convert PDF pages to images in batches
    2. Run EasyOCR on each image
    3. Track confidence scores
    4. Aggregate results

    Reason: Processing in batches prevents memory exhaustion on
    large PDFs (e.g., 500+ page books). Default batch_size=10 keeps
    memory under 4GB on most systems.
    """
    if not EASYOCR_AVAILABLE:
        error_msg = (
            "easyocr library not available. Install with: poetry add easyocr\n"
            "Note: EasyOCR requires PyTorch but works CPU-only"
        )
        logger.error(error_msg)
        return "", {
            "title": path.stem,
            "error": error_msg,
            "quality_score": 0.0,
        }

    if not PDF2IMAGE_AVAILABLE:
        error_msg = (
            "pdf2image library not available. Install with: poetry add pdf2image\n"
            "Also requires poppler: brew install poppler (Mac) or apt-get install poppler-utils (Linux)"
        )
        logger.error(error_msg)
        return "", {
            "title": path.stem,
            "error": error_msg,
            "quality_score": 0.0,
        }

    logger.info(f"OCR Extraction: {path.name}")
    logger.warning("OCR is slow - expect ~5-10 seconds per page")
    logger.info(f"Processing in batches of {batch_size} pages")

    try:
        # Initialize EasyOCR reader (CPU-only)
        logger.debug("Initializing EasyOCR reader (this may take a moment)...")
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        logger.debug("EasyOCR reader initialized")

        # Get total page count (quick check)
        try:
            import fitz

            doc = fitz.open(str(path))
            total_pages = len(doc)
            doc.close()
            logger.info(f"Document has {total_pages} pages")
        except Exception as exc:
            logger.warning("Could not determine page count: %s", exc)
            total_pages = None

        all_results = []
        all_confidences = []
        page_num = 0

        # Process in batches
        while True:
            # Convert batch of pages to images
            logger.info(
                f"Converting pages {page_num+1}-{page_num+batch_size} to images..."
            )

            try:
                images = convert_from_path(
                    str(path),
                    first_page=page_num + 1,
                    last_page=page_num + batch_size,
                    dpi=300,  # Higher DPI = better OCR but slower
                    fmt="jpeg",
                    jpegopt={
                        "quality": 85,
                        "progressive": True,
                        "optimize": True,
                    },
                )
            except Exception as e:
                # Likely reached end of document
                if page_num == 0:
                    raise  # If first batch fails, it's a real error
                logger.debug(f"Reached end of document or error: {e}")
                break

            if not images:
                break

            # Process each image
            for i, img in enumerate(images):
                current_page = page_num + i + 1
                logger.info(f"OCR processing page {current_page}...")

                try:
                    # Run OCR
                    result = reader.readtext(img, paragraph=True)

                    # Extract text and confidences
                    page_text = []
                    page_confidences = []

                    for detection in result:
                        # EasyOCR returns: (bbox, text, confidence)
                        text = detection[1]
                        confidence = detection[2]

                        page_text.append(text)
                        page_confidences.append(confidence)

                    # Combine page text
                    combined_text = "\n".join(page_text)
                    all_results.append(combined_text)

                    # Track confidences
                    if page_confidences:
                        page_avg_conf = sum(page_confidences) / len(
                            page_confidences
                        )
                        all_confidences.append(page_avg_conf)
                        logger.info(
                            f"  Page {current_page}: {len(combined_text)} chars, "
                            f"confidence: {page_avg_conf:.2%}"
                        )
                    else:
                        logger.warning(
                            f"  Page {current_page}: No text detected"
                        )
                        all_confidences.append(0.0)

                except Exception as e:
                    logger.error(f"OCR failed on page {current_page}: {e}")
                    all_confidences.append(0.0)
                    continue

            page_num += batch_size

            # Safety check: prevent infinite loop
            if total_pages and page_num >= total_pages:
                break

        # Combine all pages
        text = "\n\n".join(all_results)

        # Calculate overall confidence
        avg_confidence = (
            sum(all_confidences) / len(all_confidences)
            if all_confidences
            else 0.0
        )

        metadata = {
            "title": path.stem,
            "char_count": len(text),
            "pages_processed": len(all_results),
            "ocr_confidence_avg": avg_confidence,
            "ocr_confidence_min": (
                min(all_confidences) if all_confidences else 0.0
            ),
            "ocr_confidence_max": (
                max(all_confidences) if all_confidences else 0.0
            ),
            "tool_used": "easyocr",
        }

        # Quality assessment based on confidence
        if not text.strip():
            logger.error("OCR produced no text")
            metadata["quality_score"] = 0.0
            metadata["error"] = "No text detected"
        elif len(text) < 100:
            logger.warning(f"Very little text extracted: {len(text)} chars")
            metadata["quality_score"] = 0.3
        elif avg_confidence < 0.5:
            logger.warning(
                f"Low OCR confidence ({avg_confidence:.2%}) - "
                f"text likely has errors"
            )
            metadata["quality_score"] = 0.5
        elif avg_confidence < 0.7:
            logger.info(f"Moderate OCR confidence ({avg_confidence:.2%})")
            metadata["quality_score"] = 0.7
        else:
            logger.info(f"Good OCR confidence ({avg_confidence:.2%})")
            metadata["quality_score"] = 0.85  # OCR never gets 1.0

        logger.info("=" * 60)
        logger.info("OCR COMPLETE")
        logger.info(f"Pages processed: {len(all_results)}")
        logger.info(f"Total chars: {len(text):,}")
        logger.info(f"Average confidence: {avg_confidence:.2%}")
        logger.info("=" * 60)

        # Warnings for low-quality results
        if avg_confidence < 0.7:
            logger.warning("⚠️  Low OCR confidence - consider:")
            logger.warning("  1. Using higher resolution scan (300+ DPI)")
            logger.warning("  2. Improving source document quality")
            logger.warning("  3. Manual review of extracted text")

        return text, metadata

    except Exception as e:
        logger.error(f"OCR extraction failed: {type(e).__name__}: {e}")
        return "", {
            "title": path.stem,
            "error": f"OCR failed: {type(e).__name__}: {str(e)}",
            "quality_score": 0.0,
        }
