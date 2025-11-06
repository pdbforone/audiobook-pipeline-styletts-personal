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
import os
from pathlib import Path
from time import perf_counter
from typing import Optional, Dict, Tuple
from datetime import datetime

# Extractors
from .extractors import pdf, docx, epub, html, txt, ocr

# Normalization and utilities
from .normalize import normalize_text
from .utils import (
    safe_update_json,
    with_retry,
    detect_format,
    calculate_yield,
    format_duration,
    log_error
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_file_metadata(json_path: Path, file_id: str, file_override: Optional[Path] = None) -> Dict:
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
    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Pipeline file not found: {json_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {json_path}: {e}")
        raise
    
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
        file_path = Path(file_data.get("file_path") or file_data.get("artifacts_path", ""))
    
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
        "file_size": file_path.stat().st_size
    }


def extract_text(
    file_path: Path,
    detected_format: str,
    force_ocr: bool = False,
    classification: str = "unknown"
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
    logger.info(f"EXTRACTION STAGE")
    logger.info(f"Format: {detected_format}")
    logger.info(f"Classification: {classification}")
    logger.info(f"Force OCR: {force_ocr}")
    logger.info("=" * 60)
    
    # PDF handling with OCR decision
    if detected_format == 'pdf':
        # Force OCR if requested
        if force_ocr:
            logger.info("OCR forced by --force-ocr flag")
            return with_retry(lambda: ocr.extract(file_path))
        
        # Use OCR for scanned PDFs
        if classification == 'scanned':
            logger.info("Using OCR for scanned PDF (based on Phase 1 classification)")
            return with_retry(lambda: ocr.extract(file_path))
        
        # For mixed PDFs, try text extraction first, OCR if quality is low
        if classification == 'mixed':
            logger.info("Mixed PDF detected - trying text extraction first")
            text, metadata = with_retry(lambda: pdf.extract(file_path))
            
            quality = metadata.get('quality_score', 0.0)
            if quality < 0.6:
                logger.warning(
                    f"Low quality ({quality:.2f}) from text extraction, "
                    f"trying OCR instead..."
                )
                return with_retry(lambda: ocr.extract(file_path))
            
            return text, metadata
        
        # Default: text-based PDF extraction
        return with_retry(lambda: pdf.extract(file_path))
    
    # DOCX
    elif detected_format == 'docx':
        return with_retry(lambda: docx.extract(file_path))
    
    # EPUB
    elif detected_format == 'epub':
        return with_retry(lambda: epub.extract(file_path))
    
    # HTML
    elif detected_format == 'html':
        return with_retry(lambda: html.extract(file_path))
    
    # TXT (default)
    else:
        return with_retry(lambda: txt.extract(file_path))


def main(
    file_id: str,
    json_path: Path = Path("pipeline.json"),
    extracted_dir: Path = Path("extracted_text"),
    file_override: Optional[Path] = None,
    force_ocr: bool = False
) -> None:
    """
    Main Phase 2 extraction pipeline.
    
    Stages:
    1. Load file metadata from pipeline.json
    2. Detect file format
    3. Extract text using appropriate method
    4. Normalize text for TTS
    5. Save artifacts
    6. Update pipeline.json with metrics
    
    Args:
        file_id: Unique file identifier
        json_path: Path to pipeline.json
        extracted_dir: Directory for output artifacts
        file_override: Optional file path override
        force_ocr: Force OCR extraction
    """
    start_time = perf_counter()
    
    logger.info("=" * 60)
    logger.info("PHASE 2: TEXT EXTRACTION & NORMALIZATION")
    logger.info("=" * 60)
    logger.info(f"File ID: {file_id}")
    logger.info(f"Pipeline: {json_path}")
    logger.info(f"Output: {extracted_dir}")
    logger.info("=" * 60)
    
    # Initialize Phase 2 entry in pipeline.json
    try:
        safe_update_json(json_path, 'phase2', {
            'status': 'in_progress',
            'timestamps': {
                'start': datetime.utcnow().isoformat() + 'Z'
            }
        })
    except Exception as e:
        logger.error(f"Failed to initialize Phase 2 in pipeline.json: {e}")
        return
    
    try:
        # Stage 1: Load File Metadata
        logger.info("\nStage 1: Loading file metadata...")
        file_metadata = load_file_metadata(json_path, file_id, file_override)
        file_path = file_metadata['file_path']
        classification = file_metadata['classification']
        file_size = file_metadata['file_size']
        
        logger.info(f"  File: {file_path}")
        logger.info(f"  Size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")
        logger.info(f"  Classification: {classification}")
        
        # Stage 2: Detect Format
        logger.info("\nStage 2: Detecting file format...")
        detected_format = detect_format(file_path)
        logger.info(f"  Detected format: {detected_format}")
        
        # Stage 3: Extract Text
        logger.info("\nStage 3: Extracting text...")
        text, extraction_metadata = extract_text(
            file_path,
            detected_format,
            force_ocr,
            classification
        )
        
        if not text or len(text) < 50:
            error_msg = (
                f"Extraction failed or produced minimal text ({len(text)} chars). "
                f"If this is a scanned PDF, try --force-ocr"
            )
            logger.error(error_msg)
            log_error(
                json_path,
                'phase2',
                'extraction_failed',
                error_msg,
                'blocking'
            )
            
            safe_update_json(json_path, 'phase2', {
                'status': 'failed',
                'files': {
                    file_id: {
                        'error': error_msg,
                        'extraction_metadata': extraction_metadata
                    }
                },
                'timestamps': {
                    'end': datetime.utcnow().isoformat() + 'Z',
                    'duration': perf_counter() - start_time
                }
            })
            return
        
        logger.info(f"  ✓ Extracted {len(text):,} characters")
        logger.info(f"  Tool used: {extraction_metadata.get('tool_used', 'unknown')}")
        logger.info(f"  Quality score: {extraction_metadata.get('quality_score', 0.0):.2f}")
        
        # Stage 4: Normalize Text
        logger.info("\nStage 4: Normalizing text for TTS...")
        normalized_text, norm_metrics = normalize_text(text, file_id, extracted_dir)
        
        logger.info(f"  ✓ Normalized to {len(normalized_text):,} characters")
        logger.info(f"  Text yield: {norm_metrics.get('text_yield', 0.0):.2%}")
        logger.info(f"  Changes applied: {len(norm_metrics.get('changes', []))}")
        
        # Stage 5: Save Artifacts
        logger.info("\nStage 5: Saving artifacts...")
        extracted_dir.mkdir(parents=True, exist_ok=True)
        
        # Save cleaned text
        output_path = extracted_dir / f"{file_id}.txt"
        with output_path.open('w', encoding='utf-8') as f:
            f.write(normalized_text)
        logger.info(f"  ✓ Saved: {output_path}")
        
        # Save metadata
        meta_path = extracted_dir / f"{file_id}_meta.json"
        combined_metadata = {
            **extraction_metadata,
            **norm_metrics,
            "file_id": file_id,
            "source_file": str(file_path),
            "detected_format": detected_format,
            "classification": classification
        }
        
        import json as json_lib
        with meta_path.open('w', encoding='utf-8') as f:
            json_lib.dump(combined_metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"  ✓ Saved: {meta_path}")
        
        # Stage 6: Calculate Final Metrics
        end_time = perf_counter()
        duration = end_time - start_time
        
        yield_pct = calculate_yield(file_size, len(normalized_text))
        
        # Determine overall status
        quality_score = extraction_metadata.get('quality_score', 0.0)
        if quality_score >= 0.8 and yield_pct >= 0.85:
            status = 'success'
        elif quality_score >= 0.6 or yield_pct >= 0.6:
            status = 'partial_success'
        else:
            status = 'failed'
        
        # Stage 7: Update Pipeline.json
        logger.info("\nStage 6: Updating pipeline.json...")
        
        phase2_data = {
            'status': status,
            'timestamps': {
                'start': datetime.fromtimestamp(start_time).isoformat() + 'Z',
                'end': datetime.utcnow().isoformat() + 'Z',
                'duration': duration
            },
            'metrics': {
                'text_yield': yield_pct,
                'quality_score': quality_score,
                'language': norm_metrics.get('language', 'unknown'),
                'language_confidence': norm_metrics.get('language_confidence', 0.0),
                'normalization_metrics': {
                    'removed_junk_lines': norm_metrics.get('removed_junk_lines', 0),
                    'converted_quotes': norm_metrics.get('converted_quotes', False),
                    'preserved_headings': norm_metrics.get('preserved_headings', 0),
                    'extracted_footnotes': norm_metrics.get('extracted_footnotes', 0),
                    'tts_ready': norm_metrics.get('tts_ready', False)
                }
            },
            'files': {
                file_id: {
                    'path': str(output_path),
                    'metadata_path': str(meta_path),
                    'detected_format': detected_format,
                    'word_count': len(normalized_text.split()),
                    'char_count': len(normalized_text),
                    'metadata': {
                        'title': extraction_metadata.get('title', file_path.stem),
                        'author': extraction_metadata.get('author', 'Unknown'),
                        'tool_used': extraction_metadata.get('tool_used', 'unknown')
                    }
                }
            }
        }
        
        safe_update_json(json_path, 'phase2', phase2_data)
        
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
        
        if status == 'failed':
            logger.warning("⚠️  Extraction completed but quality is low")
            logger.warning("  Consider:")
            logger.warning("    - Using --force-ocr for scanned PDFs")
            logger.warning("    - Checking source file quality")
            logger.warning("    - Reviewing extraction metadata")
        
    except Exception as e:
        logger.error(f"Phase 2 failed: {type(e).__name__}: {e}", exc_info=True)
        
        # Log error to pipeline.json
        log_error(
            json_path,
            'phase2',
            type(e).__name__,
            f"{type(e).__name__}: {str(e)}",
            'blocking'
        )
        
        # Update status
        safe_update_json(json_path, 'phase2', {
            'status': 'failed',
            'timestamps': {
                'end': datetime.utcnow().isoformat() + 'Z',
                'duration': perf_counter() - start_time
            }
        })
        
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
"""
    )
    
    parser.add_argument(
        '--file_id',
        required=True,
        help='File ID from Phase 1 (or unique identifier if using --file)'
    )
    parser.add_argument(
        '--json_path',
        type=Path,
        default=Path('pipeline.json'),
        help='Path to pipeline.json (default: pipeline.json)'
    )
    parser.add_argument(
        '--extracted_dir',
        type=Path,
        default=Path('extracted_text'),
        help='Output directory for extracted text (default: extracted_text)'
    )
    parser.add_argument(
        '--file',
        type=Path,
        help='Optional: Input file path (overrides path from pipeline.json)'
    )
    parser.add_argument(
        '--force-ocr',
        action='store_true',
        help='Force OCR extraction for PDFs (useful for scanned documents)'
    )
    
    args = parser.parse_args()
    
    # Run extraction
    main(
        file_id=args.file_id,
        json_path=args.json_path,
        extracted_dir=args.extracted_dir,
        file_override=args.file,
        force_ocr=args.force_ocr
    )
