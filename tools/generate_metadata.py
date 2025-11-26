"""
CLI to generate metadata for a completed run (opt-in, non-destructive).

Usage:
    python -m tools.generate_metadata --pipeline_json ../pipeline.json --book_id mybook

Outputs:
    .pipeline/metadata/<book_id>.json
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import sys
import os

# Ensure project root import path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metadata.metadata_pipeline import (  # noqa: E402
    Chapter,
    ProcessedBook,
    serialize_metadata,
)

logger = logging.getLogger(__name__)


def load_book_from_pipeline(pipeline_json: Path, book_id: str) -> ProcessedBook:
    """Best-effort book loader from pipeline.json; falls back to placeholders."""
    try:
        data = json.loads(pipeline_json.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    title = book_id
    text = ""
    chapters: List[Chapter] = []

    # Try to pull phase2 extraction text if present
    phase2 = (data.get("phase2") or {}).get("files", {})
    if book_id in phase2:
        meta = phase2[book_id]
        title = meta.get("title") or title
        text = meta.get("text") or text
        chapter_list = meta.get("chapters") or []
        for idx, ch in enumerate(chapter_list, start=1):
            chapters.append(
                Chapter(
                    chapter_id=str(ch.get("id") or f"chapter_{idx:03d}"),
                    title=ch.get("title") or f"Chapter {idx}",
                    text=ch.get("text") or "",
                )
            )

    if not chapters and text:
        # Fallback to a single chapter using full text
        chapters.append(Chapter(chapter_id="chapter_001", title=title, text=text))

    return ProcessedBook(book_id=book_id, title=title, text=text, chapters=chapters)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate metadata (opt-in, non-destructive).")
    parser.add_argument("--pipeline_json", type=Path, default=Path("../pipeline.json"), help="Path to pipeline.json")
    parser.add_argument("--book_id", required=True, help="Book identifier (matches pipeline.json file id)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".pipeline") / "metadata",
        help="Output directory (default: .pipeline/metadata)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    book = load_book_from_pipeline(args.pipeline_json, args.book_id)
    meta = serialize_metadata(book)

    args.output.mkdir(parents=True, exist_ok=True)
    out_path = args.output / f"{args.book_id}.json"
    out_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    logger.info("Metadata written to %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
