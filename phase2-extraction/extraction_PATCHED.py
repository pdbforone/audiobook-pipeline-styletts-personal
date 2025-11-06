import argparse
import logging
from pathlib import Path
import sys
import os
from time import perf_counter
from typing import Optional, Dict, List
import yaml
import pdfplumber
import pymupdf as fitz
from unstructured.partition.auto import partition
import easyocr
import nostril
import nltk
from langdetect import detect, DetectorFactory
from pydantic import BaseModel, ValidationError, Field
import json
import numpy as np

# Try to import pypdf for better font encoding support
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("pypdf not available - install with 'poetry add pypdf' for better font encoding")

# Fix relative imports for script mode
if __name__ == '__main__':
    sys.path.append(str(Path(__file__).parent))
from structure_detector import extract_structure, structure_to_dict

# Setup logging and NLTK
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
nltk.download("punkt", quiet=True)
DetectorFactory.seed = 0  # Consistent langdetect


class ExtractionConfig(BaseModel):
    json_path: str
    file_id: str
    extracted_dir: Optional[str] = "extracted_text"
    retry_limit: int = 1
    gibberish_threshold: float = 0.5
    perplexity_threshold: float = 0.92
    lang_confidence: float = 0.9
    extract_structure: bool = True


class ExtractionRecord(BaseModel):
    extracted_text_path: str
    tool_used: str
    yield_pct: float
    gibberish_score: float
    perplexity: float
    language: str
    lang_confidence: float
    status: str  # success, partial_success, failed
    errors: List[str] = Field(default_factory=list)
    timestamps: Dict[str, float]
    structure: Optional[List[Dict]] = None


def load_from_json(json_path: str, file_id: str, file_arg: str = None) -> Dict:
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        file_data = data.get("phase1", {}).get("files", {}).get(file_id, {})
        file_path = file_data.get("file_path") or file_data.get("artifacts_path")
        
        if file_arg:
            file_path = file_arg  # Prefer CLI --file if provided
        elif not file_path:
            file_path = os.environ.get("AUDIOBOOK_INPUT_PATH")
            if not file_path:
                raise ValueError(f"No file_path found for file_id '{file_id}' and AUDIOBOOK_INPUT_PATH not set")
            logger.warning(f"Using fallback path from environment: {file_path}")
        
        return {
            "file_path": file_path,
            "classification": file_data.get("classification", "text"),
        }
    except Exception as e:
        logger.error(f"JSON load failed: {e}")
        raise


def extract_text_pypdf(file_path: str) -> str:
    """
    Extract text using pypdf (PyPDF2 successor).
    Often better for PDFs with custom fonts due to superior font encoding/mapping.
    """
    if not PYPDF_AVAILABLE:
        return ""
    try:
        reader = PdfReader(file_path)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        extracted = "\n".join(text)
        if extracted.strip():
            logger.info(f"pypdf extracted {len(extracted)} characters")
        return extracted
    except Exception as e:
        logger.warning(f"pypdf failed: {e}")
        return ""


def extract_text_pdfplumber(file_path: str) -> str:
    try:
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")
        return ""


def extract_text_pymupdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        logger.warning(f"PyMuPDF failed: {e}")
        return ""


def extract_text_unstructured(file_path: str) -> str:
    try:
        elements = partition(filename=file_path, strategy="auto")
        return "\n".join(str(el) for el in elements)
    except Exception as e:
        logger.warning(f"Unstructured failed: {e}")
        return ""


def extract_text_easyocr(file_path: str) -> str:
    try:
        reader = easyocr.Reader(["en"])
        doc = fitz.open(file_path)
        text = ""
        for page_num, page in enumerate(doc):
            pix = page.get_pixmap()
            import io
            from PIL import Image
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            img_array = np.array(img)
            result = reader.readtext(img_array)
            text += "\n".join([res[1] for res in result]) + "\n"
        doc.close()
        return text
    except Exception as e:
        logger.error(f"EasyOCR failed: {e}")
        return ""


def evaluate_gibberish(text: str) -> float:
    try:
        return nostril.nonsense_score(text) if text.strip() else 1.0
    except:
        return 1.0


def evaluate_perplexity(text: str) -> float:
    sentences = nltk.sent_tokenize(text)
    if not sentences:
        return 0.0
    tokens = nltk.word_tokenize(text.lower())
    unique_tokens = set(tokens)
    return len(unique_tokens) / len(tokens) if tokens else 0.0


def detect_language(text: str) -> Dict:
    try:
        lang = detect(text)
        detector = DetectorFactory.create()
        detector.append(text)
        probs = detector.get_probabilities()
        confidence = probs[0].prob if probs else 0.0
        return {"language": lang, "confidence": confidence}
    except:
        return {"language": "unknown", "confidence": 0.0}


