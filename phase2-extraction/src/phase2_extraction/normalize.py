"""
Text Normalization Pipeline

Prepares extracted text for TTS synthesis by:
1. Removing PDF artifacts (page numbers, headers, footers)
2. Converting numbers to words for TTS clarity
3. Normalizing whitespace and unicode
4. Preserving structural elements (headings, footnotes)
5. Converting curly quotes
6. Fixing punctuation spacing

Integrates with existing tts_normalizer.py for comprehensive cleanup.
"""

import re
import json
from pathlib import Path
from typing import Tuple, Dict
import logging

# Import existing TTS normalizer
try:
    from .tts_normalizer import normalize_for_tts, validate_tts_readiness
    TTS_NORMALIZER_AVAILABLE = True
except (ImportError, AttributeError):
    TTS_NORMALIZER_AVAILABLE = False

try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from num2words import num2words
    NUM2WORDS_AVAILABLE = True
except ImportError:
    NUM2WORDS_AVAILABLE = False

logger = logging.getLogger(__name__)


def convert_numbers_to_words(text: str) -> Tuple[str, int]:
    """
    Convert standalone numbers to words for better TTS pronunciation.
    
    Converts:
    - Standalone line-start numbers: "3 The Master" → "Three The Master"
    - Book/Chapter numbers: "Book 1" → "Book One"
    - Section numbers at start of paragraphs
    
    Does NOT convert:
    - Numbers in dates (e.g., "1984")
    - Numbers with decimals (e.g., "3.14")
    - Numbers in measurements (e.g., "5 miles")
    
    Args:
        text: Input text with numbers
        
    Returns:
        (converted_text, conversion_count)
        
    Reason: TTS engines often mispronounce or inconsistently read numbers.
    Converting to words prevents hallucinations and improves listening quality.
    """
    if not NUM2WORDS_AVAILABLE:
        logger.warning("num2words not available - skipping number conversion")
        return text, 0
    
    conversion_count = 0
    
    # Convert "Book 1" → "Book One" (ordinal forms)
    def replace_book_chapter(match):
        nonlocal conversion_count
        prefix = match.group(1)  # "Book" or "Chapter"
        num = int(match.group(2))
        conversion_count += 1
        # Use title case: "Book One", "Chapter Two"
        return f"{prefix} {num2words(num, to='ordinal').title()}"
    
    text = re.sub(
        r'\b(Book|Chapter|Section|Part)\s+(\d+)\b',
        replace_book_chapter,
        text,
        flags=re.IGNORECASE
    )
    
    # Convert standalone numbers at start of lines (likely section/verse numbers)
    # But be careful not to convert dates or large numbers
    def replace_line_start_number(match):
        nonlocal conversion_count
        num = int(match.group(1))
        # Only convert small numbers (1-999) at line start
        # These are likely verse/section numbers
        if 1 <= num <= 999:
            conversion_count += 1
            return num2words(num).title() + ' '
        else:
            return match.group(0)  # Leave as-is
    
    text = re.sub(
        r'^(\d+)\s+(?=[A-Z])',  # Number at line start, followed by capital letter
        replace_line_start_number,
        text,
        flags=re.MULTILINE
    )
    
    return text, conversion_count


