"""
Surgical Phrase Remover - Word-Level Precision
Removes ONLY the target phrase, preserving all surrounding content.
"""

import logging
from pathlib import Path
from faster_whisper import WhisperModel
from pydub import AudioSegment
import time
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

TARGET_PHRASE_WORDS = [
    "you",
    "need",
    "to",
    "add",
    "some",
    "text",
    "for",
    "me",
    "to",
    "talk",
]


def find_phrase_in_words(words: List[dict]) -> List[Tuple[int, int]]:
    """
    Find target phrase in word list and return (start_idx, end_idx) tuples.

    Args:
        words: List of word dicts with 'word' and timing info

    Returns:
        List of (start_word_idx, end_word_idx) tuples for matches
    """
    matches = []
    phrase_len = len(TARGET_PHRASE_WORDS)

    i = 0
    while i <= len(words) - phrase_len:
        # Check if next N words match the target phrase
        window = [
            w["word"].lower().strip(".,!?;:")
            for w in words[i : i + phrase_len]
        ]

        if window == TARGET_PHRASE_WORDS:
            matches.append((i, i + phrase_len - 1))
            logger.info(
                f"  Found phrase at word index {i} ({words[i]['start']:.1f}s)"
            )
            i += phrase_len  # Skip past this match
        else:
            i += 1

    return matches


def surgical_remove_phrases(input_mp3: Path, output_mp3: Path):
    """Remove target phrases with word-level precision."""

    logger.info(f"Loading audio: {input_mp3}")
    audio = AudioSegment.from_mp3(str(input_mp3))

    logger.info("Transcribing with Whisper (word-level timestamps)...")
    logger.info("⏱️  This will take ~15-25 minutes for full precision...")

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(input_mp3),
        beam_size=5,
        word_timestamps=True,  # ← CRITICAL: Word-level precision
        language="en",
    )

    # Extract all words with timestamps
    logger.info("Extracting word-level timestamps...")
    all_words = []
    for segment in segments:
        if hasattr(segment, "words") and segment.words:
            for word in segment.words:
                all_words.append(
                    {"word": word.word, "start": word.start, "end": word.end}
                )

    logger.info(f"Total words transcribed: {len(all_words)}")

    # Find phrase matches
    logger.info("Scanning for target phrase...")
    matches = find_phrase_in_words(all_words)

    if not matches:
        logger.warning("No phrases found!")
        logger.info("Copying original to output (no changes needed)")
        audio.export(str(output_mp3), format="mp3", bitrate="192k")
        return

    logger.info(f"Found {len(matches)} instances of the phrase")

    # Convert word indices to time ranges (with small padding)
    PADDING_MS = 50  # Small padding to ensure clean cuts
    time_ranges_to_remove = []

    for start_idx, end_idx in matches:
        start_time_ms = int(all_words[start_idx]["start"] * 1000) - PADDING_MS
        end_time_ms = int(all_words[end_idx]["end"] * 1000) + PADDING_MS

        # Clamp to audio bounds
        start_time_ms = max(0, start_time_ms)
        end_time_ms = min(len(audio), end_time_ms)

        time_ranges_to_remove.append((start_time_ms, end_time_ms))

        duration = (end_time_ms - start_time_ms) / 1000
        logger.info(
            f"  → Will remove {start_time_ms/1000:.1f}s to {end_time_ms/1000:.1f}s ({duration:.1f}s)"
        )

    # Build clean audio by keeping everything EXCEPT the phrase ranges
    logger.info("Building cleaned audio...")
    result = AudioSegment.empty()
    last_end_ms = 0

    for start_ms, end_ms in sorted(time_ranges_to_remove):
        # Keep audio from last cut to this cut
        if start_ms > last_end_ms:
            chunk = audio[last_end_ms:start_ms]

            if len(result) > 0:
                # Use crossfade for smooth transitions
                result = result.append(chunk, crossfade=100)
            else:
                result += chunk

        last_end_ms = end_ms

    # Add remaining audio after last phrase
    if last_end_ms < len(audio):
        chunk = audio[last_end_ms:]
        if len(result) > 0:
            result = result.append(chunk, crossfade=100)
        else:
            result += chunk

    # Export
    logger.info(f"Exporting cleaned audio to: {output_mp3}")
    result.export(
        str(output_mp3),
        format="mp3",
        bitrate="192k",
        tags={
            "title": "Meditations (Surgically Cleaned)",
            "artist": "Marcus Aurelius",
        },
    )

    # Summary
    original_mins = len(audio) / 1000 / 60
    cleaned_mins = len(result) / 1000 / 60
    removed_mins = original_mins - cleaned_mins

    logger.info("=" * 70)
    logger.info(f"✅ DONE! Surgically removed {len(matches)} phrases")
    logger.info(f"   Removed time: {removed_mins:.2f} minutes")
    logger.info(
        f"   Original: {original_mins:.1f} min → Cleaned: {cleaned_mins:.1f} min"
    )
    logger.info("   Legitimate content PRESERVED ✓")
    logger.info("=" * 70)


if __name__ == "__main__":
    # Use the ORIGINAL file, not the already-cleaned one
    input_file = Path("processed/meditations_audiobook.mp3")
    output_file = Path("processed/meditations_SURGICAL.mp3")

    if not input_file.exists():
        print(f"ERROR: {input_file} not found!")
        exit(1)

    start_time = time.perf_counter()
    surgical_remove_phrases(input_file, output_file)
    elapsed = time.perf_counter() - start_time

    print(f"\n⏱️  Total processing time: {elapsed/60:.1f} minutes")
