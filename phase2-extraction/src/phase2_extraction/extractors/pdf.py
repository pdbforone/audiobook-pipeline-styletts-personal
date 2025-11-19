"""
PDF Text Extractor - Multi-Pass with Comprehensive Quality Validation

Maintains the thoroughness of the original Phase 2 implementation:
- Multi-pass extraction (pypdf, pdfplumber, PyMuPDF)
- Comprehensive quality validation
- Detailed logging and metrics
- Robust error handling
- Optimal method selection based on quality scores

This is a modularized version that preserves all existing functionality.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..extraction import validate_extraction_quality as base_validate_extraction_quality

# Try optional extraction libraries
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


def validate_extraction_quality(text: str, method_name: str) -> float:
    """Delegate to shared Phase 2 quality validation."""
    return base_validate_extraction_quality(text, method_name)


def extract_text_pypdf(file_path: Path) -> str:
    """
    Extract using pypdf library.
    
    Reason: pypdf is pure Python and handles some PDFs better than alternatives.
    Often good for text-based PDFs with standard encoding.
    """
    if not PYPDF_AVAILABLE:
        logger.debug("pypdf not available - skipping")
        return ""
    
    try:
        logger.debug(f"Attempting extraction with pypdf...")
        reader = PdfReader(str(file_path))
        pages_text = []
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text)
            else:
                logger.debug(f"pypdf: Page {i+1} yielded no text")
        
        text = "\n".join(pages_text)
        
        if text.strip():
            logger.info(f"pypdf: Extracted {len(text):,} chars from {len(pages_text)} pages")
        else:
            logger.warning("pypdf: No text extracted")
            
        return text
        
    except Exception as e:
        logger.warning(f"pypdf extraction failed: {type(e).__name__}: {e}")
        return ""


def extract_text_pdfplumber(file_path: Path) -> str:
    """
    Extract using pdfplumber library.
    
    Reason: pdfplumber often handles layout and spacing better than other tools.
    Good for complex layouts and preserving text structure.
    """
    if not PDFPLUMBER_AVAILABLE:
        logger.debug("pdfplumber not available - skipping")
        return ""
    
    try:
        logger.debug(f"Attempting extraction with pdfplumber...")
        pages_text = []
        
        with pdfplumber.open(str(file_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
                else:
                    logger.debug(f"pdfplumber: Page {i+1} yielded no text")
        
        text = "\n".join(pages_text)
        
        if text.strip():
            logger.info(f"pdfplumber: Extracted {len(text):,} chars from {len(pages_text)} pages")
        else:
            logger.warning("pdfplumber: No text extracted")
            
        return text
        
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {type(e).__name__}: {e}")
        return ""


def extract_text_pymupdf(file_path: Path) -> str:
    """
    Extract using PyMuPDF (fitz) library.
    
    Reason: PyMuPDF is fast and robust, often works when others fail.
    Good general-purpose fallback with decent accuracy.
    """
    if not PYMUPDF_AVAILABLE:
        logger.debug("PyMuPDF not available - skipping")
        return ""
    
    try:
        logger.debug(f"Attempting extraction with PyMuPDF...")
        doc = fitz.open(str(file_path))
        pages_text = []
        
        for i, page in enumerate(doc):
            page_text = page.get_text()
            if page_text.strip():
                pages_text.append(page_text)
            else:
                logger.debug(f"PyMuPDF: Page {i+1} yielded no text")
        
        text = "\n".join(pages_text)
        doc.close()
        
        if text.strip():
            logger.info(f"PyMuPDF: Extracted {len(text):,} chars from {len(pages_text)} pages")
        else:
            logger.warning("PyMuPDF: No text extracted")
            
        return text
        
    except Exception as e:
        logger.warning(f"PyMuPDF extraction failed: {type(e).__name__}: {e}")
        return ""


def extract_pdf_metadata(file_path: Path) -> Dict:
    """
    Extract PDF metadata using PyMuPDF.
    
    Returns dict with title, author, etc. Falls back to filename if unavailable.
    """
    metadata = {
        "title": file_path.stem,
        "author": "Unknown"
    }
    
    if not PYMUPDF_AVAILABLE:
        return metadata
    
    try:
        doc = fitz.open(str(file_path))
        pdf_meta = doc.metadata
        
        if pdf_meta:
            metadata["title"] = pdf_meta.get("title") or file_path.stem
            metadata["author"] = pdf_meta.get("author") or "Unknown"
            
            # Add optional metadata if present
            if pdf_meta.get("subject"):
                metadata["subject"] = pdf_meta.get("subject")
            if pdf_meta.get("keywords"):
                metadata["keywords"] = pdf_meta.get("keywords")
                
        doc.close()
        logger.debug(f"Extracted metadata: {metadata}")
        
    except Exception as e:
        logger.debug(f"Metadata extraction failed: {e}")
    
    return metadata


def extract(path: Path, force_method: Optional[str] = None) -> Tuple[str, Dict]:
    """
    Multi-pass PDF extraction with comprehensive quality validation.
    
    Strategy:
    1. Try all available extraction methods (pypdf, pdfplumber, PyMuPDF)
    2. Validate quality of each result
    3. Select the best result based on quality score
    4. Extract metadata separately
    
    Args:
        path: Path to PDF file
        force_method: Optional - force specific method ('pypdf', 'pdfplumber', 'pymupdf')
        
    Returns:
        (text, metadata) where metadata includes:
        - title, author (from PDF metadata or filename)
        - quality_score (0.0-1.0)
        - tool_used (which extraction method won)
        - char_count (length of extracted text)
        
    Reason: Multi-pass approach maximizes extraction quality by trying
    multiple methods and selecting the best result. Different PDF generators
    work better with different extraction tools.
    """
    logger.info("=" * 60)
    logger.info(f"EXTRACTING PDF: {path.name}")
    logger.info("=" * 60)
    
    # If forced method, use only that one
    if force_method:
        logger.info(f"Using forced method: {force_method}")
        
        method_map = {
            'pypdf': extract_text_pypdf,
            'pdfplumber': extract_text_pdfplumber,
            'pymupdf': extract_text_pymupdf
        }
        
        if force_method not in method_map:
            logger.error(f"Unknown method: {force_method}")
            return "", {
                "title": path.stem,
                "quality_score": 0.0,
                "tool_used": "none",
                "error": f"Unknown method: {force_method}"
            }
        
        text = method_map[force_method](path)
        quality_score = validate_extraction_quality(text, force_method) if text else 0.0
        
        metadata = extract_pdf_metadata(path)
        metadata.update({
            "quality_score": quality_score,
            "tool_used": force_method,
            "char_count": len(text)
        })
        
        return text, metadata
    
    # Multi-pass: try all methods
    results = {}
    
    methods = [
        ("pypdf", extract_text_pypdf),
        ("pdfplumber", extract_text_pdfplumber),
        ("pymupdf", extract_text_pymupdf),
    ]
    
    for method_name, extract_func in methods:
        logger.info(f"\nTrying {method_name}...")
        text = extract_func(path)
        
        if text.strip():
            score = validate_extraction_quality(text, method_name)
            results[method_name] = (text, score)
            logger.info(f"{method_name}: Score={score:.2f}, Length={len(text):,} chars")
        else:
            logger.warning(f"{method_name}: No text extracted")
    
    # Check if any method succeeded
    if not results:
        logger.error("=" * 60)
        logger.error("ALL EXTRACTION METHODS FAILED")
        logger.error("=" * 60)
        logger.error("Possible causes:")
        logger.error("  1. PDF is scanned/image-based (needs OCR)")
        logger.error("  2. PDF is corrupted or encrypted")
        logger.error("  3. PDF uses unsupported encoding")
        logger.error("Recommendation: Run Phase 1 validation to check PDF type")
        
        metadata = extract_pdf_metadata(path)
        metadata.update({
            "quality_score": 0.0,
            "tool_used": "none",
            "char_count": 0,
            "error": "All extraction methods failed"
        })
        return "", metadata
    
    # Select best method by quality score
    best_method = max(results.keys(), key=lambda k: results[k][1])
    best_text, best_score = results[best_method]
    
    logger.info("=" * 60)
    logger.info(f"BEST METHOD: {best_method}")
    logger.info(f"Quality Score: {best_score:.2f}/1.0")
    logger.info(f"Length: {len(best_text):,} chars")
    logger.info("=" * 60)
    
    # Get metadata
    metadata = extract_pdf_metadata(path)
    metadata.update({
        "quality_score": best_score,
        "tool_used": best_method,
        "char_count": len(best_text),
        "methods_tried": list(results.keys()),
        "all_scores": {k: v[1] for k, v in results.items()}
    })
    
    # Quality warnings
    if best_score < 0.6:
        logger.warning(
            f"⚠️  Low quality score ({best_score:.2f}) - "
            f"extracted text may have issues"
        )
    elif best_score < 0.8:
        logger.info(f"Quality score acceptable ({best_score:.2f})")
    else:
        logger.info(f"✓ High quality extraction ({best_score:.2f})")
    
    return best_text, metadata
