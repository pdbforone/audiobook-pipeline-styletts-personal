import argparse
import json
import logging
import os
import shutil
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

import chardet
import ebooklib
import ftfy
import hachoir.metadata
import hachoir.parser
import pikepdf
import pymupdf as fitz  # PyMuPDF
from docx import Document
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pipeline_common import PipelineState, StateError, ensure_phase_and_file, ensure_phase_block
from pipeline_common.state_manager import StateTransaction

from .utils import compute_sha256 as utils_compute_sha256
from .utils import log_error

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PHASE_NAME = "phase1"
SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".docx", ".txt"}


def _install_update_phase_api() -> None:
    """Ensure StateTransaction objects expose update_phase for schema-safe writes."""

    if hasattr(StateTransaction, "update_phase"):
        return

    def update_phase(  # type: ignore[override]
        self,
        file_id: str,
        phase_name: str,
        status: str,
        timestamps: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Any] = None,
        metrics: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Any]] = None,
        *,
        chunks: Optional[List[Dict[str, Any]]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        phase_block, file_entry = ensure_phase_and_file(self.data, phase_name, file_id)
        envelope = file_entry
        envelope["status"] = status
        envelope["timestamps"] = dict(timestamps or {})
        envelope["artifacts"] = artifacts if artifacts is not None else {}
        envelope["metrics"] = dict(metrics or {})
        envelope["errors"] = list(errors or [])
        envelope["chunks"] = list(chunks or [])
        if extra_fields:
            envelope.update(extra_fields)
        return envelope

    setattr(StateTransaction, "update_phase", update_phase)


_install_update_phase_api()


class PDFParsingError(Exception):
    """Raised when a PDF cannot be parsed or re-opened after repair."""


class EncodingIssue(Exception):
    """Raised when we cannot decode text content after repair attempts."""


class FileValidationError(Exception):
    """Generic validation failure for unsupported formats."""


class FileMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    file_path: str
    file_type: str
    classification: str
    size_bytes: int
    sha256: str
    repair_attempted: bool
    repair_success: bool
    errors: List[str] = Field(default_factory=list)
    timestamps: Dict[str, float]
    page_count: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None
    artifacts_path: Optional[str] = None
    duplicate: bool = False
    metrics: Optional[Dict[str, float]] = None
    hash: Optional[str] = None  # Backwards compatibility alias
    file_size_bytes: Optional[int] = None  # Backwards compatibility alias

    def as_payload(self) -> Dict[str, Any]:
        payload = self.model_dump()
        payload["hash"] = payload.get("hash") or self.sha256
        payload["sha256"] = self.sha256
        payload.setdefault("file_size_bytes", self.size_bytes)
        if self.metrics is None and "duration" in self.timestamps:
            payload["metrics"] = {"elapsed_time": self.timestamps["duration"]}
        return payload


def compute_sha256(file_path: str | Path) -> str:
    """Re-exported for compatibility with existing callers/tests."""
    return utils_compute_sha256(Path(file_path))


def _alphabetic_ratio(text: str) -> float:
    tokens = [token for token in text.split() if token]
    if not tokens:
        return 0.0
    ratios = []
    for token in tokens:
        letters = sum(1 for ch in token if ch.isalpha())
        ratios.append(letters / len(token))
    return sum(ratios) / len(ratios)


def classify_pdf(file_path: Path) -> str:
    """
    Classify a PDF using a deterministic heuristic:
    - Extractable text length
    - Pagewise density (chars per page area)
    - Replacement character count
    - Average token alphabetic ratio
    """
    doc = fitz.open(file_path)
    total_pages = len(doc)
    total_text_len = 0
    total_replacements = 0
    alpha_ratios: List[float] = []
    text_like_pages = 0
    dense_pages = 0

    for page in doc:
        text = page.get_text() or ""
        cleaned = text.strip()
        length = len(cleaned)
        total_text_len += length
        replacements = cleaned.count("\ufffd")
        total_replacements += replacements

        alpha_ratio = _alphabetic_ratio(cleaned)
        if alpha_ratio:
            alpha_ratios.append(alpha_ratio)

        page_area = max(float(page.rect.width * page.rect.height), 1.0)
        density = length / page_area
        if length >= 150 or (length >= 60 and alpha_ratio >= 0.55):
            text_like_pages += 1
        if density > 0.001:
            dense_pages += 1

    doc.close()

    text_ratio = text_like_pages / total_pages if total_pages else 0.0
    density_ratio = dense_pages / total_pages if total_pages else 0.0
    avg_alpha = sum(alpha_ratios) / len(alpha_ratios) if alpha_ratios else 0.0
    replacement_ratio = total_replacements / total_text_len if total_text_len else 0.0

    classification = "mixed"
    if total_pages == 0:
        classification = "unknown"
    elif text_ratio > 0.8 and avg_alpha > 0.6 and replacement_ratio < 0.05:
        classification = "text"
    elif (text_ratio < 0.2 and total_text_len < 800 and density_ratio < 0.25) or (
        replacement_ratio > 0.2 and text_ratio < 0.5
    ):
        classification = "scanned"

    logger.info(
        "PDF classification=%s text_ratio=%.2f density_ratio=%.2f avg_alpha=%.2f replacement_ratio=%.3f total_text=%s",
        classification,
        text_ratio,
        density_ratio,
        avg_alpha,
        replacement_ratio,
        total_text_len,
    )
    return classification


def classify_file(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return classify_pdf(file_path)
    if ext in {".txt", ".epub", ".docx"}:
        return "text"
    return "unknown"


def repair_pdf(file_path: Path, retries: int = 2) -> bool:
    for attempt in range(1, retries + 1):
        try:
            with pikepdf.open(file_path, allow_overwriting_input=True) as pdf:
                pdf.save(file_path)
            logger.info("PDF repair attempt %s succeeded.", attempt)
            return True
        except Exception as exc:
            logger.warning("PDF repair attempt %s failed: %s", attempt, exc)
    return False


def repair_epub(file_path: Path, retries: int = 2) -> bool:
    for attempt in range(1, retries + 1):
        try:
            book = ebooklib.epub.read_epub(file_path)
            ebooklib.epub.write_epub(file_path, book)
            logger.info("EPUB repair attempt %s succeeded.", attempt)
            return True
        except Exception as exc:
            logger.warning("EPUB repair attempt %s failed: %s", attempt, exc)
    return False


def repair_docx(file_path: Path, retries: int = 2) -> bool:
    for attempt in range(1, retries + 1):
        try:
            doc = Document(file_path)
            doc.save(file_path)
            logger.info("DOCX repair attempt %s succeeded.", attempt)
            return True
        except Exception as exc:
            logger.warning("DOCX repair attempt %s failed: %s", attempt, exc)
    return False


def repair_txt(file_path: Path, retries: int = 2) -> bool:
    for attempt in range(1, retries + 1):
        try:
            with open(file_path, "rb") as handle:
                raw = handle.read()
            encoding = chardet.detect(raw)["encoding"] or "utf-8"
            text = ftfy.fix_text(raw.decode(encoding, errors="replace"))
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(text)
            logger.info("TXT repair attempt %s succeeded with detected encoding %s.", attempt, encoding)
            return True
        except Exception as exc:
            logger.warning("TXT repair attempt %s failed: %s", attempt, exc)
    return False


def validate_pdf(file_path: Path, retries: int, errors: List[str]) -> Tuple[Dict[str, Any], bool, bool]:
    details: Dict[str, Any] = {}
    repair_attempted = False
    repair_success = False
    doc = None
    try:
        doc = fitz.open(file_path)
        details["page_count"] = len(doc)
    except Exception as exc:
        repair_attempted = True
        errors.append(str(exc))
        logger.info("PDF validation failed; attempting repair.")
        repair_success = repair_pdf(file_path, retries)
        if not repair_success:
            raise PDFParsingError(str(exc))
        try:
            doc = fitz.open(file_path)
            details["page_count"] = len(doc)
        except Exception as reopened_exc:
            errors.append(str(reopened_exc))
            raise PDFParsingError(str(reopened_exc))
    finally:
        try:
            doc.close()  # type: ignore[has-type]
        except Exception:
            pass
    return details, repair_attempted, repair_success


def validate_epub(file_path: Path, retries: int, errors: List[str]) -> Tuple[Dict[str, Any], bool, bool]:
    repair_attempted = False
    repair_success = False
    try:
        ebooklib.epub.read_epub(file_path)
    except Exception as exc:
        repair_attempted = True
        errors.append(str(exc))
        logger.info("EPUB validation failed; attempting repair.")
        repair_success = repair_epub(file_path, retries)
        if not repair_success:
            raise FileValidationError(str(exc))
    return {}, repair_attempted, repair_success


def validate_docx(file_path: Path, retries: int, errors: List[str]) -> Tuple[Dict[str, Any], bool, bool]:
    repair_attempted = False
    repair_success = False
    try:
        Document(file_path)
    except Exception as exc:
        repair_attempted = True
        errors.append(str(exc))
        logger.info("DOCX validation failed; attempting repair.")
        repair_success = repair_docx(file_path, retries)
        if not repair_success:
            raise FileValidationError(str(exc))
    return {}, repair_attempted, repair_success


def validate_txt(file_path: Path, retries: int, errors: List[str]) -> Tuple[Dict[str, Any], bool, bool]:
    repair_attempted = False
    repair_success = False
    try:
        with open(file_path, "r", encoding="utf-8", errors="strict") as handle:
            handle.read()
    except UnicodeDecodeError as exc:
        repair_attempted = True
        errors.append(str(exc))
        logger.info("TXT validation failed; attempting repair.")
        repair_success = repair_txt(file_path, retries)
        if not repair_success:
            raise EncodingIssue(str(exc))
    except Exception as exc:
        errors.append(str(exc))
        raise FileValidationError(str(exc))
    return {}, repair_attempted, repair_success


def extract_metadata(file_path: Path) -> Dict[str, Optional[str]]:
    file_ext = file_path.suffix.lower()
    metadata_dict: Dict[str, Optional[str]] = {"title": None, "author": None, "creation_date": None}

    if file_ext == ".pdf":
        try:
            doc = fitz.open(file_path)
            pdf_meta = doc.metadata or {}
            metadata_dict["title"] = pdf_meta.get("title")
            metadata_dict["author"] = pdf_meta.get("author")
            metadata_dict["creation_date"] = pdf_meta.get("creationDate")
            doc.close()
        except Exception as exc:
            logger.warning("PyMuPDF metadata extraction failed: %s", exc)

    try:
        parser = hachoir.parser.createParser(str(file_path))
        if parser:
            extracted = hachoir.metadata.extractMetadata(parser)
            if extracted:
                metadata_dict["title"] = metadata_dict["title"] or extracted.get("title")
                metadata_dict["author"] = metadata_dict["author"] or extracted.get("author")
                metadata_dict["creation_date"] = metadata_dict["creation_date"] or extracted.get("creation_date")
    except Exception as exc:
        logger.warning("Hachoir metadata extraction failed: %s", exc)

    for key, value in list(metadata_dict.items()):
        if value:
            metadata_dict[key] = ftfy.fix_text(value)

    logger.info("Extracted metadata: %s", metadata_dict)
    return metadata_dict


def write_artifacts(file_path: Path, artifacts_dir: Path) -> Optional[str]:
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        destination = artifacts_dir / file_path.name
        shutil.copy(file_path, destination)
        logger.info("Wrote repaired artifact to %s", destination)
        return str(destination)
    except Exception as exc:
        logger.warning("Failed to write artifact copy: %s", exc)
        return None


def _categorize_error(exc: Exception, file_ext: str) -> str:
    if isinstance(exc, PDFParsingError):
        return "PDF parsing"
    if isinstance(exc, EncodingIssue):
        return "Encoding"
    if isinstance(exc, (OSError, IOError, FileNotFoundError)):
        return "IO"
    if file_ext == ".pdf":
        return "PDF parsing"
    return "general"


def _read_pipeline_data(json_path: Path) -> Dict[str, Any]:
    state = PipelineState(json_path, validate_on_read=False)
    try:
        return state.read(validate=False)
    except (StateError, FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Phase 1: pipeline read failed (%s)", exc)
        return {}


def _load_existing_metadata(pipeline_json: Path, file_id: str, sha256_hash: str, size_bytes: int) -> Optional[FileMetadata]:
    data = _read_pipeline_data(pipeline_json)
    record = data.get(PHASE_NAME, {}).get("files", {}).get(file_id)
    if not record:
        return None

    recorded_hash = record.get("sha256") or record.get("hash")
    if recorded_hash != sha256_hash:
        return None

    record["sha256"] = recorded_hash
    record["hash"] = recorded_hash
    record["size_bytes"] = record.get("size_bytes") or record.get("file_size_bytes") or size_bytes
    record["file_size_bytes"] = record.get("file_size_bytes") or record["size_bytes"]
    record["repair_attempted"] = record.get("repair_attempted", record.get("repair_status") is not None)
    record["repair_success"] = record.get("repair_success", record.get("repair_status") != "skipped")
    record.setdefault("errors", [])
    record.setdefault("timestamps", {})

    try:
        return FileMetadata(**record)
    except ValidationError as exc:
        logger.warning("Phase 1 reuse record invalid; will recompute: %s", exc)
        return None


def _flag_duplicate_hash(json_path: Optional[Path], file_id: str, metadata: FileMetadata) -> None:
    if not json_path:
        return
    existing = _read_pipeline_data(json_path)
    hashes = existing.get(PHASE_NAME, {}).get("hashes", [])
    if metadata.sha256 in hashes:
        metadata.duplicate = True
        message = f"Duplicate hash {metadata.sha256} for {file_id}"
        metadata.errors.append(message)
        log_error(json_path, PHASE_NAME, file_id, message, "Integrity")


def _phase1_artifacts_from_metadata(metadata: FileMetadata) -> Dict[str, Any]:
    """Normalize the artifact payload for schema v3."""
    artifacts: Dict[str, Any] = {
        "source_path": metadata.file_path,
        "artifacts_path": metadata.artifacts_path,
        "file_type": metadata.file_type,
        "classification": metadata.classification,
        "sha256": metadata.sha256,
        "hash": metadata.hash or metadata.sha256,
        "repair_attempted": metadata.repair_attempted,
        "repair_success": metadata.repair_success,
        "duplicate": metadata.duplicate,
        "page_count": metadata.page_count,
        "title": metadata.title,
        "author": metadata.author,
        "creation_date": metadata.creation_date,
    }
    return {key: value for key, value in artifacts.items() if value is not None}


def _phase1_metrics_from_metadata(metadata: FileMetadata) -> Dict[str, Any]:
    """Project numeric metadata into the metrics envelope."""
    metrics = dict(metadata.metrics or {})
    metrics.setdefault("size_bytes", metadata.size_bytes)
    metrics.setdefault("file_size_bytes", metadata.size_bytes)
    if metadata.page_count is not None:
        metrics.setdefault("page_count", metadata.page_count)
    metrics.setdefault("duplicate", 1 if metadata.duplicate else 0)
    if metadata.timestamps.get("duration") is not None:
        metrics.setdefault("duration", metadata.timestamps["duration"])
    return metrics


def persist_metadata(metadata: FileMetadata, json_path: Path, file_id: str) -> Dict[str, Any]:
    payload = metadata.as_payload()
    status = "success" if not metadata.errors else "partial"
    timestamps = payload.get("timestamps") or {}
    artifacts = _phase1_artifacts_from_metadata(metadata)
    metrics = _phase1_metrics_from_metadata(metadata)
    errors = list(metadata.errors)
    state = PipelineState(json_path, validate_on_read=False)
    with state.transaction(operation="phase1_persist") as txn:
        file_entry = txn.update_phase(
            file_id,
            PHASE_NAME,
            status,
            timestamps,
            artifacts,
            metrics,
            errors,
            chunks=[],
            extra_fields=payload,
        )
        phase_block = ensure_phase_block(txn.data, PHASE_NAME)
        hashes = set(phase_block.get("hashes") or [])
        if metadata.sha256:
            hashes.add(metadata.sha256)
        sorted_hashes = sorted(hashes)
        phase_block["hashes"] = sorted_hashes

        phase_artifacts = phase_block.get("artifacts")
        if isinstance(phase_artifacts, dict):
            phase_artifacts = dict(phase_artifacts)
        else:
            phase_artifacts = {}
        phase_artifacts["hashes"] = sorted_hashes
        phase_block["artifacts"] = phase_artifacts

        files = phase_block.get("files", {})
        phase_metrics = phase_block.setdefault("metrics", {})
        phase_metrics["files_processed"] = len(files)
        phase_metrics["duplicates"] = sum(1 for entry in files.values() if entry.get("duplicate"))
        phase_metrics["repaired"] = sum(1 for entry in files.values() if entry.get("repair_success"))

        phase_timestamps = phase_block.setdefault("timestamps", {})
        if timestamps.get("start") and "start" not in phase_timestamps:
            phase_timestamps["start"] = timestamps["start"]
        if timestamps.get("end"):
            phase_timestamps["last_completed"] = timestamps["end"]

        phase_block.setdefault("errors", [])
        phase_block.setdefault("chunks", [])

        if status != "success":
            phase_block["status"] = "partial"
        elif phase_block.get("status") not in {"partial", "failed"}:
            phase_block["status"] = "success"

        logger.info("Persisted metadata for %s into %s", file_id, json_path)
        return txn.data


def validate_and_repair(
    file_path: str,
    max_size_mb: int = 500,
    retries: int = 2,
    artifacts_dir: str = "artifacts/phase1",
    force: bool = False,
    mode: str = "thorough",
    pipeline_json: Optional[Path] = None,
    file_id: Optional[str] = None,
) -> Optional[FileMetadata]:
    start_time = perf_counter()
    path = Path(file_path)
    errors: List[str] = []

    if not path.exists() or not os.access(path, os.R_OK):
        logger.error("File not accessible.")
        return None
    if path.stat().st_size == 0:
        logger.error("File is empty.")
        return None
    if path.stat().st_size > max_size_mb * 1024 * 1024:
        logger.error("File exceeds size limit.")
        return None

    file_ext = path.suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        logger.error("Unsupported file type: %s", file_ext)
        return None

    size_bytes = path.stat().st_size
    sha256_hash = compute_sha256(path)

    if pipeline_json and file_id and not force:
        reused = _load_existing_metadata(pipeline_json, file_id, sha256_hash, size_bytes)
        if reused:
            logger.info("Phase 1: hash match found and force=False; skipping revalidation.")
            return reused

    if mode == "fast":
        meta = extract_metadata(path)
        end_time = perf_counter()
        duration = end_time - start_time
        try:
            metadata = FileMetadata(
                file_path=str(path.resolve()),
                file_type=file_ext.lstrip("."),
                classification="unknown",
                size_bytes=size_bytes,
                sha256=sha256_hash,
                hash=sha256_hash,
                repair_attempted=False,
                repair_success=False,
                errors=[],
                timestamps={"start": start_time, "end": end_time, "duration": duration},
                page_count=None,
                title=meta.get("title"),
                author=meta.get("author"),
                creation_date=meta.get("creation_date"),
                metrics={"elapsed_time": duration},
                file_size_bytes=size_bytes,
            )
            _flag_duplicate_hash(pipeline_json, file_id or "", metadata)
            return metadata
        except ValidationError as exc:
            logger.error("Metadata validation error (fast): %s", exc)
            return None

    validators = {
        ".pdf": validate_pdf,
        ".epub": validate_epub,
        ".docx": validate_docx,
        ".txt": validate_txt,
    }
    validate_func = validators.get(file_ext)
    repair_attempted = False
    repair_success = False
    page_count = None

    try:
        details, repair_attempted, repair_success = validate_func(path, retries, errors)  # type: ignore[arg-type]
        page_count = details.get("page_count")
    except Exception as exc:
        category = _categorize_error(exc, file_ext)
        errors.append(str(exc))
        if pipeline_json and file_id:
            log_error(pipeline_json, PHASE_NAME, file_id, str(exc), category)
        logger.error("Validation failed: %s", exc)
        return None

    artifacts_path = write_artifacts(path, Path(artifacts_dir)) if repair_success else None
    try:
        classification = classify_file(path)
    except Exception as exc:
        classification = "unknown"
        errors.append(str(exc))
        if pipeline_json and file_id:
            log_error(pipeline_json, PHASE_NAME, file_id, str(exc), _categorize_error(exc, file_ext))
        logger.error("Classification failed: %s", exc)
    meta = extract_metadata(path)
    end_time = perf_counter()
    duration = end_time - start_time
    logger.info("Validation complete in %.2fs. Repair attempted=%s success=%s classification=%s", duration, repair_attempted, repair_success, classification)

    try:
        metadata = FileMetadata(
            file_path=str(path.resolve()),
            file_type=file_ext.lstrip("."),
            classification=classification,
            size_bytes=size_bytes,
            sha256=sha256_hash,
            hash=sha256_hash,
            repair_attempted=repair_attempted,
            repair_success=repair_success,
            errors=errors,
            timestamps={"start": start_time, "end": end_time, "duration": duration},
            page_count=page_count,
            title=meta.get("title"),
            author=meta.get("author"),
            creation_date=meta.get("creation_date"),
            artifacts_path=artifacts_path,
            metrics={"elapsed_time": duration},
            file_size_bytes=size_bytes,
        )
    except ValidationError as exc:
        logger.error("Metadata validation error: %s", exc)
        if pipeline_json and file_id:
            log_error(pipeline_json, PHASE_NAME, file_id or "", str(exc), "Validation")
        return None

    _flag_duplicate_hash(pipeline_json, file_id or "", metadata)
    return metadata


def persist_and_log(metadata: FileMetadata, json_path: str, file_id: str) -> None:
    persisted = persist_metadata(metadata, Path(json_path), file_id)
    try:
        logger.info("Extracted metadata persisted: %s", json.dumps(persisted[PHASE_NAME]["files"][file_id], indent=2))
    except Exception:
        logger.info("Persisted metadata for %s", file_id)


def main():
    parser = argparse.ArgumentParser(description="Phase 1: Validate and repair audiobook files.")
    parser.add_argument("--file", required=True, help="Path to input file.")
    parser.add_argument("--max_size_mb", type=int, default=500, help="Max file size in MB.")
    parser.add_argument("--retries", type=int, default=2, help="Repair retries.")
    parser.add_argument("--json_path", default="pipeline.json", help="Pipeline JSON path.")
    parser.add_argument("--artifacts_dir", default="artifacts/phase1", help="Artifacts directory.")
    parser.add_argument("--force", action="store_true", help="Force revalidation even if hash matches prior run.")
    parser.add_argument(
        "--mode",
        choices=["thorough", "fast"],
        default="thorough",
        help="Fast mode skips repairs/classification; thorough runs full validation.",
    )
    args = parser.parse_args()

    metadata = validate_and_repair(
        args.file,
        args.max_size_mb,
        args.retries,
        args.artifacts_dir,
        force=args.force,
        mode=args.mode,
        pipeline_json=Path(args.json_path),
        file_id=Path(args.file).stem,
    )
    if metadata:
        file_id = Path(args.file).stem
        persist_and_log(metadata, args.json_path, file_id)
        serialized = metadata.model_dump_json(indent=2)
        logger.info("Success: %s", serialized)
    else:
        logger.error("Validation failed.")


if __name__ == "__main__":
    main()
