"""
Phase 3 Genre-Aware Chunker - Main Entry Point

Integrates:
- Genre detection (auto-classification)
- Profile-based chunking (5 genre profiles)
- Voice selection for TTS
- Enhanced metrics tracking
"""

import argparse
import logging
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Optional, Tuple

# Import existing modules
try:
    from .profiles import get_profile, list_profiles, get_profile_info
    from .detect import detect_genre
    from .main import run_phase3, load_pipeline_state
    from .models import Phase3Config
    from .utils import (
        detect_sentences,
        form_semantic_chunks,
    )
    from .models import ChunkRecord, ValidationConfig
except ImportError:
    from profiles import get_profile, list_profiles, get_profile_info
    from detect import detect_genre
    from main import run_phase3, load_pipeline_state
    from models import Phase3Config
    from utils import detect_sentences, form_semantic_chunks
    from models import ChunkRecord, ValidationConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_metadata_from_phase2(file_id: str, pipeline_path: Path) -> Dict:
    """
    Load metadata from Phase 2 for genre detection.

    Args:
        file_id: File ID to look up
        pipeline_path: Path to pipeline.json

    Returns:
        Metadata dictionary
    """
    try:
        with open(pipeline_path, "r") as f:
            data = json.load(f)

        phase2_files = data.get("phase2", {}).get("files", {})
        if file_id in phase2_files:
            metadata = phase2_files[file_id].get("metadata", {})
            logger.info(f"Loaded Phase 2 metadata for {file_id}")
            return metadata
        else:
            logger.warning(f"No Phase 2 metadata found for {file_id}")
            return {}

    except Exception as e:
        logger.warning(f"Could not load Phase 2 metadata: {e}")
        return {}


def chunk_with_profile(
    text: str, profile_name: str, metadata: Optional[Dict] = None
) -> Tuple[List[str], List[float], List, str, float]:
    """
    Chunk text using a specific genre profile.

    Args:
        text: Cleaned text to chunk
        profile_name: Genre profile to use
        metadata: Optional metadata for genre hints

    Returns:
        Tuple of (chunks, coherence_scores, embeddings, applied_profile, genre_confidence)
    """
    start_time = perf_counter()

    # Auto-detect genre if profile is 'auto'
    genre_confidence = 1.0
    if profile_name == "auto":
        detected_genre, confidence, all_scores = detect_genre(text, metadata)
        profile_name = detected_genre
        genre_confidence = confidence
        logger.info(
            f"Auto-detected genre: {profile_name} (confidence: {confidence:.2f})"
        )
        logger.debug(f"Genre scores: {all_scores}")

    # Get profile configuration
    profile = get_profile(profile_name)
    logger.info(f"Using profile: {profile.name}")
    logger.info(f"  Word range: {profile.min_words}-{profile.max_words}")
    logger.info(f"  Char range: {profile.min_chars}-{profile.max_chars}")
    logger.info(f"  Rules: {profile.rules}")

    # Detect sentences
    sentences = detect_sentences(text)
    if not sentences:
        raise ValueError("No sentences detected in text")

    logger.info(f"Detected {len(sentences)} sentences")

    # Form chunks using profile parameters
    soft_limit = max(profile.min_chars, int(profile.max_chars * 0.85))
    emergency_limit = max(
        profile.max_chars + 500, int(profile.max_chars * 1.3)
    )
    chunks, coherence, embeddings = form_semantic_chunks(
        sentences,
        min_chars=profile.min_chars,
        soft_limit=soft_limit,
        hard_limit=profile.max_chars,
        emergency_limit=emergency_limit,
        max_duration=25.0,
        emergency_duration=38.0,
    )

    if not chunks:
        raise ValueError("No chunks created from text")

    logger.info(f"Created {len(chunks)} chunks")

    elapsed = perf_counter() - start_time
    logger.info(
        f"Chunking with profile '{profile_name}' completed in {elapsed:.2f}s"
    )

    return chunks, coherence, embeddings, profile_name, genre_confidence


def process_genre_aware_chunking(
    text_path: str,
    chunks_dir: str,
    file_id: str,
    profile_name: str = "auto",
    pipeline_path: str = "pipeline.json",
    config: Optional[ValidationConfig] = None,
) -> ChunkRecord:
    """Delegate genre-aware processing to the unified Phase 3 runner."""
    cfg = config or Phase3Config()
    if not isinstance(cfg, Phase3Config):
        payload = (
            cfg.model_dump() if hasattr(cfg, "model_dump") else cfg.dict()
        )
        cfg = Phase3Config(**payload)
    cfg.json_path = pipeline_path
    cfg.chunks_dir = chunks_dir
    cfg.genre_profile = profile_name
    cfg.text_path_override = text_path

    pipeline = load_pipeline_state(pipeline_path)
    return run_phase3(file_id=file_id, pipeline=pipeline, config=cfg)


def main():
    """Main entry point for genre-aware chunking."""
    parser = argparse.ArgumentParser(
        description="Phase 3: Genre-Aware Semantic Chunking for TTS"
    )

    parser.add_argument(
        "--file_id", required=True, help="File ID from Phase 2"
    )
    parser.add_argument(
        "--text_path", required=True, help="Path to cleaned text file"
    )
    parser.add_argument(
        "--chunks_dir", default="chunks", help="Output directory for chunks"
    )
    parser.add_argument(
        "--profile",
        default="auto",
        choices=list_profiles(),
        help="Genre profile to use (default: auto-detect)",
    )
    parser.add_argument(
        "--pipeline_path",
        default="pipeline.json",
        help="Path to pipeline.json",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    try:
        logger.info("=" * 60)
        logger.info("PHASE 3: GENRE-AWARE CHUNKING")
        logger.info("=" * 60)
        logger.info(f"File ID: {args.file_id}")
        logger.info(f"Profile: {args.profile}")

        # Show profile info
        if args.profile != "auto":
            profile_info = get_profile_info(args.profile)
            logger.info(f"Profile details: {profile_info}")

        # Process chunking
        record = process_genre_aware_chunking(
            text_path=args.text_path,
            chunks_dir=args.chunks_dir,
            file_id=args.file_id,
            profile_name=args.profile,
            pipeline_path=args.pipeline_path,
        )

        # Print summary
        metrics = record.get_metrics()
        print("\n" + "=" * 60)
        print("PHASE 3 CHUNKING SUMMARY")
        print("=" * 60)
        print(f"File ID: {args.file_id}")
        print(f"Applied Profile: {getattr(record, 'applied_profile', 'N/A')}")
        print(
            f"Genre Confidence: {getattr(record, 'genre_confidence', 0):.2f}"
        )
        print(f"Selected Voice: {getattr(record, 'suggested_voice', 'N/A')}")
        print(f"Status: {record.status}")
        print(f"Chunks created: {metrics['num_chunks']}")
        print(f"Average coherence: {metrics['avg_coherence']:.4f}")
        print(f"Average Flesch score: {metrics['avg_flesch']:.2f}")
        print(
            f"Average chunk: {metrics.get('avg_char_length', 0):.0f} chars, "
            f"{metrics.get('avg_word_count', 0):.0f} words"
        )
        print(
            f"Average duration: {metrics.get('avg_chunk_duration', 0):.1f}s "
            f"(max: {metrics.get('max_chunk_duration', 0):.1f}s)"
        )
        print(f"Processing time: {metrics['duration']:.2f}s")

        if record.errors:
            print("\nWarnings/Errors:")
            for error in record.errors:
                print(f"  - {error}")

        print("=" * 60 + "\n")

        sys.exit(0 if record.status == "success" else 1)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
