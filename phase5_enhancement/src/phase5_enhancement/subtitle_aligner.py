"""
Timestamp alignment and drift correction for subtitles.
Handles timestamp drift that accumulates in long audiobooks.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def detect_drift(segments: List[Dict], audio_duration: float) -> float:
    """
    Calculate timestamp drift between last subtitle and actual audio duration.

    Returns:
        Drift in seconds (positive = subtitles shorter than audio)
    """
    if not segments:
        return 0.0

    last_timestamp = segments[-1]['end']
    drift = audio_duration - last_timestamp

    return drift


def align_timestamps(segments: List[Dict], audio_duration: float) -> List[Dict]:
    """
    Stretch or compress timestamps to match actual audio duration.

    Uses linear scaling: new_time = old_time * (audio_duration / last_timestamp)
    """
    if not segments:
        return segments

    last_timestamp = segments[-1]['end']
    if last_timestamp == 0:
        logger.warning("Last timestamp is 0, cannot align")
        return segments

    scale_factor = audio_duration / last_timestamp
    logger.info(f"Scaling timestamps by {scale_factor:.6f}x")

    aligned_segments = []
    for seg in segments:
        aligned_seg = seg.copy()
        aligned_seg['start'] = seg['start'] * scale_factor
        aligned_seg['end'] = seg['end'] * scale_factor
        aligned_segments.append(aligned_seg)

    return aligned_segments


def validate_alignment(segments: List[Dict]) -> bool:
    """
    Validate that timestamps are monotonically increasing.

    Returns:
        True if valid, False if overlaps or gaps detected
    """
    for i in range(len(segments) - 1):
        current_end = segments[i]['end']
        next_start = segments[i + 1]['start']

        if current_end > next_start:
            logger.error(f"Overlap detected: segment {i} ends at {current_end:.2f}s "
                        f"but segment {i+1} starts at {next_start:.2f}s")
            return False

    return True
