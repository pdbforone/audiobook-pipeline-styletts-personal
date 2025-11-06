import hashlib
import pytest
from unittest.mock import patch, mock_open, MagicMock
from phase1_validation.validation import validate_and_repair, FileMetadata, compute_sha256
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)  # Suppress SWIG deprecations

@pytest.fixture
def mock_path_obj():
    mock = MagicMock()
    mock.exists.return_value = True
    mock.suffix = '.pdf'
    mock.stat.return_value.st_size = 100  # Small size
    return mock

@pytest.fixture
def mock_file():
    return "test.pdf"

@patch("phase1_validation.validation.os.access", return_value=True)
@patch("phase1_validation.validation.Path")
@patch("phase1_validation.validation.hachoir.parser.createParser")
@patch("phase1_validation.validation.pikepdf.open")
@patch("phase1_validation.validation.fitz.open")
def test_validate_pdf_success(mock_fitz, mock_pikepdf, mock_parser, mock_path, mock_os_access, mock_path_obj, mock_file):
    mock_path.return_value = mock_path_obj
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_page = MagicMock()
    mock_page.get_text.return_value = "text" * 130  # 520 chars > 0.05 * 10000 = 500
    mock_page.rect.width = 100
    mock_page.rect.height = 100
    mock_doc.__iter__.return_value = [mock_page]
    mock_fitz.return_value = mock_doc
    mock_parser.return_value = MagicMock()  # For metadata
    with patch("builtins.open") as mock_open:
        mock_file_obj = MagicMock()
        mock_file_obj.read.side_effect = [b"fake_data", b""]  # Simulate chunks and EOF for SHA256
        mock_open.return_value.__enter__.return_value = mock_file_obj
        metadata = validate_and_repair(mock_file)
    assert metadata.classification == "text"
    assert isinstance(metadata, FileMetadata)

@patch("builtins.open", mock_open(read_data=b"data"))
def test_compute_sha256():
    assert compute_sha256("dummy") == hashlib.sha256(b"data").hexdigest()

@patch("phase1_validation.validation.os.access", return_value=True)
@patch("phase1_validation.validation.Path")
@patch("phase1_validation.validation.repair_pdf", return_value=True)
@patch("phase1_validation.validation.fitz.open")
def test_repair_pdf_success(mock_fitz, mock_repair, mock_path, mock_os_access, mock_path_obj, mock_file):
    mock_path.return_value = mock_path_obj
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_page = MagicMock()
    mock_page.get_text.return_value = "text" * 130  # Consistent with success test
    mock_page.rect.width = 100
    mock_page.rect.height = 100
    mock_doc.__iter__.return_value = [mock_page]
    mock_fitz.side_effect = [Exception("Corrupted"), mock_doc]
    with patch("builtins.open") as mock_open:
        mock_file_obj = MagicMock()
        mock_file_obj.read.side_effect = [b"fake_data", b""]  # Simulate chunks and EOF for SHA256
        mock_open.return_value.__enter__.return_value = mock_file_obj
        metadata = validate_and_repair(mock_file)
    assert metadata is not None  # Repair succeeded

@patch("phase1_validation.validation.os.access", return_value=True)
@patch("phase1_validation.validation.Path")
@patch("phase1_validation.validation.repair_pdf", return_value=False)
@patch("phase1_validation.validation.fitz.open", side_effect=Exception("Corrupted"))
def test_repair_pdf_failure(mock_fitz, mock_repair, mock_path, mock_os_access, mock_path_obj, mock_file):
    mock_path.return_value = mock_path_obj
    metadata = validate_and_repair(mock_file)
    assert metadata is None  # Repair failed

# Expand for EPUB/D