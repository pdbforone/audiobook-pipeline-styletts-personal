"""
Subtitle quality validation: WER calculation, coverage checks, and formatting.
"""

import logging
from typing import List, Dict
from jiwer import wer as calculate_jiwer_wer

logger = logging.getLogger(__name__)


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate between reference text and transcription.

    WER = (Substitutions + Deletions + Insertions) / Total Words
    Lower is better (0.0 = perfect match)
    """
    # Normalize text
    reference = reference.lower().strip()
    hypothesis = hypothesis.lower().strip()

    # Handle empty strings
    if not reference:
        return 1.0 if hypothesis else 0.0

    try:
        error_rate = calculate_jiwer_wer(reference, hypothesis)
        return error_rate
    except Exception as e:
        logger.error(f"WER calculation failed: {e}")
        return 1.0


def validate_coverage(coverage: float, min_coverage: float) -> bool:
    """
    Check if subtitle coverage meets minimum threshold.

    Args:
        coverage: Actual coverage (0.0 to 1.0)
        min_coverage: Minimum required (0.0 to 1.0)

    Returns:
        True if coverage is acceptable
    """
    return coverage >= min_coverage


def format_srt(segments: List[Dict]) -> str:
    """
    Format segments as SRT subtitle file.

    SRT Format:
    1
    00:00:00,000 --> 00:00:05,000
    First subtitle text

    2
    00:00:05,500 --> 00:00:10,000
    Second subtitle text
    """
    lines = []

    for i, seg in enumerate(segments, start=1):
        start_time = _format_timestamp_srt(seg['start'])
        end_time = _format_timestamp_srt(seg['end'])

        lines.append(f"{i}")
        lines.append(f"{start_time} --> {end_time}")
        lines.append(seg['text'])
        lines.append("")  # Blank line between subtitles

    return "\n".join(lines)


def format_vtt(segments: List[Dict]) -> str:
    """
    Format segments as WebVTT subtitle file.

    VTT Format:
    WEBVTT

    00:00:00.000 --> 00:00:05.000
    First subtitle text

    00:00:05.500 --> 00:00:10.000
    Second subtitle text
    """
    lines = ["WEBVTT", ""]

    for seg in segments:
        start_time = _format_timestamp_vtt(seg['start'])
        end_time = _format_timestamp_vtt(seg['end'])

        lines.append(f"{start_time} --> {end_time}")
        lines.append(seg['text'])
        lines.append("")  # Blank line between subtitles

    return "\n".join(lines)


def _format_timestamp_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    """Format seconds as VTT timestamp: HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
