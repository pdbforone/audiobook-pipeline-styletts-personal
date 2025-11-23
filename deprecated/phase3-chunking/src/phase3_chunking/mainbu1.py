import argparse
import logging
import os
import yaml
import json
from time import perf_counter
from .models import ChunkRecord
from .utils import (
    clean_text,
    detect_sentences,
    form_semantic_chunks,
    assess_readability,
    save_chunks,
    log_chunk_times,
)

logger = logging.getLogger(__name__)  # For consistent logging


def process_chunking(
    text_path: str,
    chunks_dir: str,
    min_words: int,
    max_words: int,
    coherence_threshold: float,
    flesch_threshold: float,
) -> ChunkRecord:
    start_time = perf_counter()
    if not os.path.exists(text_path):
        logger.error("Text file not found")
        raise FileNotFoundError("Text file not found")

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()

    cleaned = clean_text(text)  # 3.1
    sentences = detect_sentences(cleaned)  # 3.2
    chunks, coherence, embeddings = form_semantic_chunks(
        sentences, min_words, max_words
    )  # Updated utils return

    readability = assess_readability(chunks)  # 3.4
    avg_coherence = sum(coherence) / len(coherence) if coherence else 0
    avg_flesch = sum(readability) / len(readability) if readability else 0
    status = (
        "success"
        if avg_coherence > coherence_threshold
        and avg_flesch > flesch_threshold
        else "partial"
    )
    errors = []
    if avg_coherence <= coherence_threshold:
        errors.append("Low coherence")
    if avg_flesch <= flesch_threshold:
        errors.append("Low readability")

    chunk_paths = save_chunks(text_path, chunks)  # 3.5
    logger.info(f"Created {len(chunk_paths)} chunks")

    log_chunk_times(chunks)  # 3.6

    end_time = perf_counter()
    duration = end_time - start_time

    return ChunkRecord(
        text_path=text_path,
        chunk_paths=chunk_paths,
        coherence_scores=coherence,
        readability_scores=readability,
        embeddings=[emb.tolist() for emb in embeddings],
        status=status,
        errors=errors,
        timestamps={
            "start": start_time,
            "end": end_time,
            "duration": duration,
        },
    )


def load_from_json(json_path: str, file_id: str) -> str:
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        text_path = (
            data.get("phase2", {})
            .get("files", {})
            .get(file_id, {})
            .get("extracted_text_path", "")
        )
        if not text_path:
            logger.warning(
                "No extracted_text_path in phase2; using absolute fallback."
            )
            text_path = f"C:\\Users\\myson\\Pipeline\\audiobook-pipeline\\phase2-extraction\\extracted_text\\{file_id}.txt"  # Absolute based on structure
        return text_path
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(
            f"{json_path} not found or invalid; creating empty and using absolute fallback."
        )
        with open(json_path, "w") as f:
            json.dump({}, f)
        return f"C:\\Users\\myson\\Pipeline\\audiobook-pipeline\\phase2-extraction\\extracted_text\\{file_id}.txt"  # Absolute fallback
    except Exception as e:
        logger.error(f"JSON load failed: {e}")
        return f"C:\\Users\\myson\\Pipeline\\audiobook-pipeline\\phase2-extraction\\extracted_text\\{file_id}.txt"  # Absolute fallback


def merge_to_json(record: ChunkRecord, json_path: str, file_id: str):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    if "phase3" not in data:
        data["phase3"] = {"files": {}, "errors": [], "metrics": {}}

    data["phase3"]["files"][file_id] = record.model_dump()
    data["phase3"]["files"][file_id]["metrics"] = {
        "num_chunks": len(record.chunk_paths),
        "avg_coherence": (
            sum(record.coherence_scores) / len(record.coherence_scores)
            if record.coherence_scores
            else 0
        ),
        "avg_flesch": (
            sum(record.readability_scores) / len(record.readability_scores)
            if record.readability_scores
            else 0
        ),
        "duration": record.timestamps["duration"],
    }

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Chunking")
    parser.add_argument(
        "--file_id", required=True, help="File ID from Phase 2"
    )
    parser.add_argument(
        "--json_path", default="pipeline.json", help="Pipeline JSON path"
    )
    parser.add_argument(
        "--chunks_dir", default="chunks", help="Chunks directory"
    )
    parser.add_argument("--config", help="Path to YAML config file")
    args = parser.parse_args()

    config_data = {}
    if args.config:
        try:
            with open(args.config, "r") as f:
                config_data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(
                f"Config file {args.config} not found; using defaults."
            )

    min_words = config_data.get("chunk_min_words", 250)
    max_words = config_data.get("chunk_max_words", 400)
    coherence_threshold = config_data.get("coherence_threshold", 0.87)
    flesch_threshold = config_data.get("flesch_threshold", 60)

    text_path = load_from_json(args.json_path, args.file_id)
    if not text_path:
        logger.error("No text path from Phase 2.")
        return

    try:
        record = process_chunking(
            text_path,
            args.chunks_dir,
            min_words,
            max_words,
            coherence_threshold,
            flesch_threshold,
        )
        merge_to_json(record, args.json_path, args.file_id)
    except Exception as e:
        logger.error(f"Error chunking {text_path}: {e}")


if __name__ == "__main__":
    main()
