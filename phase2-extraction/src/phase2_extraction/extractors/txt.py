"""
TXT Text Extractor

Handles plain text files with intelligent line merging.

Reason: Plain text files often have hard line breaks that create
unnatural pauses in TTS. Smart merging preserves paragraph structure
while removing unnecessary breaks.
"""

from pathlib import Path
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)


def extract(path: Path) -> Tuple[str, Dict]:
    """
    Extract and clean text from plain text file.
    
    Args:
        path: Path to TXT file
        
    Returns:
        (text, metadata) with cleaned text
        
    Strategy:
    - Merge short lines (likely hard-wrapped text)
    - Preserve paragraph breaks (empty lines or indentation)
    - Handle various text encodings
    
    Reason: Many text files have hard line breaks at 80 chars that
    create unnatural TTS pauses. Intelligent merging creates natural
    paragraph flow while preserving intended structure.
    """
    logger.info(f"Extracting TXT: {path.name}")
    
    # Try multiple encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    text = None
    used_encoding = None
    
    for encoding in encodings:
        try:
            with path.open('r', encoding=encoding, errors='replace') as f:
                text = f.read()
            used_encoding = encoding
            logger.debug(f"Successfully read with encoding: {encoding}")
            break
        except UnicodeDecodeError:
            logger.debug(f"Failed to read with encoding: {encoding}")
            continue
    
    if text is None:
        error_msg = "Failed to read file with any common encoding"
        logger.error(error_msg)
        return "", {
            "title": path.stem,
            "error": error_msg,
            "quality_score": 0.0
        }
    
    # Intelligent line merging
    lines = text.split('\n')
    merged = []
    buffer = ""
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Empty line = paragraph break
        if not line_stripped:
            if buffer:
                merged.append(buffer.strip())
                buffer = ""
            merged.append("")  # Preserve paragraph break
            continue
        
        # Check if line should be merged or kept separate
        # Keep separate if:
        # 1. Line is very short (likely heading or list item)
        # 2. Next line starts with indentation (likely new paragraph)
        # 3. Current line ends with sentence-ending punctuation followed by double space
        
        next_line = lines[i+1] if i+1 < len(lines) else ""
        next_line_stripped = next_line.strip()
        
        # Very short line (< 10 chars) - likely heading or list
        if len(line_stripped) < 10 and buffer:
            merged.append(buffer.strip())
            merged.append(line_stripped)
            buffer = ""
            continue
        
        # Next line is indented - new paragraph
        if next_line and next_line[0:1].isspace() and len(next_line_stripped) > 0:
            buffer += " " + line_stripped if buffer else line_stripped
            merged.append(buffer.strip())
            buffer = ""
            continue
        
        # Line ends with sentence-ending punctuation - likely paragraph end
        if line_stripped and line_stripped[-1] in '.!?':
            buffer += " " + line_stripped if buffer else line_stripped
            # Check if next line suggests new paragraph (capitalized, etc.)
            if next_line_stripped and next_line_stripped[0].isupper():
                merged.append(buffer.strip())
                buffer = ""
                continue
        
        # Default: merge with buffer
        buffer += " " + line_stripped if buffer else line_stripped
    
    # Don't forget last buffer
    if buffer:
        merged.append(buffer.strip())
    
    # Join with newlines
    text = "\n".join(filter(None, merged))
    
    metadata = {
        "title": path.stem,
        "char_count": len(text),
        "encoding": used_encoding,
        "original_lines": len(lines),
        "merged_lines": len(merged)
    }
    
    # Quality assessment
    if not text.strip():
        logger.warning("No text in file")
        metadata["quality_score"] = 0.0
        metadata["error"] = "Empty file"
    elif len(text) < 100:
        logger.warning(f"Very short file: {len(text)} chars")
        metadata["quality_score"] = 0.5
    else:
        metadata["quality_score"] = 1.0
        logger.info(
            f"✓ Extracted {len(text):,} chars "
            f"(merged {len(lines)} → {len(merged)} lines)"
        )
    
    # Check for potential encoding issues
    replacement_chars = text.count('\ufffd')
    if replacement_chars > 0:
        logger.warning(
            f"Found {replacement_chars} replacement characters - "
            f"file may have encoding issues"
        )
        metadata["quality_score"] *= 0.9
        metadata["encoding_issues"] = replacement_chars
    
    return text, metadata
