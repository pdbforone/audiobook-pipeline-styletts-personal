import pytest
from unittest.mock import patch, MagicMock
import sqlite3
from phase2_extraction.extraction import (
    compute_sha256,
    get_file_info,
    classify_pdf,
    extract_text_text_pdf,
    extract_with_paddleocr,
    extract_with_unstructured,
    extract_with_easyocr,
    extract_text_pdf,
    extract_text_epub,
    extract_text_docx,
    extract_text_txt,
    check_gibberish,
    check_perplexity,
    check_language,
    main,
    ExtractionConfig,
)


@pytest.fixture
def mock_config():
    return ExtractionConfig(db_path="test.db", file_path="test.pdf")


@pytest.fixture
def mock_db(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE files (hash TEXT PRIMARY KEY, file_type TEXT, classification TEXT)"
    )
    cursor.execute("INSERT INTO files VALUES ('hash', 'pdf', 'mixed')")
    conn.commit()
    conn.close()
    return str(db)


@patch("hashlib.sha256")
def test_compute_sha256(mock_sha):
    mock_sha.return_value.hexdigest.return_value = "hash"
    assert compute_sha256("test.pdf") == "hash"


@patch("sqlite3.connect")
def test_get_file_info(mock_conn, mock_db):
    mock_cursor = MagicMock()
    mock_conn.return_value.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = ("pdf", "mixed")
    assert get_file_info(mock_db, "hash") == ("pdf", "mixed")


@patch("fitz.open")
def test_classify_pdf(mock_fitz):
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_page = MagicMock()
    mock_page.get_text.return_value = "text"
    mock_doc.__iter__.return_value = [mock_page]
    mock_fitz.return_value = mock_doc
    with patch("os.path.getsize", return_value=100):
        assert classify_pdf("test.pdf") == "text"


@patch("pdfplumber.open")
@patch("fitz.open")
def test_extract_text_text_pdf(mock_fitz, mock_pdfplumber):
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock(extract_text=lambda: "text")]
    mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
    assert extract_text_text_pdf("test.pdf") == "text"


@patch("phase2_extraction.extraction.PaddleOCR")
def test_extract_with_paddleocr(mock_ocr):
    mock_instance = MagicMock()
    mock_instance.ocr.return_value = [[[[[1, 1]], ("text", 0.9)]]]
    mock_ocr.return_value = mock_instance
    assert extract_with_paddleocr("test.pdf") == "text"


# Similar mocks for unstructured, easyocr, epub, docx, txt


@patch("phase2_extraction.extraction.extract_text_text_pdf", return_value="text")
@patch("phase2_extraction.extraction.extract_with_paddleocr", return_value="text")
def test_extract_text_pdf(mock_paddle, mock_text):
    assert extract_text_pdf("test.pdf", "text", 1) == "text"
    assert extract_text_pdf("test.pdf", "mixed", 1) == "text"


@patch("nltk.word_tokenize", return_value=["token"])
def test_check_perplexity(mock_tok):
    assert check_perplexity("text") < float("inf")


def test_check_language():
    is_en, diag = check_language("This is English.")
    assert is_en


@patch("phase2_extraction.extraction.get_file_info", return_value=("pdf", "text"))
@patch("phase2_extraction.extraction.extract_text_pdf", return_value="text")
@patch("phase2_extraction.extraction.check_gibberish", return_value=0.5)
@patch("phase2_extraction.extraction.check_perplexity", return_value=200.0)
@patch("phase2_extraction.extraction.check_language", return_value=(True, "en 0.95"))
@patch("os.makedirs")
@patch("builtins.open")
def test_main(
    mock_open,
    mock_mkdir,
    mock_lang,
    mock_perp,
    mock_gib,
    mock_extract,
    mock_info,
    mock_config,
):
    main(mock_config)  # No raise


# Add more: exceptions, retries, non-PDF; run pytest --cov=src/phase2_extraction for >85%
