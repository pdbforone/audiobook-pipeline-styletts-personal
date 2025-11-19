"""
Text Normalization Pipeline

Prepares extracted text for TTS synthesis by:
1. Removing PDF artifacts (page numbers, headers, footers)
2. Converting numbers to words for TTS clarity
3. Preserving structural elements (headings, footnotes)
4. Delegating whitespace/unicode cleanup to the configured TTS normalizer

The normalizer selection is governed by config.yaml (`use_nemo`: false by default).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .cleaner import TTSTextCleaner
from .utils import load_config

try:
    from langdetect import LangDetectException, detect

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from num2words import num2words

    NUM2WORDS_AVAILABLE = True
except ImportError:
    NUM2WORDS_AVAILABLE = False

try:
    from .tts_normalizer import normalize_for_tts, validate_tts_readiness

    TTS_NORMALIZER_AVAILABLE = True
except (ImportError, AttributeError):
    TTS_NORMALIZER_AVAILABLE = False

logger = logging.getLogger(__name__)


def convert_numbers_to_words(text: str) -> Tuple[str, int]:
    """Convert numbers at line starts and headings into words for better TTS output."""
    if not NUM2WORDS_AVAILABLE:
        logger.debug("num2words not available - skipping number conversion")
        return text, 0

    conversion_count = 0

    def replace_book_chapter(match: re.Match[str]) -> str:
        nonlocal conversion_count
        prefix = match.group(1)
        num = int(match.group(2))
        conversion_count += 1
        return f"{prefix} {num2words(num, to='ordinal').title()}"

    text = re.sub(r"\b(Book|Chapter|Section|Part)\s+(\d+)\b", replace_book_chapter, text, flags=re.IGNORECASE)

    def replace_line_start_number(match: re.Match[str]) -> str:
        nonlocal conversion_count
        num = int(match.group(1))
        if 1 <= num <= 999:
            conversion_count += 1
            return num2words(num).title() + " "
        return match.group(0)

    text = re.sub(r"^(\d+)\s+(?=[A-Z])", replace_line_start_number, text, flags=re.MULTILINE)
    return text, conversion_count


def _apply_primary_normalizer(text: str, use_nemo: bool) -> Tuple[str, Dict[str, Any]]:
    """Route text through the configured primary normalizer."""
    metrics: Dict[str, Any] = {"changes": []}

    if use_nemo:
        cleaner = TTSTextCleaner()
        normalized = cleaner.clean_for_tts(text)
        metrics.update({"normalizer": "nemo", "tts_ready": True})
        metrics["changes"].append("Applied NeMo text normalization")
        return normalized, metrics

    if not TTS_NORMALIZER_AVAILABLE:
        metrics.update(
            {
                "normalizer": "noop",
                "tts_ready": False,
                "changes": ["TTS normalizer unavailable; returned text unchanged"],
            }
        )
        return text, metrics

    normalized, tts_stats = normalize_for_tts(text)
    metrics["normalizer"] = "regex"
    metrics["changes"].extend(tts_stats.get("changes", []))
    is_ready, issues = validate_tts_readiness(normalized)
    metrics["tts_ready"] = len(issues) == 0
    if issues:
        metrics["tts_issues"] = issues
    return normalized, metrics


def normalize_text(
    text: str,
    file_id: str,
    artifacts_dir: Path = Path("extracted_text"),
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Complete normalization pipeline for extracted text.

    Args:
        text: Raw extracted text
        file_id: Unique identifier for this file (for footnote storage)
        artifacts_dir: Directory to store footnotes if extracted
        config: Optional config overrides (merged with config.yaml)

    Returns:
        (normalized_text, metrics) where metrics tracks all changes
    """
    metrics: Dict[str, Any] = {
        "removed_junk_lines": 0,
        "removed_inline_numbers": 0,
        "converted_numbers_to_words": 0,
        "converted_quotes": False,
        "preserved_headings": 0,
        "extracted_footnotes": 0,
        "language": "unknown",
        "language_confidence": 0.0,
        "changes": [],
    }

    resolved_config = load_config()
    if config:
        resolved_config.update(config)
    use_nemo = bool(resolved_config.get("use_nemo", False))

    original_length = len(text)

    # Stage 1: Language Detection
    if LANGDETECT_AVAILABLE:
        try:
            sample = text[:5000] if len(text) > 5000 else text
            detected_lang = detect(sample)
            metrics["language"] = detected_lang
            metrics["language_confidence"] = 0.9
            metrics["changes"].append(f"Detected language: {detected_lang}")
        except LangDetectException as exc:
            logger.warning(f"Language detection failed: {exc}")
    else:
        logger.debug("langdetect not available - skipping language detection")

    # Stage 2: Remove Page Numbers and Headers/Footers
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()

        if not line_stripped:
            cleaned_lines.append("")
            continue

        if re.match(r"^\s*\d+\s*$", line_stripped):
            metrics["removed_junk_lines"] += 1
            continue

        if re.match(r"^\s*[-=_]{3,}\s*$", line_stripped):
            metrics["removed_junk_lines"] += 1
            continue

        if re.match(r"^\s*page\s+\d+(\s+of\s+\d+)?\s*$", line_stripped, re.IGNORECASE):
            metrics["removed_junk_lines"] += 1
            continue

        if re.match(r"^\d{1,4}\s+[A-Z]", line_stripped):
            cleaned_line = re.sub(r"^\d{1,4}\s+", "", line_stripped)
            cleaned_lines.append(cleaned_line)
            metrics["removed_inline_numbers"] += 1
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    metrics["changes"].append(f"Removed {metrics['removed_junk_lines']} junk lines")
    if metrics["removed_inline_numbers"] > 0:
        metrics["changes"].append(f"Removed {metrics['removed_inline_numbers']} inline page numbers")

    # Stage 3: Convert Numbers to Words
    text, num_conversions = convert_numbers_to_words(text)
    if num_conversions > 0:
        metrics["converted_numbers_to_words"] = num_conversions
        metrics["changes"].append(f"Converted {num_conversions} numbers to words for TTS")

    # Stage 4: Extract and Tag Footnotes
    footnotes = []
    footnote_pattern = r"\[(\d+)\]([^\[\n]+?)(?=\[\d+\]|$)"
    for match in re.finditer(footnote_pattern, text, re.DOTALL):
        footnote_num = match.group(1)
        footnote_text = match.group(2).strip()
        if footnote_text:
            footnotes.append({"number": footnote_num, "text": footnote_text})

    if footnotes:
        text = re.sub(footnote_pattern, "[FOOTNOTE]", text)
        metrics["extracted_footnotes"] = len(footnotes)
        metrics["changes"].append(f"Extracted {len(footnotes)} footnotes")

        try:
            footnote_dir = artifacts_dir / "footnotes"
            footnote_dir.mkdir(parents=True, exist_ok=True)
            footnote_path = footnote_dir / f"{file_id}_footnotes.json"
            footnote_path.write_text(json.dumps(footnotes, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - filesystem issues
            logger.warning(f"Failed to save footnotes: {exc}")

    # Stage 5: Count Preserved Headings
    heading_count = len(re.findall(r"<HEADING:\d+>", text))
    metrics["preserved_headings"] = heading_count
    if heading_count > 0:
        metrics["changes"].append(f"Preserved {heading_count} headings")

    # Stage 6: Delegate to Primary Normalizer (whitespace/unicode cleanup lives here)
    normalized_text, normalizer_metrics = _apply_primary_normalizer(text, use_nemo)
    metrics.update({k: v for k, v in normalizer_metrics.items() if k != "changes"})
    for change in normalizer_metrics.get("changes", []):
        if change not in metrics["changes"]:
            metrics["changes"].append(change)

    # Final metrics
    metrics["original_length"] = original_length
    metrics["final_length"] = len(normalized_text)
    metrics["size_change"] = len(normalized_text) - original_length
    metrics["text_yield"] = len(normalized_text) / original_length if original_length > 0 else 0.0

    logger.info("Normalization complete")
    logger.info(f"  Original: {original_length:,} chars")
    logger.info(f"  Final: {len(normalized_text):,} chars")
    logger.info(f"  Yield: {metrics['text_yield']:.2%}")

    return normalized_text, metrics