def main(config: ExtractionConfig, file_arg: str = None):
    start_time = perf_counter()
    phase1_data = load_from_json(config.json_path, config.file_id, file_arg)
    file_path = phase1_data["file_path"]
    classification = phase1_data["classification"]
    if not file_path or not Path(file_path).exists():
        logger.error("Invalid file path from Phase 1.")
        return

    Path(config.extracted_dir).mkdir(parents=True, exist_ok=True)
    text = ""
    tool_used = ""
    errors = []
    retries = 0

    while retries <= config.retry_limit:
        if classification == "text" or classification == "mixed":
            # Try pypdf FIRST - best for custom fonts and encoding
            logger.info("Attempting extraction with pypdf (best for font encoding)...")
            text = extract_text_pypdf(file_path)
            if text.strip():
                tool_used = "pypdf"
                logger.info(f"✓ pypdf succeeded: {len(text)} chars extracted")
            else:
                # Fallback to pdfplumber/pymupdf
                logger.info("pypdf failed or not available, trying pdfplumber/pymupdf...")
                text = extract_text_pdfplumber(file_path) or extract_text_pymupdf(file_path)
                tool_used = "pdfplumber or pymupdf"
            
            # If text extraction fails for mixed PDFs, try unstructured
            if not text.strip() and classification == "mixed":
                logger.info("Text extraction failed, trying unstructured...")
                text = extract_text_unstructured(file_path)
                tool_used = "unstructured"
                if text.strip():
                    errors.append("Fallback to unstructured")
            
            # Only use OCR as absolute last resort for mixed PDFs
            if not text.strip() and classification == "mixed":
                logger.warning("All text extraction failed, falling back to OCR...")
                text = extract_text_easyocr(file_path)
                tool_used = "easyocr"
                errors.append("Fallback to EasyOCR (last resort)")
        
        elif classification == "scanned":
            # For truly scanned PDFs, go straight to OCR
            text = extract_text_easyocr(file_path)
            tool_used = "easyocr"

        if text.strip():
            break
        retries += 1
        logger.warning(f"Retry {retries} due to empty text.")

    if not text.strip():
        status = "failed"
        yield_pct = 0.0
        gibberish_score = 1.0
        perplexity = 0.0
        lang_info = {"language": "unknown", "confidence": 0.0}
        extracted_path = ""
    else:
        gibberish_score = evaluate_gibberish(text)
        if gibberish_score < config.gibberish_threshold:
            errors.append(f"Gibberish score low: {gibberish_score}; potential retry")

        perplexity = evaluate_perplexity(text)
        lang_info = detect_language(text)
        if (
            lang_info["language"] != "en"
            or lang_info["confidence"] < config.lang_confidence
        ):
            errors.append(f"Language issue: {lang_info}")

        file_size = os.path.getsize(file_path)
        yield_pct = len(text) / file_size * 100 if file_size else 0.0
        status = (
            "success"
            if yield_pct > 98
            and perplexity > config.perplexity_threshold
            and not errors
            else "partial_success"
        )

        extracted_path = str(Path(config.extracted_dir) / f"{config.file_id}.txt")
        with open(extracted_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        logger.info(f"✓ Text written to: {extracted_path}")
        logger.info(f"  Yield: {yield_pct:.2f}%, Gibberish: {gibberish_score:.3f}, Perplexity: {perplexity:.3f}")
        logger.info(f"  Language: {lang_info['language']} (confidence: {lang_info['confidence']:.3f})")
        
        structure = None
        if config.extract_structure:
            try:
                logger.info("Extracting document structure...")
                structure_nodes = extract_structure(file_path, text)
                if structure_nodes:
                    structure = structure_to_dict(structure_nodes)
                    logger.info(f"Structure detected: {len(structure)} sections")
                else:
                    logger.info("No structure detected - will use fixed chunking")
            except Exception as e:
                logger.warning(f"Structure extraction failed (non-critical): {e}")
                structure = None

    end_time = perf_counter()
    duration = end_time - start_time
    logger.info(f"Extraction complete in {duration:.2f}s. Yield: {yield_pct:.2f}%")

    try:
        record = ExtractionRecord(
            extracted_text_path=extracted_path,
            tool_used=tool_used,
            yield_pct=yield_pct,
            gibberish_score=gibberish_score,
            perplexity=perplexity,
            language=lang_info["language"],
            lang_confidence=lang_info["confidence"],
            status=status,
            errors=errors,
            timestamps={"start": start_time, "end": end_time, "duration": duration},
            structure=structure,
        )
        merge_to_json(record, config.json_path, config.file_id)
    except ValidationError as e:
        logger.error(f"Record validation error: {e}")


def merge_to_json(record: ExtractionRecord, json_path: str, file_id: str):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    if "phase2" not in data:
        data["phase2"] = {"files": {}, "errors": [], "metrics": {}}

    data["phase2"]["files"][file_id] = record.model_dump()
    data["phase2"]["files"][file_id]["metrics"] = {
        "yield_pct": record.yield_pct,
        "duration": record.timestamps["duration"],
    }

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2: Text Extraction")
    parser.add_argument("--file_id", required=True, help="File ID from Phase 1")
    parser.add_argument("--file", type=str, help="Input file path (optional)")
    parser.add_argument("--json_path", default="pipeline.json", help="Pipeline JSON path")
    parser.add_argument("--extracted_dir", default="extracted_text", help="Output directory")
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    if args.config:
        with open(args.config, "r") as f:
            config_data = yaml.safe_load(f)
    else:
        config_data = {}

    config = ExtractionConfig(
        json_path=args.json_path,
        file_id=args.file_id,
        extracted_dir=args.extracted_dir,
        retry_limit=config_data.get("retry_limit", 1),
        gibberish_threshold=config_data.get("gibberish_threshold", 0.5),
        perplexity_threshold=config_data.get("perplexity_threshold", 0.92),
        lang_confidence=config_data.get("lang_confidence", 0.9),
    )
    main(config, file_arg=args.file)
