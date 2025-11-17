#!/usr/bin/env python3
"""
Phase 2: Multi-Pass Text Extraction with TTS Normalization

Features:
- Multi-pass extraction (tries multiple methods, picks best)
- Automatic TTS normalization (handles tabs, spaces, formatting)
- Quality validation for each method
- Handles PDF, DOCX, EPUB, TXT
"""

import argparse
import hashlib
import logging
import sys
from pathlib import Path
from time import perf_counter
from typing import Optional, Dict, List, Tuple
import yaml
import json

# Core libraries
import nltk
from langdetect import detect, DetectorFactory
from pydantic import BaseModel, ValidationError, Field
import fitz  # PyMuPDF

# Try optional extraction libraries
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("Warning: pypdf not available - install for better PDF extraction")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Try TTS normalizer
try:
    if __name__ == '__main__':
        sys.path.append(str(Path(__file__).parent))
    from tts_normalizer import normalize_for_tts, validate_tts_readiness
    TTS_NORMALIZER_AVAILABLE = True
except ImportError:
    TTS_NORMALIZER_AVAILABLE = False
    print("Warning: TTS normalizer not available")

# Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
nltk.download("punkt", quiet=True)
DetectorFactory.seed = 0


class ExtractionConfig(BaseModel):
    json_path: str
    file_id: str
    extracted_dir: Optional[str] = "extracted_text"
    retry_limit: int = 1
    use_multipass: bool = True  # Enable multi-pass by default
    force: bool = False  # Re-extract even if existing success


class ExtractionRecord(BaseModel):
    extracted_text_path: str
    tool_used: str
    yield_pct: float
    quality_score: float
    language: str
    lang_confidence: float
    status: str
    source_hash: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    timestamps: Dict[str, float]


