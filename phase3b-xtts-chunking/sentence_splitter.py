"""
Phase 3b: Simple Sentence Splitter for XTTS
Fast, lightweight chunking optimized for XTTS's 250-character limit
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Tuple
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# XTTS v2 limits (research-based)
MAX_CHARS_PER_CHUNK = 250  # Hard limit for XTTS
TARGET_CHARS = 200  # Preferred target (leaves room for punctuation)
MIN_CHARS = 50  # Minimum viable chunk


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex.
    Handles common abbreviations and edge cases.
    """
    # Common abbreviations that shouldn't trigger sentence breaks
    abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e|Ph\.D|M\.D|B\.A|M\.A)'

    # Replace abbreviations temporarily
    protected_text = re.sub(
        f'({abbreviations})\\.',
        lambda m: m.group(0).replace('.', '<DOT>'),
        text
    )

    # Split on sentence endings: . ! ? followed by space and capital letter
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(sentence_pattern, protected_text)

    # Restore abbreviations
    sentences = [s.replace('<DOT>', '.').strip() for s in sentences]

    return [s for s in sentences if s]


def chunk_sentences_for_xtts(sentences: List[str]) -> List[str]:
    """
    Group sentences into chunks optimized for XTTS (250 char max).

    Strategy:
    1. Try to group sentences to reach TARGET_CHARS (200)
    2. Never exceed MAX_CHARS_PER_CHUNK (250)
    3. Split long sentences if needed
    4. Preserve sentence boundaries when possible
    """
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If sentence alone exceeds max, split it at punctuation
        if len(sentence) > MAX_CHARS_PER_CHUNK:
            # Save current chunk if exists
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # Split long sentence at commas, semicolons, or clauses
            sub_chunks = split_long_sentence(sentence)
            chunks.extend(sub_chunks)
            continue

        # Try adding sentence to current chunk
        test_chunk = (current_chunk + " " + sentence).strip()

        if len(test_chunk) <= MAX_CHARS_PER_CHUNK:
            current_chunk = test_chunk

            # If we've reached a good target size, save chunk
            if len(current_chunk) >= TARGET_CHARS:
                chunks.append(current_chunk)
                current_chunk = ""
        else:
            # Current chunk is full, save it and start new chunk
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence

    # Don't forget last chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def split_long_sentence(sentence: str) -> List[str]:
    """
    Split a sentence longer than MAX_CHARS at natural break points.
    Tries: commas, semicolons, conjunctions, then hard splits.
    """
    if len(sentence) <= MAX_CHARS_PER_CHUNK:
        return [sentence]

    chunks = []

    # Try splitting at commas and semicolons
    parts = re.split(r'([,;])', sentence)
    current = ""

    for i, part in enumerate(parts):
        test = (current + part).strip()

        if len(test) <= MAX_CHARS_PER_CHUNK:
            current = test
        else:
            if current:
                chunks.append(current.strip())
            current = part.strip()

    if current:
        # If still too long, do hard split at word boundaries
        if len(current) > MAX_CHARS_PER_CHUNK:
            words = current.split()
            temp = ""
            for word in words:
                test = (temp + " " + word).strip()
                if len(test) <= MAX_CHARS_PER_CHUNK:
                    temp = test
                else:
                    if temp:
                        chunks.append(temp)
                    temp = word
            if temp:
                chunks.append(temp)
        else:
            chunks.append(current)

    return chunks


def process_text_file(
    text_path: Path,
    output_dir: Path,
    file_id: str
) -> Tuple[List[Path], dict]:
    """
    Process a text file into XTTS-optimized chunks.

    Args:
        text_path: Path to input text file
        output_dir: Directory for chunk outputs
        file_id: Identifier for this file

    Returns:
        Tuple of (chunk_paths, metadata)
    """
    logger.info(f"Processing {file_id}: {text_path}")

    # Read text
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Split into sentences
    sentences = split_into_sentences(text)
    logger.info(f"Found {len(sentences)} sentences")

    # Create chunks
    chunks = chunk_sentences_for_xtts(sentences)
    logger.info(f"Created {len(chunks)} chunks for XTTS")

    # Write chunks to files
    chunk_dir = output_dir / file_id
    chunk_dir.mkdir(parents=True, exist_ok=True)

    chunk_paths = []
    for i, chunk_text in enumerate(chunks, 1):
        chunk_file = chunk_dir / f"chunk_{i:04d}.txt"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(chunk_text)
        chunk_paths.append(chunk_file)

    # Calculate statistics
    char_lengths = [len(c) for c in chunks]
    metadata = {
        "total_chunks": len(chunks),
        "avg_chunk_chars": sum(char_lengths) / len(char_lengths) if chunks else 0,
        "max_chunk_chars": max(char_lengths) if chunks else 0,
        "min_chunk_chars": min(char_lengths) if chunks else 0,
    }

    logger.info(f"Chunk stats: avg={metadata['avg_chunk_chars']:.0f}, "
                f"max={metadata['max_chunk_chars']}, min={metadata['min_chunk_chars']}")

    return chunk_paths, metadata


