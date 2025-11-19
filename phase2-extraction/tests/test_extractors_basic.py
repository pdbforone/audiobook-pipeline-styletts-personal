"""
Basic tests for Phase 2 extractors

Tests verify that extractors:
1. Can be imported
2. Return expected format (text, metadata)
3. Handle errors gracefully
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_pdf_extractor_import():
    """Test that PDF extractor can be imported."""
    from phase2_extraction.extractors import pdf
    assert hasattr(pdf, 'extract')


def test_docx_extractor_import():
    """Test that DOCX extractor can be imported."""
    from phase2_extraction.extractors import docx
    assert hasattr(docx, 'extract')


def test_epub_extractor_import():
    """Test that EPUB extractor can be imported."""
    from phase2_extraction.extractors import epub
    assert hasattr(epub, 'extract')


def test_html_extractor_import():
    """Test that HTML extractor can be imported."""
    from phase2_extraction.extractors import html
    assert hasattr(html, 'extract')


def test_txt_extractor_import():
    """Test that TXT extractor can be imported."""
    from phase2_extraction.extractors import txt
    assert hasattr(txt, 'extract')


def test_ocr_extractor_import():
    """Test that OCR extractor can be imported."""
    from phase2_extraction.extractors import ocr
    assert hasattr(ocr, 'extract')


def test_normalize_import():
    """Test that normalize module can be imported."""
    from phase2_extraction import normalize
    assert hasattr(normalize, 'normalize_text')


def test_utils_import():
    """Test that utils module can be imported."""
    from phase2_extraction import utils
    assert hasattr(utils, 'merge_phase_state')
    assert hasattr(utils, 'with_retry')
    assert hasattr(utils, 'detect_format')


def test_txt_extractor_basic():
    """Test TXT extractor with sample text."""
    from phase2_extraction.extractors import txt
    
    # Create a temporary text file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("This is a test.\nThis is line 2.\n\nNew paragraph.")
        temp_path = Path(f.name)
    
    try:
        text, metadata = txt.extract(temp_path)
        
        # Verify output format
        assert isinstance(text, str)
        assert isinstance(metadata, dict)
        
        # Verify content
        assert len(text) > 0
        assert "test" in text.lower()
        
        # Verify metadata
        assert 'title' in metadata
        assert 'quality_score' in metadata or 'char_count' in metadata
        
    finally:
        temp_path.unlink()


def test_normalize_text_basic():
    """Test basic text normalization."""
    from phase2_extraction.normalize import normalize_text
    
    # Sample text with issues
    raw_text = "This  has   multiple spaces.\n\n\n\nToo many newlines.\n"
    
    # Normalize
    normalized, metrics = normalize_text(raw_text, "test_file")
    
    # Verify output format
    assert isinstance(normalized, str)
    assert isinstance(metrics, dict)
    
    # Verify normalization happened
    assert "  " not in normalized  # Multiple spaces should be collapsed
    assert "\n\n\n\n" not in normalized  # Excessive newlines removed
    
    # Verify metrics
    assert 'changes' in metrics
    assert 'text_yield' in metrics


def test_detect_format():
    """Test format detection."""
    from phase2_extraction.utils import detect_format
    
    # Test with various extensions
    assert detect_format(Path("test.pdf")) == "pdf"
    assert detect_format(Path("test.docx")) == "docx"
    assert detect_format(Path("test.epub")) == "epub"
    assert detect_format(Path("test.html")) == "html"
    assert detect_format(Path("test.txt")) == "txt"


def test_calculate_yield():
    """Test yield calculation."""
    from phase2_extraction.utils import calculate_yield
    
    # Test normal yield
    yield_pct = calculate_yield(1000, 900)
    assert 0.8 < yield_pct < 1.0
    
    # Test zero size
    yield_pct = calculate_yield(0, 100)
    assert yield_pct == 0.0


def test_with_retry_success():
    """Test retry logic with successful function."""
    from phase2_extraction.utils import with_retry
    
    mock_func = Mock(return_value="success")
    result = with_retry(mock_func, max_attempts=3)
    
    assert result == "success"
    assert mock_func.call_count == 1


def test_with_retry_eventual_success():
    """Test retry logic with function that succeeds on second try."""
    from phase2_extraction.utils import with_retry
    
    mock_func = Mock(side_effect=[IOError("temp failure"), "success"])
    result = with_retry(mock_func, max_attempts=3, delay=0.1)
    
    assert result == "success"
    assert mock_func.call_count == 2


def test_with_retry_all_fail():
    """Test retry logic with function that always fails."""
    from phase2_extraction.utils import with_retry
    
    mock_func = Mock(side_effect=IOError("persistent failure"))
    
    with pytest.raises(IOError):
        with_retry(mock_func, max_attempts=3, delay=0.1)
    
    assert mock_func.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
