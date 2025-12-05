"""
Phase 2: Multi-Format Text Extraction and Normalization

Main entry point for text extraction with:
- Multi-format support (PDF, DOCX, EPUB, HTML, TXT, OCR)
- Intelligent format detection
- TTS normalization
- Quality validation
- Comprehensive metrics tracking

Usage:
    python -m phase2_extraction.ingest --file_id <id> --json_path pipeline.json
    python -m phase2_extraction.ingest --file_id <id> --file /path/to/file.pdf --force-ocr
"""

import argparse
import json
import logging
import sys
from itertools import chain
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

try:
    from pipeline_common import PipelineState, StateError
except ImportError:
    project_root = Path(__file__).resolve().parents[3]
    package_root = Path(__file__).resolve().parents[1]
    for _path in (project_root, package_root):
        if str(_path) not in sys.path:
            sys.path.insert(0, str(_path))
    from pipeline_common import PipelineState, StateError

# Extractors
from .extractors import docx, epub, html, ocr, txt

# Normalization and utilities
from .extraction import extract_text_multipass
from .normalize import normalize_text
from .structure_detector import (
    StructureNode,
    calculate_section_boundaries,
    detect_structure_heuristic,
    extract_pdf_structure_by_fonts,
    extract_pdf_toc,
)
from .utils import (
    calculate_yield,
    detect_format,
    format_duration,
    load_config,
    log_error,
    merge_phase_state,
    with_retry,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_file_metadata(
    json_path: Path, file_id: str, file_override: Optional[Path] = None
) -> Dict:
    """
    Load file metadata from pipeline.json.

    Args:
        json_path: Path to pipeline.json
        file_id: File identifier from Phase 1
        file_override: Optional path to override file location

    Returns:
        Dict with file_path and classification

    Raises:
        FileNotFoundError: If pipeline.json or file not found
        ValueError: If file_id not in pipeline.json
    """
    state = PipelineState(json_path, validate_on_read=False)
    try:
        data = state.read(validate=False)
    except FileNotFoundError:
        logger.error(f"Pipeline file not found: {json_path}")
        raise
    except StateError as exc:
        logger.error(f"Unable to read pipeline state: {exc}")
        raise RuntimeError("Failed to read pipeline.json") from exc

    # Get file data from Phase 1
    phase1_data = data.get("phase1", {})
    file_data = phase1_data.get("files", {}).get(file_id, {})

    if not file_data and not file_override:
        raise ValueError(
            f"File ID '{file_id}' not found in pipeline.json. "
            f"Run Phase 1 first or use --file to specify file path."
        )

    # Use override if provided
    if file_override:
        file_path = file_override
        logger.info(f"Using file override: {file_path}")
    else:
        file_path = Path(
            file_data.get("file_path") or file_data.get("artifacts_path", "")
        )

    # Get classification from Phase 1
    classification = file_data.get("classification", "unknown")

    if classification == "unknown":
        logger.warning(
            "No classification from Phase 1 - will detect format from extension. "
            "For optimal extraction, run Phase 1 validation first."
        )

    # Validate file exists
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    return {
        "file_path": file_path,
        "classification": classification,
        "file_size": file_path.stat().st_size,
    }


def _merge_structure_nodes(
    text: str, node_groups: List[List[StructureNode]]
) -> List[StructureNode]:
    """
    Combine structure detections and align missing offsets.
    """
    merged: Dict[Tuple[str, int], StructureNode] = {}
    lower_text = text.lower()

    for node in chain.from_iterable(node_groups):
        candidate = node.copy()
        if candidate.char_offset == 0 and candidate.title:
            idx = lower_text.find(candidate.title.lower())
            if idx != -1:
                candidate.char_offset = idx
                candidate.char_end = idx + len(candidate.title)

        key = (candidate.title.lower(), candidate.char_offset)
        if key not in merged:
            merged[key] = candidate

    merged_nodes = list(merged.values())
    merged_nodes.sort(key=lambda n: n.char_offset)
    return merged_nodes


def _safe_model_dump(node):
    """Compatibility wrapper for Pydantic v1/v2."""
    if hasattr(node, "model_dump"):  # Pydantic v2
        return node.model_dump()
    elif hasattr(node, "dict"):  # Pydantic v1
        return node.dict()
    else:
        raise TypeError(f"Cannot serialize StructureNode: {type(node)}")


def extract_text(
    file_path: Path,
    detected_format: str,
    force_ocr: bool = False,
    classification: str = "unknown",
) -> Tuple[str, Dict]:
    """
    Extract text using appropriate method based on format and classification.

    Args:
        file_path: Path to input file
        detected_format: Format from detection ('pdf', 'docx', etc.)
        force_ocr: Force OCR extraction for PDFs
        classification: Classification from Phase 1 ('text', 'scanned', 'mixed')

    Returns:
        (text, metadata) from extractor

    Strategy:
    1. For PDFs: Check classification and force_ocr flag
        - If 'scanned' or force_ocr → use OCR
        - Otherwise → use PDF extractor (multi-pass)
    2. For other formats: Use format-specific extractor

    Reason: Classification from Phase 1 tells us if PDF needs OCR.
    This prevents wasting time on text extraction for scanned PDFs.
    """
    logger.info("=" * 60)
    logger.info("EXTRACTION STAGE")
    logger.info(f"Format: {detected_format}")
    logger.info(f"Classification: {classification}")
    logger.info(f"Force OCR: {force_ocr}")
    logger.info("=" * 60)

    # PDF handling with OCR decision
    if detected_format == "pdf":
        if force_ocr or classification == "scanned":
            logger.info(
                "Using OCR path for PDF (forced or classified as scanned)"
            )
            return with_retry(lambda: ocr.extract(file_path))

        text, method_used, quality_score = extract_text_multipass(file_path)

        if classification == "mixed" and quality_score < 0.6:
            logger.warning(
                "Low quality from text extraction on mixed PDF - trying OCR fallback..."
            )
            return with_retry(lambda: ocr.extract(file_path))

        if not text.strip():
            logger.warning(
                "Text extraction returned empty result - trying OCR fallback..."
            )
            return with_retry(lambda: ocr.extract(file_path))

        metadata = {
            "title": file_path.stem,
            "tool_used": method_used,
            "quality_score": quality_score,
            "char_count": len(text),
        }
        return text, metadata

    # DOCX
    elif detected_format == "docx":
        return with_retry(lambda: docx.extract(file_path))

    # EPUB
    elif detected_format == "epub":
        return with_retry(lambda: epub.extract(file_path))

    # HTML
    elif detected_format == "html":
        return with_retry(lambda: html.extract(file_path))

    # TXT (default)
    else:
        return with_retry(lambda: txt.extract(file_path))


def main(
    file_id: str,
    json_path: Path = Path("pipeline.json"),
    extracted_dir: Path = Path("extracted_text"),
    file_override: Optional[Path] = None,
    force_ocr: bool = False,
    config_path: Optional[Path] = None,
) -> None:
    """
    Main Phase 2 extraction pipeline.

    Stages:
    1. Load file metadata from pipeline.json
    2. Detect file format
    3. Extract text using appropriate method
    4. Detect structure (PDF only) before normalization
    5. Normalize text for TTS
    6. Save artifacts and update pipeline.json with metrics
    """
    start_time = perf_counter()
    wall_start = datetime.utcnow().timestamp()
    settings = load_config(config_path)

    logger.info("=" * 60)
    logger.info("PHASE 2: TEXT EXTRACTION & NORMALIZATION")
    logger.info("=" * 60)
    logger.info(f"File ID: {file_id}")
    logger.info(f"Pipeline: {json_path}")
    logger.info(f"Output: {extracted_dir}")
    logger.info("=" * 60)

    try:
        merge_phase_state(
            json_path,
            "phase2",
            {
                "status": "running",
                "timestamps": {"start": wall_start},
                "errors": [],
            },
            operation="phase2_start",
        )
    except StateError as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to initialize Phase 2 in pipeline.json: {exc}")
        return

    try:
        # Stage 1: Load File Metadata
        logger.info("\nStage 1: Loading file metadata...")
        file_metadata = load_file_metadata(json_path, file_id, file_override)
        file_path = file_metadata["file_path"]
        classification = file_metadata["classification"]
        file_size = file_metadata["file_size"]

        logger.info(f"  File: {file_path}")
        logger.info(
            f"  Size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)"
        )
        logger.info(f"  Classification: {classification}")

        # Stage 2: Detect Format
        logger.info("\nStage 2: Detecting file format...")
        detected_format = detect_format(file_path)
        logger.info(f"  Detected format: {detected_format}")

        # Stage 3: Extract Text
        logger.info("\nStage 3: Extracting text...")
        text, extraction_metadata = extract_text(
            file_path, detected_format, force_ocr, classification
        )
        quality_score = extraction_metadata.get("quality_score", 0.0)

        if not text or len(text) < 50:
            error_msg = (
                f"Extraction failed or produced minimal text ({len(text)} chars). "
                f"If this is a scanned PDF, try --force-ocr"
            )
            logger.error(error_msg)
            log_error(json_path, "phase2", file_id, error_msg)

            failure_timestamps = {
                "start": wall_start,
                "end": datetime.utcnow().timestamp(),
                "duration": perf_counter() - start_time,
            }
            merge_phase_state(
                json_path,
                "phase2",
                {
                    "status": "failed",
                    "timestamps": failure_timestamps,
                    "errors": [error_msg],
                    "files": {
                        file_id: {
                            "status": "failed",
                            "errors": [error_msg],
                            "timestamps": failure_timestamps,
                            "artifacts": {},
                            "metrics": {},
                            "extraction_metadata": extraction_metadata,
                        }
                    },
                },
                operation="phase2_fail_min_text",
            )
            return

        logger.info(f"  ✓ Extracted {len(text):,} characters")
        logger.info(
            f"  Tool used: {extraction_metadata.get('tool_used', 'unknown')}"
        )
        logger.info(f"  Quality score: {quality_score:.2f}")

        # Stage 4: Structure detection for PDFs (pre-normalization)
        structure_payload: List[Dict[str, Any]] = []
        structure_path: Optional[Path] = None
        if detected_format == "pdf":
            logger.info("\nStage 4: Detecting document structure...")
            toc_nodes = extract_pdf_toc(str(file_path))
            font_nodes = extract_pdf_structure_by_fonts(str(file_path), text)
            heuristic_nodes = detect_structure_heuristic(text)
            merged_nodes = _merge_structure_nodes(
                text, [toc_nodes, font_nodes, heuristic_nodes]
            )
            bounded_nodes = (
                calculate_section_boundaries(merged_nodes, len(text))
                if merged_nodes
                else []
            )
            if bounded_nodes:
                structure_payload = [
                    _safe_model_dump(node) for node in bounded_nodes
                ]
                structure_path = (
                    extracted_dir / f"{file_id}_structure.json"
                ).resolve()
                extracted_dir.mkdir(parents=True, exist_ok=True)
                structure_path.write_text(
                    json.dumps(
                        structure_payload, indent=2, ensure_ascii=False
                    ),
                    encoding="utf-8",
                )
                logger.info(f"  ✓ Saved structure to {structure_path}")
            else:
                logger.info("  No structure detected.")

        # Stage 5: Normalize Text
        logger.info("\nStage 5: Normalizing text for TTS...")
        normalized_text, norm_metrics = normalize_text(
            text, file_id, extracted_dir, settings
        )

        logger.info(f"  ✓ Normalized to {len(normalized_text):,} characters")
        logger.info(f"  Text yield: {norm_metrics.get('text_yield', 0.0):.2%}")
        logger.info(
            f"  Changes applied: {len(norm_metrics.get('changes', []))}"
        )

        # Stage 6: Save Artifacts
        logger.info("\nStage 6: Saving artifacts...")
        extracted_dir.mkdir(parents=True, exist_ok=True)

        output_path = (extracted_dir / f"{file_id}.txt").resolve()
        output_path.write_text(normalized_text, encoding="utf-8")
        logger.info(f"  ✓ Saved: {output_path}")

        meta_path = (extracted_dir / f"{file_id}_meta.json").resolve()
        combined_metadata = {
            **extraction_metadata,
            **norm_metrics,
            "file_id": file_id,
            "source_file": str(file_path),
            "detected_format": detected_format,
            "classification": classification,
        }
        meta_path.write_text(
            json.dumps(combined_metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"  ✓ Saved: {meta_path}")

        # Stage 7: Calculate Final Metrics
        end_time = perf_counter()
        duration = end_time - start_time
        wall_end = datetime.utcnow().timestamp()

        yield_pct = calculate_yield(file_size, len(normalized_text))
        status: str
        if quality_score >= 0.8 and yield_pct >= 0.85:
            status = "success"
        elif quality_score >= 0.6 or yield_pct >= 0.6:
            status = "partial_success"
        else:
            status = "failed"

        file_timestamps = {
            "start": wall_start,
            "end": wall_end,
            "duration": duration,
        }
        file_metrics = {
            "yield_pct": yield_pct,
            "quality_score": quality_score,
            "word_count": len(normalized_text.split()),
            "char_count": len(normalized_text),
        }
        file_artifacts = {
            "text": str(output_path),
            "metadata": str(meta_path),
        }
        if structure_path:
            file_artifacts["structure"] = str(structure_path)

        file_entry: Dict[str, Any] = {
            "status": status,
            "timestamps": file_timestamps,
            "metrics": file_metrics,
            "artifacts": file_artifacts,
            "errors": [],
            "extracted_text_path": str(output_path),
            "metadata_path": str(meta_path),
            "detected_format": detected_format,
            "tool_used": extraction_metadata.get("tool_used", "unknown"),
            "language": norm_metrics.get("language", "unknown"),
            "lang_confidence": norm_metrics.get("language_confidence", 0.0),
            "structure": structure_payload if structure_payload else [],
        }
        if yield_pct is not None:
            file_entry["yield_pct"] = yield_pct
        if quality_score is not None:
            file_entry["quality_score"] = quality_score

        phase2_data = {
            "status": status,
            "timestamps": file_timestamps,
            "artifacts": dict(file_artifacts),
            "metrics": {
                "yield_pct": yield_pct,
                "quality_score": quality_score,
            },
            "errors": [],
            "files": {file_id: file_entry},
        }

        merge_phase_state(
            json_path, "phase2", phase2_data, operation="phase2_complete"
        )

        # Final Summary
        logger.info("=" * 60)
        logger.info("PHASE 2 COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Status: {status}")
        logger.info(f"Duration: {format_duration(duration)}")
        logger.info(f"Output: {output_path}")
        logger.info(f"Quality: {quality_score:.2f}")
        logger.info(f"Yield: {yield_pct:.2%}")
        logger.info("=" * 60)

        if status == "failed":
            logger.warning("⚠️  Extraction completed but quality is low")
            logger.warning("  Consider:")
            logger.warning("    - Using --force-ocr for scanned PDFs")
            logger.warning("    - Checking source file quality")
            logger.warning("    - Reviewing extraction metadata")

    except Exception as exc:
        logger.error(
            f"Phase 2 failed: {type(exc).__name__}: {exc}",
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )

        log_error(json_path, "phase2", file_id, f"{type(exc).__name__}: {exc}")

        failure_timestamps = {
            "start": wall_start,
            "end": datetime.utcnow().timestamp(),
            "duration": perf_counter() - start_time,
        }
        merge_phase_state(
            json_path,
            "phase2",
            {
                "status": "failed",
                "timestamps": failure_timestamps,
                "errors": [str(exc)],
                "files": {
                    file_id: {
                        "status": "failed",
                        "errors": [str(exc)],
                        "timestamps": failure_timestamps,
                        "artifacts": {},
                        "metrics": {},
                    }
                },
            },
            operation="phase2_unhandled_error",
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 2: Multi-Format Text Extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic extraction using Phase 1 classification
  python -m phase2_extraction.ingest --file_id test001

  # Override file path
  python -m phase2_extraction.ingest --file_id test001 --file /path/to/book.pdf

  # Force OCR for scanned PDF
  python -m phase2_extraction.ingest --file_id test001 --force-ocr

  # Custom output directory
  python -m phase2_extraction.ingest --file_id test001 --extracted_dir ./output
""",
    )

    parser.add_argument(
        "--file_id",
        required=True,
        help="File ID from Phase 1 (or unique identifier if using --file)",
    )
    parser.add_argument(
        "--json_path",
        type=Path,
        default=Path("pipeline.json"),
        help="Path to pipeline.json (default: pipeline.json)",
    )
    parser.add_argument(
        "--extracted_dir",
        type=Path,
        default=Path("extracted_text"),
        help="Output directory for extracted text (default: extracted_text)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Optional: Input file path (overrides path from pipeline.json)",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Force OCR extraction for PDFs (useful for scanned documents)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional: Path to config.yaml (defaults to package config)",
    )

    args = parser.parse_args()

    # Run extraction
    main(
        file_id=args.file_id,
        json_path=args.json_path,
        extracted_dir=args.extracted_dir,
        file_override=args.file,
        force_ocr=args.force_ocr,
        config_path=args.config,
    )
