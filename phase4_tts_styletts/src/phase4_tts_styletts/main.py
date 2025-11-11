"""
CLI entry point for the StyleTTS2-based Phase 4 replacement.

This mirrors the basic CLI surface from the legacy Chatterbox runner so
Phase 6 can call it without additional wiring.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Tuple

from .tts import BritishFormalNarrator, StyleControls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("phase4_styletts")


def load_chunk_paths(json_path: Path, file_id: str) -> Tuple[str, List[str]]:
    """Return the resolved Phase 3 entry and its chunk paths."""
    with json_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    phase3_files = (data.get("phase3") or {}).get("files", {})
    if not phase3_files:
        raise RuntimeError("Phase 3 output missing in pipeline.json")

    if file_id in phase3_files:
        return file_id, phase3_files[file_id].get("chunk_paths", [])

    for key, entry in phase3_files.items():
        if file_id in key or key in file_id:
            logger.info("Using fuzzy match '%s' for requested file_id '%s'", key, file_id)
            return key, entry.get("chunk_paths", [])

    raise RuntimeError(f"No Phase 3 entry found for '{file_id}'")


def select_chunks(chunk_paths: List[str], chunk_id: int | None) -> List[Path]:
    if chunk_id is None:
        return [Path(p) for p in chunk_paths]

    if chunk_id < 0 or chunk_id >= len(chunk_paths):
        raise IndexError(f"chunk_id {chunk_id} out of range (0-{len(chunk_paths) - 1})")
    return [Path(chunk_paths[chunk_id])]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 4 StyleTTS synthesizer")
    parser.add_argument("--file_id", required=True, help="Phase 3 file identifier")
    parser.add_argument("--json_path", default="../pipeline.json", help="Pipeline JSON path")
    parser.add_argument("--chunk_id", type=int, help="Optional chunk index to process")
    parser.add_argument("--reference", default="Voices/calm_narrator/reference.wav", help="Reference audio path")
    parser.add_argument("--output_dir", default="audio_chunks", help="Output directory for wav files")
    parser.add_argument("--voice_id", help="Voice override (logged for parity)")
    parser.add_argument(
        "--pipeline-mode",
        choices=["commercial", "personal"],
        default="commercial",
        help="Pipeline mode forwarded from orchestrator",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    json_path = Path(args.json_path).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        resolved_file_id, chunk_paths = load_chunk_paths(json_path, args.file_id)
    except Exception as exc:
        logger.error("Failed to load chunk metadata: %s", exc)
        return 1

    if not chunk_paths:
        logger.error("No chunk paths recorded for '%s'", resolved_file_id)
        return 1

    try:
        paths_to_process = select_chunks(chunk_paths, args.chunk_id)
    except Exception as exc:
        logger.error("Chunk selection failed: %s", exc)
        return 1

    narrator = BritishFormalNarrator(reference_audio=args.reference, controls=StyleControls())
    if args.voice_id:
        logger.info("Voice override requested (%s); StyleTTS2 uses fixed reference audio.", args.voice_id)

    overall_start = time.perf_counter()
    for idx, chunk_file in enumerate(paths_to_process, start=1):
        if not chunk_file.exists():
            logger.error("Chunk missing: %s", chunk_file)
            return 1

        text = chunk_file.read_text(encoding="utf-8").strip()
        if not text:
            logger.warning("Chunk %s is empty; skipping.", chunk_file.name)
            continue

        chunk_id = chunk_file.stem
        output_path = output_dir / f"{chunk_id}.wav"

        start = time.perf_counter()
        narrator.synth(text, output_path)
        duration = time.perf_counter() - start
        logger.info("Chunk %s (%d/%d) synthesized in %.2fs -> %s", chunk_id, idx, len(paths_to_process), duration, output_path)

    logger.info("StyleTTS2 synthesis finished in %.2fs", time.perf_counter() - overall_start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
