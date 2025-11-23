"""
FAST phrase removal: Strip first 3 seconds from each chunk, then re-stitch.
Use this if "You need to add some text" is always at chunk START.
"""

import logging
from pathlib import Path
from pydub import AudioSegment
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def extract_chunk_number(filename: str) -> int:
    match = re.search(r"_chunk_(\d+)\.wav$", filename)
    return int(match.group(1)) if match else 0


def strip_and_stitch(
    chunks_dir: Path, output_mp3: Path, strip_seconds: float = 3.0
):
    """Strip first N seconds from each chunk and re-stitch."""

    wav_files = sorted(
        chunks_dir.glob("*.wav"), key=lambda f: extract_chunk_number(f.name)
    )

    if not wav_files:
        logger.error("No .wav files found!")
        return

    logger.info(
        f"Processing {len(wav_files)} chunks (stripping first {strip_seconds}s each)..."
    )

    result = AudioSegment.empty()
    strip_ms = int(strip_seconds * 1000)

    for i, wav_path in enumerate(wav_files, 1):
        audio = AudioSegment.from_wav(str(wav_path))

        # Strip first N seconds
        if len(audio) > strip_ms:
            trimmed = audio[strip_ms:]
        else:
            logger.warning(
                f"Chunk {i} shorter than {strip_seconds}s, skipping trim"
            )
            trimmed = audio

        # Append with crossfade
        if len(result) > 0:
            result = result.append(trimmed, crossfade=200)
        else:
            result += trimmed

        if i % 100 == 0:
            logger.info(f"  Processed {i}/{len(wav_files)} chunks...")

    logger.info(f"Exporting to: {output_mp3}")
    result.export(
        str(output_mp3),
        format="mp3",
        bitrate="192k",
        tags={
            "title": "Meditations (Start-Stripped)",
            "artist": "Marcus Aurelius",
        },
    )

    duration_min = len(result) / 1000 / 60
    logger.info(f"Done! Final audiobook: {duration_min:.1f} minutes")


if __name__ == "__main__":
    chunks_dir = Path("meditations_chunks")
    output_file = Path("processed/meditations_FAST_CLEANED.mp3")

    if not chunks_dir.exists():
        print(f"ERROR: {chunks_dir} not found!")
        exit(1)

    # Try 3 seconds first (adjust if needed)
    strip_and_stitch(chunks_dir, output_file, strip_seconds=3.0)