def update_pipeline_json(
    pipeline_path: Path,
    file_id: str,
    chunk_paths: List[Path],
    metadata: dict,
    duration_sec: float
):
    """Update pipeline.json with Phase 3b results."""

    # Load existing pipeline data
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ensure phase3 section exists
    if "phase3" not in data:
        data["phase3"] = {"status": "partial", "files": {}}

    phase3 = data["phase3"]
    if "files" not in phase3:
        phase3["files"] = {}

    # Convert paths to strings relative to pipeline.json when possible
    chunk_path_strings = []
    for p in chunk_paths:
        try:
            chunk_path_strings.append(str(Path(p).relative_to(pipeline_path.parent)))
        except Exception:
            chunk_path_strings.append(str(p))

    # Add file entry
    phase3["files"][file_id] = {
        "chunk_paths": chunk_path_strings,
        "chunking_method": "xtts_sentence_split",
        "total_chunks": metadata["total_chunks"],
        "avg_chunk_chars": metadata["avg_chunk_chars"],
        "max_chunk_chars": metadata["max_chunk_chars"],
        "min_chunk_chars": metadata["min_chunk_chars"],
        "duration_seconds": duration_sec,
        "status": "success"
    }

    # Update overall status
    all_success = all(
        f.get("status") == "success"
        for f in phase3["files"].values()
    )
    phase3["status"] = "success" if all_success else "partial"

    # Write back
    with open(pipeline_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Updated pipeline.json for {file_id}")


def get_phase2_text_path(pipeline_path: Path, file_id: str) -> Path:
    """Get the text file path from Phase 2 data in pipeline.json."""
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    phase2 = data.get("phase2", {})
    files = phase2.get("files", {})

    # Try exact match first
    if file_id in files:
        text_path = files[file_id].get("extracted_text_path")
        if text_path:
            return Path(text_path)

    # Try fuzzy match
    for key, entry in files.items():
        if file_id in key or key in file_id:
            logger.info(f"Using Phase 2 file_id: '{key}' for '{file_id}'")
            text_path = entry.get("extracted_text_path")
            if text_path:
                return Path(text_path)

    # Fallback to default location
    default_path = Path("phase2-extraction") / "extracted_text" / f"{file_id}.txt"
    logger.warning(f"Text path not found in pipeline.json, using default: {default_path}")
    return default_path


def resolve_text_path(text_path: Path, pipeline_path: Path) -> Path:
    """Resolve a text path, trying common locations if missing."""
    base = pipeline_path.parent

    # Absolute or exists relative to cwd
    if text_path.is_absolute() and text_path.exists():
        return text_path
    if text_path.exists():
        return text_path

    # Try relative to pipeline.json directory
    candidate = base / text_path
    if candidate.exists():
        return candidate

    # Try phase2-extraction/extracted_text
    candidate = base / "phase2-extraction" / "extracted_text" / text_path.name
    if candidate.exists():
        return candidate

    return text_path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    """Main entry point for Phase 3b sentence splitting."""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 3b: XTTS Sentence Splitter")
    parser.add_argument("--file_id", required=True, help="File identifier")
    parser.add_argument("--json_path", required=True, help="Path to pipeline.json")
    parser.add_argument("--config", help="Path to config.yaml (unused, for compatibility)")
    parser.add_argument("--output_dir", default=str(PROJECT_ROOT / "phase3b_chunks"), help="Output directory")

    args = parser.parse_args()

    start_time = time.time()

    pipeline_path = Path(args.json_path)
    output_dir = Path(args.output_dir)

    # Get text file path from Phase 2 data
    text_path = resolve_text_path(get_phase2_text_path(pipeline_path, args.file_id), pipeline_path)

    if not text_path.exists():
        logger.error(f"Text file not found: {text_path}")
        logger.error(f"Make sure Phase 2 has completed successfully")
        return 1

    logger.info(f"Reading text from: {text_path}")

    # Process file
    chunk_paths, metadata = process_text_file(
        text_path,
        output_dir,
        args.file_id
    )

    duration = time.time() - start_time

    # Update pipeline
    update_pipeline_json(
        pipeline_path,
        args.file_id,
        chunk_paths,
        metadata,
        duration
    )

    logger.info(f"Phase 3b complete in {duration:.2f}s")
    logger.info(f"Created {len(chunk_paths)} chunks in {output_dir / args.file_id}")

    return 0


if __name__ == "__main__":
    exit(main())
