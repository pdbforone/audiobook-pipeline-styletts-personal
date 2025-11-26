"""
Metadata pipeline (opt-in) powered by LlamaMetadataGenerator.

This module is non-destructive and does not affect TTS behavior.
It can be called after a run to generate summaries, tags, and
YouTube-ready metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.llama_metadata import LlamaMetadataGenerator


@dataclass
class Chapter:
    """Minimal representation of a chapter for metadata generation."""

    chapter_id: str
    title: str
    text: str


@dataclass
class ProcessedBook:
    """Minimal representation of a processed book."""

    book_id: str
    title: str
    text: str
    chapters: List[Chapter]


@dataclass
class ChapterMeta:
    """Metadata output for a chapter."""

    chapter_id: str
    summary: str
    highlights: List[str]
    confidence: float
    notes: str


@dataclass
class BookMetadata:
    """Top-level metadata for a book."""

    book_id: str
    title: str
    short_summary: str
    long_summary: str
    confidence: float
    notes: str


def _metadata_agent() -> LlamaMetadataGenerator:
    return LlamaMetadataGenerator()


def generate_book_metadata(book: ProcessedBook) -> BookMetadata:
    """Generate book-level metadata (opt-in)."""
    agent = _metadata_agent()
    short = agent.generate_short_summary(book.text, max_words=50)
    long = agent.generate_long_summary(book.text, max_words=200)

    confidence = max(float(short.get("confidence", 0.0)), float(long.get("confidence", 0.0)))
    notes = "; ".join(filter(None, [short.get("notes"), long.get("notes")]))

    return BookMetadata(
        book_id=book.book_id,
        title=book.title,
        short_summary=short.get("summary", ""),
        long_summary=long.get("summary", ""),
        confidence=confidence,
        notes=notes,
    )


def generate_chapter_metadata(chapters: List[Chapter]) -> List[ChapterMeta]:
    """Generate per-chapter metadata."""
    agent = _metadata_agent()
    outputs: List[ChapterMeta] = []
    for chapter in chapters:
        meta = agent.generate_chapter_summary(chapter_title=chapter.title, text=chapter.text)
        outputs.append(
            ChapterMeta(
                chapter_id=chapter.chapter_id,
                summary=meta.get("summary", ""),
                highlights=meta.get("highlights", []) or [],
                confidence=float(meta.get("confidence", 0.0)),
                notes=meta.get("notes", ""),
            )
        )
    return outputs


def generate_youtube_package(book: ProcessedBook) -> Dict[str, Any]:
    """Generate a YouTube-ready metadata package."""
    agent = _metadata_agent()
    yt = agent.generate_youtube_metadata(
        title=book.title,
        description=book.text[:500],
        tags=[],
    )
    tags = agent.generate_tags(book.text, max_tags=12)
    package = {
        "title": yt.get("title", book.title),
        "description": yt.get("description", ""),
        "tags": yt.get("tags", []) or tags.get("tags", []),
        "notes": yt.get("notes", ""),
        "confidence": float(yt.get("confidence", 0.0)),
    }
    return package


def serialize_metadata(book: ProcessedBook) -> Dict[str, Any]:
    """Convenience to serialize full metadata for persistence."""
    book_meta = generate_book_metadata(book)
    chapter_meta = generate_chapter_metadata(book.chapters)
    youtube = generate_youtube_package(book)

    return {
        "book": asdict(book_meta),
        "chapters": [asdict(c) for c in chapter_meta],
        "youtube": youtube,
    }
