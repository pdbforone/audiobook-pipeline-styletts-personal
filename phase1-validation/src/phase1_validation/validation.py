import argparse
import hashlib
import logging
import os
from time import perf_counter
from pathlib import Path
from typing import Optional, List, Dict

import chardet
import ebooklib
import ftfy
import hachoir.metadata
import hachoir.parser
import pikepdf
import pymupdf as fitz  # PyMuPDF
from docx import Document
from pydantic import BaseModel, ValidationError, Field
import json
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FileMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None
    file_type: str
    classification: str  # 'text', 'scanned', 'mixed'
    hash: str
    repair_status: str
    duplicate: bool = False
    errors: List[str] = Field(default_factory=list)
    timestamps: Dict[str, float]
    artifacts_path: Optional[str] = None


def compute_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()


def extract_metadata(file_path: str) -> dict:
    file_ext = Path(file_path).suffix.lower()
    metadata_dict = {"title": None, "author": None, "creation_date": None}

    if file_ext == ".pdf":
        try:
            doc = fitz.open(file_path)
            pdf_meta = doc.metadata
            metadata_dict["title"] = pdf_meta.get("title")
            metadata_dict["author"] = pdf_meta.get("author")
            metadata_dict["creation_date"] = pdf_meta.get("creationDate")
            doc.close()
        except Exception as e:
            logger.warning(f"PyMuPDF metadata extraction failed: {e}")

    # Fallback or supplement with hachoir for all formats
    try:
        parser = hachoir.parser.createParser(file_path)
        if parser:
            h_meta = hachoir.metadata.extractMetadata(parser)
            if h_meta:
                if not metadata_dict["title"]:
                    metadata_dict["title"] = h_meta.get("title")
                if not metadata_dict["author"]:
                    metadata_dict["author"] = h_meta.get("author")
                if not metadata_dict["creation_date"]:
                    metadata_dict["creation_date"] = h_meta.get("creation_date")
    except Exception as e:
        logger.warning(f"Hachoir metadata extraction failed: {e}")

    # Normalize strings with ftfy if present
    for key in metadata_dict:
        if metadata_dict[key]:
            metadata_dict[key] = ftfy.fix_text(metadata_dict[key])

    return metadata_dict


def classify_pdf(file_path: str, threshold: float = 0.02) -> str:
    """Classify PDF as text, scanned, or mixed based on extractable text.
    
    Uses a more robust heuristic:
    - Checks if pages have extractable text (not just density)
    - Lower threshold (2%) to catch PDFs with heavy formatting
    - Considers a page "text" if it has ANY meaningful text (>100 chars)
    """
    doc = fitz.open(file_path)
    text_pages = 0
    total_pages = len(doc)
    
    for page in doc:
        text = page.get_text().strip()
        
        # Quick check: if page has > 100 characters of text, it's extractable
        if len(text) > 100:
            text_pages += 1
            continue
        
        # Fallback: check density for edge cases
        page_bytes = len(page.read_contents() or b"")
        if page_bytes > 0:
            density = len(text) / page_bytes
            if density > threshold:
                text_pages += 1
    
    doc.close()
    
    # Classification logic
    text_ratio = text_pages / total_pages if total_pages > 0 else 0
    
    if text_ratio > 0.9:  # 90%+ pages have text
        return "text"
    elif text_ratio < 0.1:  # <10% pages have text
        return "scanned"
    else:
        return "mixed"


def repair_pdf(file_path: str, retries: int = 2) -> bool:
    for attempt in range(retries):
        try:
            with pikepdf.open(file_path, allow_overwriting_input=True) as pdf:
                pdf.save(file_path)
            return True
        except Exception as e:
            logger.warning(f"Repair attempt {attempt+1} failed: {e}")
    return False


def repair_epub(file_path: str, retries: int = 2) -> bool:
    try:
        book = ebooklib.epub.read_epub(file_path)
        ebooklib.epub.write_epub(file_path, book)
        return True
    except Exception as e:
        logger.error(f"EPUB repair failed: {e}")
        return False


def repair_docx(file_path: str, retries: int = 2) -> bool:
    try:
        doc = Document(file_path)
        doc.save(file_path)
        return True
    except Exception as e:
        logger.error(f"DOCX repair failed: {e}")
        return False


def repair_txt(file_path: str, retries: int = 2) -> bool:
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        encoding = chardet.detect(raw)["encoding"] or "utf-8"
        text = ftfy.fix_text(raw.decode(encoding, errors="replace"))
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        return True
    except Exception as e:
        logger.error(f"TXT repair failed: {e}")
        return False


