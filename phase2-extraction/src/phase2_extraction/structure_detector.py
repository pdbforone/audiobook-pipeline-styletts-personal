"""
Professional Document Structure Detection for Phase 2

Extracts hierarchical structure (chapters, sections) during text extraction.
Works for PDFs (TOC + font analysis), EPUB/MOBI (HTML headings), and plain text (heuristics).

This is an OPTIONAL enhancement - plain text extraction still works as before.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path
import re

import pymupdf as fitz
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class StructureNode(BaseModel):
    """Represents a section/chapter in the document"""

    level: int  # 0=Part, 1=Chapter, 2=Section, 3=Subsection
    title: str
    char_offset: int  # Start position in full text
    char_end: int  # End position in full text
    page: Optional[int] = None  # Original page number (PDF only)


def extract_pdf_toc(pdf_path: str) -> List[StructureNode]:
    """
    Extract Table of Contents from PDF if available.

    Uses PyMuPDF's built-in TOC extraction which works for PDFs that
    have embedded TOC metadata.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of StructureNode objects representing TOC hierarchy
    """
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()  # Returns [(level, title, page), ...]
        doc.close()

        if not toc:
            logger.info("No embedded TOC found in PDF")
            return []

        # Convert to StructureNode format
        # Note: char offsets will be filled in later when we have full text
        nodes = []
        for level, title, page in toc:
            node = StructureNode(
                level=level - 1,  # Normalize: level 1 → 0, level 2 → 1, etc.
                title=title.strip(),
                char_offset=0,  # Placeholder - will be calculated
                char_end=0,  # Placeholder - will be calculated
                page=page,
            )
            nodes.append(node)

        logger.info(f"Extracted {len(nodes)} TOC entries from PDF")
        return nodes

    except Exception as e:
        logger.warning(f"TOC extraction failed: {e}")
        return []


def extract_pdf_structure_by_fonts(
    pdf_path: str, text: str
) -> List[StructureNode]:
    """
    Extract document structure by analyzing font sizes.

    Headings typically use larger or bold fonts. This method:
    1. Analyzes font size distribution
    2. Identifies outlier sizes (likely headings)
    3. Maps headings to their positions in the extracted text

    Args:
        pdf_path: Path to PDF file
        text: Extracted plain text (for position mapping)

    Returns:
        List of StructureNode objects detected by font analysis
    """
    try:
        doc = fitz.open(pdf_path)

        # Collect all text blocks with font information
        font_data = []
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font_data.append(
                                {
                                    "text": span["text"],
                                    "size": span["size"],
                                    "flags": span[
                                        "flags"
                                    ],  # Bold, italic, etc.
                                    "page": page_num + 1,
                                }
                            )

        doc.close()

        if not font_data:
            logger.info("No font data found in PDF")
            return []

        # Calculate median font size (body text)
        sizes = [d["size"] for d in font_data]
        sizes.sort()
        median_size = sizes[len(sizes) // 2]

        # Identify potential headings (size > median + 2 points)
        threshold = median_size + 2
        heading_candidates = []

        for item in font_data:
            if item["size"] >= threshold:
                # Check if text looks like a heading (short, capitalized, etc.)
                text_content = item["text"].strip()
                if not text_content:
                    continue

                # Heuristics for heading detection
                is_short = len(text_content) < 100
                has_chapter_keyword = re.search(
                    r"\b(chapter|part|section|book|volume)\b",
                    text_content,
                    re.IGNORECASE,
                )
                is_mostly_caps = (
                    sum(c.isupper() for c in text_content if c.isalpha())
                    / max(1, len([c for c in text_content if c.isalpha()]))
                    > 0.7
                )

                if is_short and (has_chapter_keyword or is_mostly_caps):
                    heading_candidates.append(
                        {
                            "title": text_content,
                            "size": item["size"],
                            "page": item["page"],
                        }
                    )

        # Determine heading levels based on font size
        # Largest = Part, next = Chapter, etc.
        if not heading_candidates:
            logger.info("No headings detected by font analysis")
            return []

        unique_sizes = sorted(
            set(h["size"] for h in heading_candidates), reverse=True
        )
        size_to_level = {size: idx for idx, size in enumerate(unique_sizes)}

        # Create StructureNode objects
        nodes = []
        for heading in heading_candidates:
            # Try to find position in text
            title = heading["title"]
            char_offset = text.find(title)

            if char_offset == -1:
                # Try case-insensitive search
                pattern = re.escape(title)
                match = re.search(pattern, text, re.IGNORECASE)
                char_offset = match.start() if match else 0

            node = StructureNode(
                level=size_to_level[heading["size"]],
                title=title,
                char_offset=char_offset,
                char_end=char_offset + len(title),  # Approximate
                page=heading["page"],
            )
            nodes.append(node)

        # Sort by position in text
        nodes.sort(key=lambda n: n.char_offset)

        logger.info(f"Detected {len(nodes)} headings by font analysis")
        return nodes

    except Exception as e:
        logger.error(f"Font-based structure detection failed: {e}")
        return []


def detect_structure_heuristic(text: str) -> List[StructureNode]:
    """
    Fallback: Detect document structure using text pattern heuristics.

    Looks for common chapter/section markers like:
    - "Chapter 1", "Chapter I", "CHAPTER ONE"
    - "Part 1", "PART I"
    - "Section 1.1", "1.1 Introduction"
    - All-caps headings

    Args:
        text: Full document text

    Returns:
        List of StructureNode objects detected by pattern matching
    """
    nodes = []

    # Patterns for different heading levels
    patterns = {
        0: [  # Part level
            r"^(PART|BOOK|VOLUME)\s+([IVXLCDM]+|\d+|[A-Z]+)[:\.\s]*(.*?)$",
        ],
        1: [  # Chapter level
            r"^(CHAPTER|Ch\.|CHapter)\s+([IVXLCDM]+|\d+|[A-Z]+)[:\.\s]*(.*?)$",
            r"^([IVXLCDM]+|Chapter\s+\d+)\.\s+(.*?)$",
        ],
        2: [  # Section level
            r"^(SECTION|SEC\.?)\s+(\d+\.?\d*)[:\.\s]*(.*?)$",
            r"^(\d+\.)\s+([A-Z][a-z].{3,60})$",
        ],
    }

    lines = text.split("\n")
    current_pos = 0

    for line_num, line in enumerate(lines):
        line_stripped = line.strip()

        if not line_stripped or len(line_stripped) < 3:
            current_pos += len(line) + 1
            continue

        # Try patterns
        for level, pattern_list in patterns.items():
            matched = False
            for pattern in pattern_list:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    title = line_stripped
                    node = StructureNode(
                        level=level,
                        title=title,
                        char_offset=current_pos,
                        char_end=current_pos + len(line),
                        page=None,
                    )
                    nodes.append(node)
                    matched = True
                    break

            if matched:
                break

        # Check for all-caps headings (likely section titles)
        if (
            not matched
            and line_stripped.isupper()
            and 5 <= len(line_stripped) <= 60
        ):
            # Avoid false positives (acronyms, repeated words)
            if line_stripped.count(" ") >= 1 and not line_stripped.startswith(
                "  "
            ):
                node = StructureNode(
                    level=2,  # Assume section-level
                    title=line_stripped,
                    char_offset=current_pos,
                    char_end=current_pos + len(line),
                    page=None,
                )
                nodes.append(node)

        current_pos += len(line) + 1  # +1 for newline

    if nodes:
        logger.info(f"Detected {len(nodes)} headings by heuristic analysis")
    else:
        logger.info("No headings detected by heuristic analysis")

    return nodes


def calculate_section_boundaries(
    nodes: List[StructureNode], text_length: int
) -> List[StructureNode]:
    """
    Fill in char_end values for each node based on where the next section starts.

    Args:
        nodes: List of StructureNode objects (sorted by char_offset)
        text_length: Total length of document text

    Returns:
        Updated list with char_end filled in
    """
    if not nodes:
        return nodes

    # Sort by position
    nodes.sort(key=lambda n: n.char_offset)

    # Update char_end values
    for i in range(len(nodes) - 1):
        nodes[i].char_end = nodes[i + 1].char_offset

    # Last node extends to end of document
    nodes[-1].char_end = text_length

    return nodes


def extract_structure(
    pdf_path: str, text: str, enable_heuristic: bool = True
) -> List[StructureNode]:
    """
    Main entry point: Extract document structure using best available method.

    Priority order:
    1. Embedded PDF TOC (if available)
    2. Font-based detection (for PDFs)
    3. Heuristic pattern matching (fallback for all formats)

    Args:
        pdf_path: Path to PDF file (or None for non-PDF)
        text: Extracted plain text
        enable_heuristic: Whether to use heuristic fallback

    Returns:
        List of StructureNode objects representing document hierarchy
    """
    nodes = []

    # Try PDF-specific methods first
    if pdf_path and Path(pdf_path).suffix.lower() == ".pdf":
        # Method 1: Embedded TOC
        nodes = extract_pdf_toc(pdf_path)

        # Method 2: Font analysis (if TOC didn't work)
        if not nodes:
            nodes = extract_pdf_structure_by_fonts(pdf_path, text)

    # Fallback: Heuristic detection
    if not nodes and enable_heuristic:
        logger.info("Using heuristic structure detection (fallback)")
        nodes = detect_structure_heuristic(text)

    # Calculate boundaries
    if nodes:
        nodes = calculate_section_boundaries(nodes, len(text))
        logger.info(f"Final structure: {len(nodes)} sections detected")
    else:
        logger.info("No document structure detected - will use fixed chunking")

    return nodes


def structure_to_dict(nodes: List[StructureNode]) -> List[Dict]:
    """Convert StructureNode list to JSON-serializable dict format."""
    return [node.model_dump() for node in nodes]
