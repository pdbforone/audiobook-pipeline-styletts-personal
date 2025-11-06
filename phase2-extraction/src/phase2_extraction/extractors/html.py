"""
HTML Text Extractor

Extracts clean text from HTML files using readability algorithm.

Reason: HTML files often contain navigation, ads, and other non-content.
The readability algorithm extracts the main article/content body.
"""

from pathlib import Path
from typing import Tuple, Dict
import logging

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from readability import Document as ReadabilityDocument
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract(path: Path) -> Tuple[str, Dict]:
    """
    Extract text from HTML file focusing on main content.
    
    Args:
        path: Path to HTML file
        
    Returns:
        (text, metadata) with cleaned text and basic metadata
        
    Reason: Readability algorithm helps filter out navigation, headers,
    footers, and other non-content elements that would confuse TTS.
    """
    if not BS4_AVAILABLE:
        error_msg = "beautifulsoup4 library not available. Install with: poetry add beautifulsoup4 lxml"
        logger.error(error_msg)
        return "", {
            "title": path.stem,
            "error": error_msg,
            "quality_score": 0.0
        }
    
    logger.info(f"Extracting HTML: {path.name}")
    
    try:
        # Read HTML file
        with path.open('r', encoding='utf-8', errors='replace') as f:
            html_content = f.read()
        
        # Try readability extraction if available
        if READABILITY_AVAILABLE:
            try:
                logger.debug("Using readability algorithm for content extraction")
                doc = ReadabilityDocument(html_content)
                title = doc.title()
                summary_html = doc.summary()
                
                # Parse the cleaned HTML
                soup = BeautifulSoup(summary_html, 'lxml')
                
            except Exception as e:
                logger.warning(f"Readability extraction failed: {e}, falling back to basic extraction")
                soup = BeautifulSoup(html_content, 'lxml')
                title = path.stem
        else:
            logger.debug("Readability not available, using basic HTML parsing")
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Try to extract title from HTML
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else path.stem
        
        # Remove script, style, and navigation elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()
        
        # Extract text with proper spacing
        text = soup.get_text(separator="\n", strip=True)
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        metadata = {
            "title": title or path.stem,
            "char_count": len(text),
            "source_format": "html"
        }
        
        # Quality assessment
        if not text.strip():
            logger.warning("No text extracted from HTML")
            metadata["quality_score"] = 0.0
            metadata["error"] = "Empty HTML or no readable content"
        elif len(text) < 100:
            logger.warning(f"Very short HTML content: {len(text)} chars")
            metadata["quality_score"] = 0.5
        else:
            metadata["quality_score"] = 1.0
            logger.info(f"✓ Extracted {len(text):,} chars")
        
        # Check for common issues
        if text.count('\n') / len(text) > 0.1:
            logger.warning("High line break density - HTML may have formatting issues")
            metadata["quality_score"] *= 0.9
        
        return text, metadata
        
    except Exception as e:
        logger.error(f"HTML extraction failed: {type(e).__name__}: {e}")
        return "", {
            "title": path.stem,
            "error": f"Extraction failed: {type(e).__name__}: {str(e)}",
            "quality_score": 0.0
        }
