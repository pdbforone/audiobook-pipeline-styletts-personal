"""
Phase 2 Extractors Module

Format-specific text extraction for audiobook pipeline.
Each extractor returns (text: str, metadata: dict).
"""

from . import pdf
from . import docx
from . import epub
from . import html
from . import txt
from . import ocr

__all__ = ["pdf", "docx", "epub", "html", "txt", "ocr"]
