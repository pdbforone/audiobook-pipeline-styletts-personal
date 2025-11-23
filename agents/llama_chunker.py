"""
Llama Chunker Agent - Semantic chunk boundary detection using local LLM.

This agent analyzes text to find optimal split points that:
- Preserve semantic coherence
- Respect natural speech pauses
- Stay within TTS engine limits
- Never break mid-sentence

Usage:
    from agents import LlamaChunker

    chunker = LlamaChunker()
    boundaries = chunker.find_boundaries(long_text, max_chars=1000)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .llama_base import LlamaAgent, DEFAULT_MODEL

logger = logging.getLogger(__name__)

CHUNKER_SYSTEM_PROMPT = """You are an expert text segmentation system for audiobook production.

Your task is to identify optimal break points in text that:
1. Preserve semantic coherence - keep related ideas together
2. Respect natural speech pauses - break at paragraph/sentence boundaries
3. Stay within specified character limits
4. NEVER break mid-sentence
5. Prefer breaks at paragraph boundaries over sentence boundaries
6. Keep dialogue exchanges together when possible

For each break point, provide:
- The character position
- A brief reason for the break

Output format: JSON with "boundaries" array of {"position": int, "reason": string}"""


@dataclass
class ChunkBoundary:
    """A recommended chunk boundary."""

    position: int  # Character position in text
    reason: str  # Why this is a good break point
    confidence: float = 1.0  # 0.0 to 1.0


class LlamaChunker:
    """
    LLM-powered semantic chunker for audiobook text.

    Uses local Llama to find semantically meaningful split points
    that preserve narrative flow and stay within TTS limits.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        agent: Optional[LlamaAgent] = None,
    ):
        self.agent = agent or LlamaAgent(model=model)

    def find_boundaries(
        self,
        text: str,
        max_chars: int = 1000,
        min_chars: int = 200,
        prefer_paragraphs: bool = True,
    ) -> List[ChunkBoundary]:
        """
        Find optimal chunk boundaries in text.

        Args:
            text: Full text to chunk
            max_chars: Maximum characters per chunk
            min_chars: Minimum characters per chunk
            prefer_paragraphs: Prefer paragraph over sentence breaks

        Returns:
            List of ChunkBoundary objects with positions and reasons
        """
        if len(text) <= max_chars:
            return []  # No splitting needed

        # For very long texts, process in segments
        if len(text) > 4000:
            return self._chunk_long_text(text, max_chars, min_chars)

        prompt = f"""Analyze this text and identify optimal break points for audiobook narration.

Text length: {len(text)} characters
Target chunk size: {min_chars}-{max_chars} characters
Preference: {"paragraph breaks" if prefer_paragraphs else "sentence breaks"}

TEXT:
{text}

Find break points that divide this into chunks of {min_chars}-{max_chars} characters each.
Return JSON: {{"boundaries": [{{"position": <char_index>, "reason": "<brief reason>"}}]}}"""

        response = self.agent.query_json(
            prompt,
            max_tokens=500,
            system_prompt=CHUNKER_SYSTEM_PROMPT,
        )

        if "error" in response:
            logger.warning(f"LLM chunking failed: {response.get('error')}")
            return self._fallback_boundaries(text, max_chars, min_chars)

        boundaries = []
        for item in response.get("boundaries", []):
            try:
                pos = int(item.get("position", 0))
                reason = str(item.get("reason", "LLM suggestion"))

                # Validate position
                if min_chars <= pos <= len(text) - min_chars:
                    boundaries.append(ChunkBoundary(
                        position=pos,
                        reason=reason,
                        confidence=0.9,
                    ))
            except (TypeError, ValueError):
                continue

        # If LLM didn't find enough boundaries, supplement with fallback
        if not boundaries:
            return self._fallback_boundaries(text, max_chars, min_chars)

        return sorted(boundaries, key=lambda b: b.position)

    def _chunk_long_text(
        self,
        text: str,
        max_chars: int,
        min_chars: int,
    ) -> List[ChunkBoundary]:
        """Process very long text in segments."""
        boundaries = []
        segment_size = 3000
        overlap = 500

        position = 0
        while position < len(text):
            segment_end = min(position + segment_size, len(text))
            segment = text[position:segment_end]

            # Find boundaries in this segment
            segment_boundaries = self.find_boundaries(
                segment, max_chars, min_chars
            )

            # Adjust positions to absolute
            for b in segment_boundaries:
                abs_pos = position + b.position
                if abs_pos not in [x.position for x in boundaries]:
                    boundaries.append(ChunkBoundary(
                        position=abs_pos,
                        reason=b.reason,
                        confidence=b.confidence,
                    ))

            position += segment_size - overlap

        return sorted(boundaries, key=lambda b: b.position)

    def _fallback_boundaries(
        self,
        text: str,
        max_chars: int,
        min_chars: int,
    ) -> List[ChunkBoundary]:
        """
        Fallback to heuristic-based chunking when LLM unavailable.

        Uses paragraph and sentence boundaries.
        """
        boundaries = []

        # Find all paragraph breaks
        para_breaks = [m.end() for m in re.finditer(r'\n\n+', text)]

        # Find all sentence breaks
        sent_breaks = [m.end() for m in re.finditer(r'[.!?]\s+', text)]

        # Combine and sort
        all_breaks = sorted(set(para_breaks + sent_breaks))

        # Select breaks that respect min/max constraints
        last_break = 0
        for pos in all_breaks:
            chunk_size = pos - last_break

            if chunk_size >= min_chars and chunk_size <= max_chars:
                # Good break point
                reason = "paragraph" if pos in para_breaks else "sentence"
                boundaries.append(ChunkBoundary(
                    position=pos,
                    reason=f"Heuristic: {reason} boundary",
                    confidence=0.7,
                ))
                last_break = pos

            elif chunk_size > max_chars:
                # Need to find a break before this
                # Look for the last valid break before max_chars
                valid_breaks = [b for b in all_breaks if last_break < b <= last_break + max_chars]
                if valid_breaks:
                    best = max(valid_breaks)
                    reason = "paragraph" if best in para_breaks else "sentence"
                    boundaries.append(ChunkBoundary(
                        position=best,
                        reason=f"Heuristic: {reason} boundary (forced)",
                        confidence=0.5,
                    ))
                    last_break = best

        return boundaries

    def split_text(
        self,
        text: str,
        max_chars: int = 1000,
        min_chars: int = 200,
    ) -> List[Tuple[str, ChunkBoundary]]:
        """
        Split text into chunks with their boundary info.

        Returns list of (chunk_text, boundary) tuples.
        """
        boundaries = self.find_boundaries(text, max_chars, min_chars)

        if not boundaries:
            # Return whole text as single chunk
            return [(text, ChunkBoundary(position=len(text), reason="complete"))]

        chunks = []
        start = 0

        for boundary in boundaries:
            chunk_text = text[start:boundary.position].strip()
            if chunk_text:
                chunks.append((chunk_text, boundary))
            start = boundary.position

        # Add final chunk
        final_text = text[start:].strip()
        if final_text:
            chunks.append((
                final_text,
                ChunkBoundary(position=len(text), reason="end of text"),
            ))

        return chunks

    def suggest_improvements(
        self,
        chunk_text: str,
        issues: List[str],
    ) -> Optional[str]:
        """
        Suggest improvements for a problematic chunk.

        Args:
            chunk_text: The chunk that has issues
            issues: List of problems (e.g., "too long", "ends mid-sentence")

        Returns:
            Suggested rewrite or None if no improvement possible
        """
        prompt = f"""This text chunk has issues for TTS synthesis:

Issues: {', '.join(issues)}

Text:
{chunk_text}

Suggest how to split or rewrite this for better TTS compatibility.
Keep ALL original meaning - no hallucinations or additions.
Output JSON: {{"suggestion": "...", "split_points": [int], "rewrite": "..." or null}}"""

        response = self.agent.query_json(prompt, max_tokens=500)

        if "error" in response:
            return None

        return response.get("rewrite") or response.get("suggestion")
