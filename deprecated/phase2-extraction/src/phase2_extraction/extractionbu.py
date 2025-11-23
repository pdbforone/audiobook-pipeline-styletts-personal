import argparse
import logging
import os
from time import perf_counter
from pathlib import Path
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


class ExtractionRecord(BaseModel):
    extracted_text_path: str
    tool_used: str
    yield_pct: float
    gibberish_score: float
    perplexity: float
    language: str
    lang_confidence: float
    status: str  # repaired, partially_repaired, skipped
    errors: List[str] = Field(default_factory=list)
    timestamps: Dict[str, float]


def load_from_json(json_path: str, file_id: str) -> Dict:
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        file_data = data.get("phase1", {}).get("files", {}).get(file_id, {})
        return {
            "file_path": file_data.get("artifacts_path")
            or file_data.get(
                "original_path", ""
            ),  # Assume original_path added in Phase1
            "classification": file_data.get("classification", "text"),
        }
    except Exception as e:
        logger.error(f"JSON load failed: {e}")
        return {"file_path": "", "classification": "text"}


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
        elements = partition(filename=file_path, strategy="auto")  # CPU hybrid
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
            img_bytes = pix.tobytes("png")
            result = reader.readtext(np.frombuffer(img_bytes, np.uint8))
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


def main(config: ExtractionConfig):
    start_time = perf_counter()
    phase1_data = load_from_json(config.json_path, config.file_id)
    file_path = phase1_data["file_path"]
    classification = phase1_data["classification"]
    if not file_path:
        logger.error("No file path from Phase 1.")
        return

    Path(config.extracted_dir).mkdir(parents=True, exist_ok=True)
    text = ""
    tool_used = ""
    errors = []
    retries = 0

    while retries <= config.retry_limit:
        if classification == "text":
            text = extract_text_pdfplumber(file_path) or extract_text_pymupdf(
                file_path
            )
            tool_used = "pdfplumber or pymupdf"
        else:  # scanned/mixed
            text = extract_text_unstructured(file_path)
            tool_used = "unstructured"
            if not text.strip():
                text = extract_text_easyocr(file_path)
                tool_used = "easyocr"
                errors.append("Fallback to EasyOCR")

        if text.strip():
            break
        retries += 1
        logger.warning(f"Retry {retries} due to empty text.")

    if not text.strip():
        status = "failed"
    else:
        gibberish_score = evaluate_gibberish(text)
        if gibberish_score < config.gibberish_threshold:
            errors.append(
                f"Gibberish score low: {gibberish_score}; potential retry"
            )

        perplexity = evaluate_perplexity(text)
        lang_info = detect_language(text)
        if (
            lang_info["language"] != "en"
            or lang_info["confidence"] < config.lang_confidence
        ):
            errors.append(f"Language issue: {lang_info}")

        file_size = os.path.getsize(file_path)
        yield_pct = len(text) / file_size * 100 if file_size else 0.0
        status = "success" if yield_pct > 98 else "partial_success"

        extracted_path = str(
            Path(config.extracted_dir) / f"{config.file_id}.txt"
        )
        with open(extracted_path, "w", encoding="utf-8") as f:
            f.write(text)

        end_time = perf_counter()
        duration = end_time - start_time
        logger.info(
            f"Extraction complete in {duration:.2f}s. Yield: {yield_pct:.2f}%"
        )

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
                timestamps={
                    "start": start_time,
                    "end": end_time,
                    "duration": duration,
                },
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
    parser.add_argument(
        "--file_id", required=True, help="File ID from Phase 1"
    )
    parser.add_argument(
        "--json_path", default="pipeline.json", help="Pipeline JSON path"
    )
    parser.add_argument(
        "--extracted_dir", default="extracted_text", help="Output directory"
    )
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config_data = yaml.safe_load(open(args.config, "r")) if args.config else {}
    config = ExtractionConfig(
        json_path=args.json_path,
        file_id=args.file_id,
        extracted_dir=args.extracted_dir,
        **config_data,
    )
    main(config)