def normalize_text(text: str, file_id: str, artifacts_dir: Path = Path("extracted_text")) -> Tuple[str, Dict]:
    """
    Complete normalization pipeline for extracted text.
    
    Args:
        text: Raw extracted text
        file_id: Unique identifier for this file (for footnote storage)
        artifacts_dir: Directory to store footnotes if extracted
        
    Returns:
        (normalized_text, metrics) where metrics tracks all changes
        
    Pipeline stages:
    1. Language detection
    2. Remove page numbers and headers/footers (including inline numbers)
    3. Convert remaining numbers to words for TTS
    4. Extract and tag footnotes
    5. Preserve headings
    6. Whitespace normalization
    7. Unicode normalization (curly quotes → straight quotes)
    8. TTS-specific normalization (if available)
    9. Final validation
    
    Reason: Each stage addresses a specific TTS quality issue. Running
    them in order prevents one normalization from interfering with another.
    """
    metrics = {
        "removed_junk_lines": 0,
        "removed_inline_numbers": 0,
        "converted_numbers_to_words": 0,
        "converted_quotes": False,
        "preserved_headings": 0,
        "extracted_footnotes": 0,
        "language": "unknown",
        "language_confidence": 0.0,
        "changes": []
    }
    
    original_length = len(text)
    
    # Stage 1: Language Detection
    if LANGDETECT_AVAILABLE:
        try:
            # Use first 5000 chars for speed
            sample = text[:5000] if len(text) > 5000 else text
            detected_lang = detect(sample)
            metrics["language"] = detected_lang
            metrics["language_confidence"] = 0.9  # langdetect doesn't provide confidence
            metrics["changes"].append(f"Detected language: {detected_lang}")
            logger.debug(f"Detected language: {detected_lang}")
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
            metrics["language"] = "unknown"
            metrics["language_confidence"] = 0.0
    else:
        logger.debug("langdetect not available - skipping language detection")
    
    # Stage 2: Remove Page Numbers and Headers/Footers (Enhanced)
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines (will be re-added appropriately later)
        if not line_stripped:
            cleaned_lines.append("")
            continue
        
        # Remove page numbers (standalone numbers on their own line)
        if re.match(r'^\s*\d+\s*$', line_stripped):
            metrics["removed_junk_lines"] += 1
            continue
        
        # Remove horizontal rules (likely headers/footers)
        if re.match(r'^\s*[-=_]{3,}\s*$', line_stripped):
            metrics["removed_junk_lines"] += 1
            continue
        
        # Remove "Page X of Y" patterns
        if re.match(r'^\s*page\s+\d+(\s+of\s+\d+)?\s*$', line_stripped, re.IGNORECASE):
            metrics["removed_junk_lines"] += 1
            continue
        
        # NEW: Remove inline page numbers at start of paragraphs
        # Pattern: "3 The Master said..." → "The Master said..."
        # Only if number is 1-4 digits (page numbers, not years like 1984)
        if re.match(r'^\d{1,4}\s+[A-Z]', line_stripped):
            # This looks like a page number followed by content
            cleaned_line = re.sub(r'^\d{1,4}\s+', '', line_stripped)
            cleaned_lines.append(cleaned_line)
            metrics["removed_inline_numbers"] += 1
            continue
        
        cleaned_lines.append(line)
    
    text = "\n".join(cleaned_lines)
    metrics["changes"].append(f"Removed {metrics['removed_junk_lines']} junk lines")
    if metrics["removed_inline_numbers"] > 0:
        metrics["changes"].append(f"Removed {metrics['removed_inline_numbers']} inline page numbers")
    
    # Stage 3: Convert Numbers to Words (NEW)
    text, num_conversions = convert_numbers_to_words(text)
    if num_conversions > 0:
        metrics["converted_numbers_to_words"] = num_conversions
        metrics["changes"].append(f"Converted {num_conversions} numbers to words for TTS")
        logger.info(f"Converted {num_conversions} numbers to words")
    
    # Stage 4: Extract and Tag Footnotes
    # Pattern: [1] Some footnote text [2] Next footnote text
    footnotes = []
    footnote_pattern = r'\[(\d+)\]([^\[\n]+?)(?=\[\d+\]|$)'
    
    for match in re.finditer(footnote_pattern, text, re.DOTALL):
        footnote_num = match.group(1)
        footnote_text = match.group(2).strip()
        if footnote_text:
            footnotes.append({
                "number": footnote_num,
                "text": footnote_text
            })
    
    if footnotes:
        # Replace footnotes with tags
        text = re.sub(footnote_pattern, '[FOOTNOTE]', text)
        metrics["extracted_footnotes"] = len(footnotes)
        metrics["changes"].append(f"Extracted {len(footnotes)} footnotes")
        
        # Save footnotes to separate file
        try:
            footnote_dir = artifacts_dir / "footnotes"
            footnote_dir.mkdir(parents=True, exist_ok=True)
            footnote_path = footnote_dir / f"{file_id}_footnotes.json"
            
            with footnote_path.open('w', encoding='utf-8') as f:
                json.dump(footnotes, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(footnotes)} footnotes to {footnote_path}")
        except Exception as e:
            logger.warning(f"Failed to save footnotes: {e}")
    
    # Stage 5: Count Preserved Headings
    # Headings use markers like <HEADING:1>, <HEADING:2>, etc.
    heading_count = len(re.findall(r'<HEADING:\d+>', text))
    metrics["preserved_headings"] = heading_count
    if heading_count > 0:
        metrics["changes"].append(f"Preserved {heading_count} headings")
    
    # Stage 6: Whitespace Normalization
    # Collapse multiple spaces (but not multiple newlines - those are paragraph breaks)
    before_spaces = len(re.findall(r' {2,}', text))
    text = re.sub(r' +', ' ', text)  # Collapse multiple spaces
    text = re.sub(r'\t+', ' ', text)  # Convert tabs to spaces
    after_spaces = len(re.findall(r' {2,}', text))
    
    if before_spaces > after_spaces:
        metrics["changes"].append(f"Collapsed {before_spaces - after_spaces} multiple-space instances")
    
    # Normalize paragraph breaks (max 2 consecutive newlines)
    text = re.sub(r'\n\n\n+', '\n\n', text)
    
    # Remove trailing whitespace from lines
    text = '\n'.join(line.rstrip() for line in text.split('\n'))
    
    # Stage 7: Unicode Normalization (Curly Quotes → Straight Quotes)
    # TTS engines often handle straight quotes better than curly quotes
    quote_chars = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote  
        '\u201C': '"',  # Left double quote
        '\u201D': '"',  # Right double quote
        '\u2013': '-',  # En dash
        '\u2014': '--',  # Em dash
        '\u2026': '...', # Ellipsis
    }
    
    if any(char in text for char in quote_chars.keys()):
        for old, new in quote_chars.items():
            text = text.replace(old, new)
        metrics["converted_quotes"] = True
        metrics["changes"].append("Converted curly quotes to straight quotes")
    
    # Stage 8: TTS-Specific Normalization
    if TTS_NORMALIZER_AVAILABLE:
        logger.debug("Applying TTS-specific normalization...")
        text, tts_stats = normalize_for_tts(text)
        
        # Merge TTS stats into metrics
        for change in tts_stats.get('changes', []):
            if change not in metrics["changes"]:  # Avoid duplicates
                metrics["changes"].append(f"TTS: {change}")
        
        # Validate TTS readiness
        is_ready, issues = validate_tts_readiness(text)
        if issues:
            metrics["tts_issues"] = issues
            logger.warning("TTS validation issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        else:
            logger.info("✓ Text is TTS-ready")
            metrics["tts_ready"] = True
    else:
        logger.warning("TTS normalizer not available - skipping TTS-specific normalization")
        metrics["tts_ready"] = False
    
    # Final metrics
    metrics["original_length"] = original_length
    metrics["final_length"] = len(text)
    metrics["size_change"] = len(text) - original_length
    
    # Calculate text yield
    metrics["text_yield"] = len(text) / original_length if original_length > 0 else 0.0
    
    logger.info(f"Normalization complete:")
    logger.info(f"  Original: {original_length:,} chars")
    logger.info(f"  Final: {len(text):,} chars")
    logger.info(f"  Yield: {metrics['text_yield']:.2%}")
    logger.info(f"  Changes: {len(metrics['changes'])}")
    
    for change in metrics["changes"]:
        logger.debug(f"    - {change}")
    
    return text, metrics
