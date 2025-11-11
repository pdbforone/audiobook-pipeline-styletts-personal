"""
CLI entry point for the Kokoro-based Phase 4 replacement.

This mirrors the basic CLI surface from the legacy Chatterbox runner so
Phase 6 can call it without additional wiring.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .tts import VOICE_ALIASES, BritishFormalNarrator, StyleControls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("phase4_styletts")


WHITESPACE_RE = re.compile(r"\s+")
NO_SPACE_BEFORE = re.compile(r"\s+([,.;:!?])")
LETTER_RUN_RE = re.compile(r"\b(?:[A-Za-z](?: [A-Za-z]){1,})\b")
PARA_BREAK_RE = re.compile(r"(?:\n\s*){2,}")


def normalize_chunk_text(raw: str) -> str:
    """
    Collapse PDF artifacts (letter-by-letter spacing, stray line breaks, soft hyphens)
    so Kokoro receives natural prose instead of staccato fragments.
    """
    if not raw:
        return ""

    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = PARA_BREAK_RE.sub(". ", text)
    text = re.sub(r"(?<=\w)-\s*\n\s*", "", text)  # undo hyphenation inside words
    text = text.replace("\n", " ")
    text = re.sub(r"\.\s+\.", ". ", text)

    def collapse_letters(match: re.Match[str]) -> str:
        return match.group(0).replace(" ", "")

    text = LETTER_RUN_RE.sub(collapse_letters, text)
    text = WHITESPACE_RE.sub(" ", text).strip()

    tokens = text.split(" ")
    rebuilt: List[str] = []
    buffer: List[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        if not buffer:
            return
        if len(buffer) == 1:
            rebuilt.append(buffer[0])
        else:
            rebuilt.append("".join(buffer))
        buffer = []

    for token in tokens:
        if not token:
            continue
        if len(token) == 1 and token.isalpha():
            buffer.append(token)
            continue
        flush_buffer()
        rebuilt.append(token)
    flush_buffer()

    collapsed = " ".join(rebuilt)
    collapsed = NO_SPACE_BEFORE.sub(r"\1", collapsed)
    collapsed = re.sub(r"\(\s+", "(", collapsed)
    collapsed = re.sub(r"\s+\)", ")", collapsed)
    collapsed = collapsed.strip()

    if collapsed:
        if collapsed[-1] in {"\"", "'"}:
            if len(collapsed) >= 2 and collapsed[-2] not in ".?!":
                collapsed = f"{collapsed[:-1]}.{collapsed[-1]}"
        elif collapsed[-1] not in ".?!":
            collapsed = f"{collapsed}."

    return collapsed


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
    parser = argparse.ArgumentParser(description="Phase 4 Kokoro synthesizer")
    parser.add_argument("--file_id", required=True, help="Phase 3 file identifier")
    parser.add_argument("--json_path", default="../pipeline.json", help="Pipeline JSON path")
    parser.add_argument("--chunk_id", type=int, help="Optional chunk index to process")
    parser.add_argument("--reference", default="", help="Reference audio path (ignored for Kokoro)")
    parser.add_argument("--output_dir", default="audio_chunks", help="Output directory for wav files")
    parser.add_argument("--voice_id", help="Voice override (af_sky, am_adam, etc.)")
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

    voice_id = resolve_voice(args.voice_id)
    narrator = BritishFormalNarrator(
        reference_audio=args.reference or None,
        controls=StyleControls(),
        voice_id=voice_id,
    )
    if args.voice_id:
        logger.info("Voice override requested -> %s", voice_id)

    overall_start = time.perf_counter()
    produced_files: List[Dict[str, object]] = []

    for idx, chunk_file in enumerate(paths_to_process, start=1):
        if not chunk_file.exists():
            logger.error("Chunk missing: %s", chunk_file)
            return 1

        text = normalize_chunk_text(chunk_file.read_text(encoding="utf-8"))
        if not text:
            logger.warning("Chunk %s is empty; skipping.", chunk_file.name)
            continue

        chunk_id = chunk_file.stem
        output_path = output_dir / f"{chunk_id}.wav"

        start = time.perf_counter()
        narrator.synth(text, output_path)
        digest = sha256_file(output_path)
        produced_files.append(
            {
                "path": str(output_path),
                "sha256": digest,
                "bytes": output_path.stat().st_size,
            }
        )
        duration = time.perf_counter() - start
        logger.info(
            "Chunk %s (%d/%d) synthesized in %.2fs -> %s",
            chunk_id,
            idx,
            len(paths_to_process),
            duration,
            output_path,
        )

    total_duration = time.perf_counter() - overall_start
    logger.info("Kokoro synthesis finished in %.2fs", total_duration)
    write_metadata(output_dir, voice_id, produced_files, total_duration)
    return 0


def resolve_voice(requested: Optional[str]) -> str:
    if not requested:
        return VOICE_ALIASES.get("female_default", VOICE_ALIASES.get("af_sky", "af_sky"))

    key = requested.lower()
    if key in VOICE_ALIASES:
        return VOICE_ALIASES[key]

    logger.warning("Unknown voice_id '%s' - using Kokoro default.", requested)
    return VOICE_ALIASES.get("af_sky", "af_sky")


def write_metadata(output_dir: Path, voice_id: str, files: List[Dict[str, object]], runtime_sec: float) -> None:
    meta = {
        "voice": voice_id,
        "chunk_count": len(files),
        "files": files,
        "sample_rate_hz": 24000,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": runtime_sec,
    }
    meta_path = output_dir / "kokoro_run_meta.json"
    with meta_path.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    logger.info("Wrote Kokoro run metadata to %s", meta_path)


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


if __name__ == "__main__":
    sys.exit(main())