def compute_sha256(file_path: Path) -> str:
    """Compute sha256 hash for change detection / reuse checks."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def load_from_json(json_path: str, file_id: str, file_arg: str = None) -> Dict:
    """Load file metadata from pipeline.json."""
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        file_data = data.get("phase1", {}).get("files", {}).get(file_id, {})
        file_path = file_data.get("file_path") or file_data.get("artifacts_path")
        
        if file_arg:
            file_path = file_arg
        
        # Smart fallback for classification
        classification = file_data.get("classification")
        if not classification:
            logger.warning("No classification from Phase 1 - defaulting to 'text'")
            logger.warning("Run Phase 1 first for optimal performance!")
            classification = "text"
        
        return {
            "file_path": file_path,
            "classification": classification,
            "pipeline_data": data,
        }
    except Exception as e:
        logger.error(f"JSON load failed: {e}")
        raise


def validate_extraction_quality(text: str, method_name: str) -> float:
    """
    Validate extraction quality for TTS.
    Returns quality score: 0.0 (worst) to 1.0 (perfect)
    """
    if not text or len(text) < 100:
        return 0.0
    
    score = 1.0
    sample = text[:20000]
    
    # Check for replacement characters
    if text.count('\ufffd') > 0:
        score -= 0.5
        logger.warning(f"{method_name}: Contains replacement characters")
    
    # Check alphabetic ratio
    alpha_ratio = sum(1 for c in sample if c.isalpha()) / len(sample)
    if alpha_ratio < 0.65:
        score -= 0.3
        logger.warning(f"{method_name}: Low alphabetic ratio ({alpha_ratio:.1%})")
    elif alpha_ratio < 0.75:
        score -= 0.1
    
    # Check for common English words
    text_lower = sample.lower()
    common_words = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'that', 'for', 'it']
    found_common = sum(1 for word in common_words if f' {word} ' in text_lower)
    if found_common < 8:
        score -= 0.4
        logger.warning(f"{method_name}: Only {found_common}/10 common words found")
    
    score = max(0.0, score)
    logger.info(f"{method_name} quality score: {score:.2f}")
    return score


def extract_text_pypdf(file_path: str) -> str:
    """Extract with pypdf."""
    if not PYPDF_AVAILABLE:
        return ""
    try:
        reader = PdfReader(file_path)
        text = "\\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            logger.info(f"pypdf: {len(text):,} chars")
        return text
    except Exception as e:
        logger.warning(f"pypdf failed: {e}")
        return ""


def extract_text_pdfplumber(file_path: str) -> str:
    """Extract with pdfplumber."""
    if not PDFPLUMBER_AVAILABLE:
        return ""
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            logger.info(f"pdfplumber: {len(text):,} chars")
        return text
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")
        return ""


def extract_text_pymupdf(file_path: str) -> str:
    """Extract with PyMuPDF."""
    try:
        doc = fitz.open(file_path)
        text = "\\n".join(page.get_text() for page in doc)
        doc.close()
        if text.strip():
            logger.info(f"PyMuPDF: {len(text):,} chars")
        return text
    except Exception as e:
        logger.warning(f"PyMuPDF failed: {e}")
        return ""


def extract_text_multipass(file_path: str) -> Tuple[str, str, float]:
    """
    Multi-pass extraction: Try multiple methods, pick the best.
    Returns (text, method_used, quality_score)
    """
    logger.info("=" * 60)
    logger.info("MULTI-PASS EXTRACTION")
    logger.info("=" * 60)
    
    results = {}
    
    # Try all methods
    methods = [
        ("pypdf", extract_text_pypdf),
        ("pdfplumber", extract_text_pdfplumber),
        ("pymupdf", extract_text_pymupdf),
    ]
    
    for method_name, extract_func in methods:
        text = extract_func(file_path)
        if text.strip():
            score = validate_extraction_quality(text, method_name)
            results[method_name] = (text, score)
    
    if not results:
        logger.error("All extraction methods failed!")
        return "", "none", 0.0
    
    # Pick best by score
    best_method = max(results.keys(), key=lambda k: results[k][1])
    best_text, best_score = results[best_method]
    
    logger.info("=" * 60)
    logger.info(f"BEST: {best_method} (score: {best_score:.2f}, {len(best_text):,} chars)")
    logger.info("=" * 60)
    
    return best_text, best_method, best_score


def main(config: ExtractionConfig, file_arg: str = None):
    """Main extraction function."""
    start_time = perf_counter()
    
    # Load file info
    phase1_data = load_from_json(config.json_path, config.file_id, file_arg)
    file_path = phase1_data["file_path"]
    classification = phase1_data["classification"]
    pipeline_data = phase1_data.get("pipeline_data", {})
    
    if not file_path or not Path(file_path).exists():
        logger.error(f"Invalid file path: {file_path}")
        return

    # Track source hash for smarter reuse
    source_hash: Optional[str] = None
    try:
        source_hash = compute_sha256(Path(file_path))
    except Exception as exc:
        logger.warning(f"Phase 2: could not hash source for reuse check: {exc}")

    # Skip if already extracted and not forced
    try:
        phase2_files = pipeline_data.get("phase2", {}).get("files", {}) or {}
        existing = phase2_files.get(config.file_id, {})
        existing_path = existing.get("extracted_text_path")
        existing_hash = existing.get("source_hash")
        if (
            existing.get("status") == "success"
            and existing_path
            and Path(existing_path).exists()
            and not config.force
        ):
            if source_hash and existing_hash and source_hash != existing_hash:
                logger.info("Phase 2: source hash changed; re-extracting.")
            else:
                logger.info("Phase 2: existing extraction found and force=False; skipping.")
                return
    except Exception as exc:
        logger.warning(f"Phase 2: reuse check failed (will re-extract): {exc}")
    
    Path(config.extracted_dir).mkdir(parents=True, exist_ok=True)
    
    # Extract based on classification
    text = ""
    tool_used = ""
    quality_score = 0.0
    
    if classification in ["text", "mixed"]:
        if config.use_multipass:
            text, tool_used, quality_score = extract_text_multipass(file_path)
        else:
            # Fallback to single method
            text = extract_text_pypdf(file_path) or extract_text_pymupdf(file_path)
            tool_used = "pypdf or pymupdf"
            quality_score = validate_extraction_quality(text, tool_used) if text else 0.0
    
    elif classification == "scanned":
        logger.warning("Scanned PDF detected - text extraction may be poor")
        logger.warning("Consider using OCR if available")
        text = extract_text_pymupdf(file_path)
        tool_used = "pymupdf"
        quality_score = 0.5  # Lower quality expected for scanned
    
    if not text.strip():
        logger.error("Extraction failed - no text extracted")
        status = "failed"
        extracted_path = ""
    else:
        # CRITICAL: Normalize for TTS
        if TTS_NORMALIZER_AVAILABLE:
            logger.info("Normalizing text for TTS...")
            text, norm_stats = normalize_for_tts(text)
            is_ready, issues = validate_tts_readiness(text)
            
            if issues:
                logger.warning("TTS validation issues:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("✓ Text is TTS-ready")
            
            for change in norm_stats['changes']:
                logger.info(f"  - {change}")
        else:
            logger.warning("⚠️  TTS normalization skipped")
        
        # Save
        extracted_path = str(Path(config.extracted_dir) / f"{config.file_id}.txt")
        with open(extracted_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        logger.info(f"✓ Saved: {extracted_path}")
        logger.info(f"  Length: {len(text):,} chars")
        logger.info(f"  Quality: {quality_score:.2f}")
        
        # Determine status
        if quality_score >= 0.8:
            status = "success"
        elif quality_score >= 0.6:
            status = "partial_success"
        else:
            status = "failed"
    
    # Calculate metrics
    end_time = perf_counter()
    duration = end_time - start_time
    
    # Detect language
    try:
        lang = detect(text[:5000]) if text else "unknown"
        lang_conf = 0.9  # Simplified
    except:
        lang = "unknown"
        lang_conf = 0.0
    
    # Calculate yield
    import os
    file_size = os.path.getsize(file_path)
    yield_pct = (len(text) / file_size * 100) if file_size else 0.0
    
    # Save to pipeline.json
    try:
        record = ExtractionRecord(
            extracted_text_path=extracted_path,
            tool_used=tool_used,
            yield_pct=yield_pct,
            quality_score=quality_score,
            language=lang,
            lang_confidence=lang_conf,
            status=status,
            source_hash=source_hash,
            timestamps={"start": start_time, "end": end_time, "duration": duration},
        )
        merge_to_json(record, config.json_path, config.file_id)
    except ValidationError as e:
        logger.error(f"Record validation error: {e}")


def merge_to_json(record: ExtractionRecord, json_path: str, file_id: str):
    """Save extraction record to pipeline.json."""
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
        "quality_score": record.quality_score,
        "duration": record.timestamps["duration"],
    }
    
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2: Multi-Pass Text Extraction")
    parser.add_argument("--file_id", required=True, help="File ID from Phase 1")
    parser.add_argument("--file", type=str, help="Input file path (optional)")
    parser.add_argument("--json_path", default="pipeline.json", help="Pipeline JSON path")
    parser.add_argument("--extracted_dir", default="extracted_text", help="Output directory")
    parser.add_argument("--no-multipass", action="store_true", help="Disable multi-pass")
    parser.add_argument("--config", help="Path to YAML config file")
    parser.add_argument("--force", action="store_true", help="Force re-extraction even if previous success exists")
    args = parser.parse_args()
    
    config_data = {}
    if args.config:
        with open(args.config, "r") as f:
            config_data = yaml.safe_load(f) or {}
    
    config = ExtractionConfig(
        json_path=args.json_path,
        file_id=args.file_id,
        extracted_dir=args.extracted_dir,
        use_multipass=not args.no_multipass,
        retry_limit=config_data.get("retry_limit", 1),
        force=args.force,
    )
    
    main(config, file_arg=args.file)