def validate_and_repair(
    file_path: str,
    max_size_mb: int = 500,
    retries: int = 2,
    artifacts_dir: str = "artifacts/phase1",
) -> Optional[FileMetadata]:
    start_time = perf_counter()
    path = Path(file_path)
    if not path.exists() or not os.access(file_path, os.R_OK):
        logger.error("File not accessible.")
        return None
    if path.stat().st_size > max_size_mb * 1024 * 1024:
        logger.error("File exceeds size limit.")
        return None

    file_ext = path.suffix.lower()
    repaired = False
    repair_status = "validated"  # Default if no repair needed
    try:
        if file_ext == ".pdf":
            classify_pdf(file_path)  # Test open
        elif file_ext == ".epub":
            ebooklib.epub.read_epub(file_path)
        elif file_ext == ".docx":
            Document(file_path)
        elif file_ext == ".txt":
            with open(file_path, "r") as f:
                f.read()
    except Exception:
        logger.info("File corrupted; attempting repair.")
        repair_func = {
            ".pdf": repair_pdf,
            ".epub": repair_epub,
            ".docx": repair_docx,
            ".txt": repair_txt,
        }.get(file_ext)
        if repair_func:
            repaired = repair_func(file_path, retries)
        if not repaired:
            logger.error("Repair failed after retries.")
            repair_status = "skipped"
            return None
        else:
            repair_status = "repaired"

    # If repaired, save artifact
    artifacts_path = None
    if repaired:
        artifacts_dir_path = Path(artifacts_dir)
        artifacts_dir_path.mkdir(parents=True, exist_ok=True)
        artifacts_path = str(artifacts_dir_path / path.name)
        shutil.copy(file_path, artifacts_path)

    classification = "text"  # Default; override for PDF
    if file_ext == ".pdf":
        classification = classify_pdf(file_path)

    metadata = extract_metadata(file_path)
    file_hash = compute_sha256(file_path)
    end_time = perf_counter()
    duration = end_time - start_time
    logger.info(f"Validation complete in {duration:.2f}s. Repaired: {repaired}")

    try:
        return FileMetadata(
            title=metadata.get("title"),
            author=metadata.get("author"),
            creation_date=metadata.get("creation_date"),
            file_type=file_ext[1:],
            classification=classification,
            hash=file_hash,
            repair_status=repair_status,
            timestamps={"start": start_time, "end": end_time, "duration": duration},
            artifacts_path=artifacts_path,
        )
    except ValidationError as e:
        logger.error(f"Metadata validation error: {e}")
        return None


def merge_to_json(
    metadata: FileMetadata, json_path: str = "pipeline.json", file_id: str = ""
):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    if "phase1" not in data:
        data["phase1"] = {"files": {}, "hashes": [], "errors": [], "metrics": {}}

    if metadata.hash in data["phase1"]["hashes"]:
        data["phase1"]["errors"].append(
            {
                "type": "IntegrityWarning",
                "message": f"Duplicate hash {metadata.hash} for {file_id}",
            }
        )
        metadata.duplicate = True
    else:
        data["phase1"]["hashes"].append(metadata.hash)

    if file_id not in data["phase1"]["files"]:
        data["phase1"]["files"][file_id] = {}

    data["phase1"]["files"][file_id].update(metadata.model_dump())

    # Add per-file metric (for aggregate later)
    data["phase1"]["files"][file_id]["metrics"] = {
        "elapsed_time": metadata.timestamps["duration"]
    }

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1: Validate and repair audiobook files."
    )
    parser.add_argument("--file", required=True, help="Path to input file.")
    parser.add_argument(
        "--max_size_mb", type=int, default=500, help="Max file size in MB."
    )
    parser.add_argument("--retries", type=int, default=2, help="Repair retries.")
    parser.add_argument(
        "--json_path", default="pipeline.json", help="Pipeline JSON path."
    )
    parser.add_argument(
        "--artifacts_dir", default="artifacts/phase1", help="Artifacts directory."
    )
    args = parser.parse_args()

    metadata = validate_and_repair(
        args.file, args.max_size_mb, args.retries, args.artifacts_dir
    )
    if metadata:
        file_id = Path(args.file).stem
        merge_to_json(metadata, args.json_path, file_id)
        logger.info(f"Success: {metadata.model_dump_json(indent=2)}")
    else:
        logger.error("Validation failed.")


if __name__ == "__main__":
    main()
