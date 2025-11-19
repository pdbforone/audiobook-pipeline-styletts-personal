import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from phase1_validation import validation
from phase1_validation.utils import safe_update_json


def _mock_pdf_doc(text_len: int = 600) -> MagicMock:
    page = MagicMock()
    page.get_text.return_value = "text" * (text_len // 4)
    page.rect.width = 100
    page.rect.height = 100
    doc = MagicMock()
    doc.__len__.return_value = 1
    doc.__iter__.return_value = [page]
    doc.metadata = {}
    doc.close.return_value = None
    return doc


def test_compute_sha256(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("data", encoding="utf-8")
    result = validation.compute_sha256(file_path)
    assert result == validation.compute_sha256(file_path)  # deterministic


def test_validate_pdf_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"pdf-bytes")

    mock_doc = _mock_pdf_doc()
    monkeypatch.setattr(validation.fitz, "open", MagicMock(return_value=mock_doc))

    result = validation.validate_and_repair(
        str(pdf_path), artifacts_dir=str(tmp_path / "artifacts"), pipeline_json=None, file_id=None
    )
    assert isinstance(result, validation.FileMetadata)
    assert result.classification == "text"
    assert result.repair_attempted is False


def test_validate_pdf_repair_flow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"pdf-bytes")

    repaired_doc = _mock_pdf_doc()
    fitz_open = MagicMock(side_effect=[Exception("Corrupted"), repaired_doc, repaired_doc, repaired_doc])
    monkeypatch.setattr(validation.fitz, "open", fitz_open)

    pdf_ctx = MagicMock()
    pdf_ctx.__enter__.return_value = MagicMock(save=lambda *args, **kwargs: None)
    pdf_ctx.__exit__.return_value = None
    monkeypatch.setattr(validation.pikepdf, "open", MagicMock(return_value=pdf_ctx))

    result = validation.validate_and_repair(
        str(pdf_path), artifacts_dir=str(tmp_path / "artifacts"), pipeline_json=None, file_id=None
    )
    assert result is not None
    assert result.repair_attempted is True
    assert result.repair_success is True


def test_safe_update_json_merges_without_overwrite(tmp_path: Path):
    json_path = tmp_path / "pipeline.json"
    initial = {"phase2": {"status": "done"}, "phase1": {"hashes": ["abc"], "files": {}}}
    json_path.write_text(json.dumps(initial), encoding="utf-8")

    update = {"phase1": {"hashes": ["abc", "def"], "files": {"book": {"sha256": "def"}}}}
    merged = safe_update_json(json_path, update)

    assert merged["phase2"]["status"] == "done"
    assert merged["phase1"]["hashes"] == ["abc", "def"]
    assert "book" in merged["phase1"]["files"]
