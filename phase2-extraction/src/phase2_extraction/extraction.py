"""
Phase 2 extraction utilities.

This module provides reusable helpers for text extraction and scoring.
All orchestration lives in ingest.py; no CLI entry point is exposed here.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

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

logger = logging.getLogger(__name__)


def compute_sha256(file_path: Path) -> str:
    """Compute sha256 hash for change detection / reuse checks."""
    sha = hashlib.sha256()
    with file_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def _get_expected_page_count(file_path: Path) -> Optional[int]:
    """Best-effort page count for quality checks."""
    if PYPDF_AVAILABLE:
        try:
            return len(PdfReader(str(file_path)).pages)
        except Exception as exc:  # pragma: no cover - defensive guardrail
            logger.debug(f"pypdf page count failed: {exc}")

    if PYMUPDF_AVAILABLE:
        try:
            with fitz.open(str(file_path)) as doc:
                return len(doc)
        except Exception as exc:  # pragma: no cover - defensive guardrail
            logger.debug(f"PyMuPDF page count failed: {exc}")

    return None


def validate_extraction_quality(
    text: str,
    method_name: str = "unknown",
    expected_pages: Optional[int] = None,
) -> float:
    """
    Validate extraction quality for TTS.

    Checks include:
    - Replacement character rate
    - Alphabetic ratio
    - Common-word frequency
    - Digit/letter balance
    - Page count consistency (when available)
    """
    if not text or len(text) < 100:
        logger.warning(f"{method_name}: insufficient text extracted (<100 chars)")
        return 0.0

    score = 1.0
    sample = text[:20000]

    replacement_rate = text.count("\ufffd") / len(text)
    if replacement_rate > 0.01:
        score -= 0.3
        logger.warning(f"{method_name}: high replacement character rate ({replacement_rate:.2%})")
    elif replacement_rate > 0:
        score -= 0.1

    alpha_ratio = sum(1 for c in sample if c.isalpha()) / len(sample)
    if alpha_ratio < 0.65:
        score -= 0.3
        logger.warning(f"{method_name}: low alphabetic ratio ({alpha_ratio:.1%})")
    elif alpha_ratio < 0.75:
        score -= 0.1

    text_lower = sample.lower()
    common_words = ["the", "and", "of", "to", "a", "in", "is", "that", "for", "it"]
    found_common = sum(1 for word in common_words if f" {word} " in text_lower)
    if found_common < 6:
        score -= 0.3
        logger.warning(f"{method_name}: only {found_common}/10 common words found")
    elif found_common < 8:
        score -= 0.1

    digits = sum(1 for c in sample if c.isdigit())
    letters = sum(1 for c in sample if c.isalpha())
    digit_ratio = digits / max(letters, 1)
    if digit_ratio > 0.35:
        score -= 0.2
        logger.warning(f"{method_name}: high digit/letter ratio ({digit_ratio:.1%})")

    if expected_pages:
        estimated_pages = text.count("\f") or max(int(len(text) / 1800), 1)
        page_ratio = estimated_pages / expected_pages
        if page_ratio < 0.5 or page_ratio > 2.5:
            score -= 0.2
            logger.warning(f"{method_name}: page count mismatch est={estimated_pages} vs expected={expected_pages}")

    score = max(0.0, score)
    logger.info(f"{method_name} quality score: {score:.2f}")
    return score


def _extract_text_pypdf(file_path: Path) -> str:
    if not PYPDF_AVAILABLE:
        return ""
    try:
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.warning(f"pypdf extraction failed: {exc}")
        return ""


def _extract_text_pdfplumber(file_path: Path) -> str:
    if not PDFPLUMBER_AVAILABLE:
        return ""
    try:
        with pdfplumber.open(str(file_path)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:
        logger.warning(f"pdfplumber extraction failed: {exc}")
        return ""


def _extract_text_pymupdf(file_path: Path) -> str:
    if not PYMUPDF_AVAILABLE:
        return ""
    try:
        with fitz.open(str(file_path)) as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception as exc:
        logger.warning(f"PyMuPDF extraction failed: {exc}")
        return ""


def extract_text_single(file_path: Path, method: str) -> str:
    """Extract text using a specific method name."""
    method_map: Dict[str, Callable[[Path], str]] = {
        "pypdf": _extract_text_pypdf,
        "pdfplumber": _extract_text_pdfplumber,
        "pymupdf": _extract_text_pymupdf,
    }

    if method not in method_map:
        raise ValueError(f"Unknown extraction method: {method}")

    return method_map[method](file_path)


def extract_text_multipass(file_path: Path) -> Tuple[str, str, float]:
    """
    Multi-pass extraction: try multiple methods, pick the best.

    Returns (text, method_used, quality_score)
    """
    logger.info("=" * 60)
    logger.info("MULTI-PASS EXTRACTION")
    logger.info("=" * 60)

    results: Dict[str, Tuple[str, float]] = {}
    expected_pages = _get_expected_page_count(file_path)
    methods: Tuple[Tuple[str, Callable[[Path], str]], ...] = (
        ("pypdf", _extract_text_pypdf),
        ("pdfplumber", _extract_text_pdfplumber),
        ("pymupdf", _extract_text_pymupdf),
    )

    for method_name, extract_func in methods:
        text = extract_func(file_path)
        if text.strip():
            score = validate_extraction_quality(text, method_name, expected_pages)
            results[method_name] = (text, score)
            logger.info(f"{method_name}: {len(text):,} chars (score={score:.2f})")
        else:
            logger.warning(f"{method_name}: no text extracted")

    if not results:
        logger.error("All extraction methods failed.")
        return "", "none", 0.0

    best_method = max(results.keys(), key=lambda key: results[key][1])
    best_text, best_score = results[best_method]

    logger.info("=" * 60)
    logger.info(f"BEST: {best_method} (score: {best_score:.2f}, {len(best_text):,} chars)")
    logger.info("=" * 60)

    return best_text, best_method, best_score


__all__ = [
    "compute_sha256",
    "validate_extraction_quality",
    "extract_text_single",
    "extract_text_multipass",
]
