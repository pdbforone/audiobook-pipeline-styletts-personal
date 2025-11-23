"""
Generate subtitles for cleaned audiobook using Whisper.
Outputs SRT file for YouTube upload.
"""

import logging
from pathlib import Path
from faster_whisper import WhisperModel
import srt
from datetime import timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def generate_subtitles(
    audio_file: Path, output_srt: Path, model_size: str = "medium"
):
    """
    Generate SRT subtitles from audio file.

    Args:
        audio_file: Input audio file (MP3, WAV, etc.)
        output_srt: Output SRT file path
        model_size: Whisper model size (tiny, base, small, medium, large)
    """

    logger.info(f"Loading audio: {audio_file}")

    logger.info(f"Loading Whisper model: {model_size}")
    logger.info("Note: 'medium' provides best accuracy but is slower")
    logger.info("      Use 'base' for faster processing with good quality")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    logger.info(
        "Transcribing... (this may take 30-60 minutes for full audiobook)"
    )

    segments, info = model.transcribe(
        str(audio_file),
        beam_size=5,
        word_timestamps=True,
        language="en",
        condition_on_previous_text=True,
        vad_filter=True,  # Voice activity detection - removes silence
        vad_parameters=dict(
            min_silence_duration_ms=500,  # Minimum silence to split on
        ),
    )

    logger.info(
        f"Detected language: {info.language} (confidence: {info.language_probability:.1%})"
    )

    # Convert to SRT format
    subtitle_entries = []

    for i, segment in enumerate(segments, start=1):
        subtitle = srt.Subtitle(
            index=i,
            start=timedelta(seconds=segment.start),
            end=timedelta(seconds=segment.end),
            content=segment.text.strip(),
        )
        subtitle_entries.append(subtitle)

        if i % 100 == 0:
            logger.info(
                f"  Processed {i} segments... ({segment.start/60:.1f} minutes)"
            )

    logger.info(f"Generated {len(subtitle_entries)} subtitle entries")

    # Write SRT file
    logger.info(f"Writing subtitles to: {output_srt}")
    with output_srt.open("w", encoding="utf-8") as f:
        f.write(srt.compose(subtitle_entries))

    total_duration_min = subtitle_entries[-1].end.total_seconds() / 60

    logger.info("=" * 60)
    logger.info("✅ SUBTITLES COMPLETE!")
    logger.info(f"  Total segments: {len(subtitle_entries)}")
    logger.info(f"  Duration: {total_duration_min:.1f} minutes")
    logger.info(f"  Output: {output_srt}")
    logger.info("=" * 60)
    logger.info("\n📺 YouTube Upload Steps:")
    logger.info("  1. Upload video with audio")
    logger.info("  2. Go to YouTube Studio → Subtitles")
    logger.info(f"  3. Upload this SRT file: {output_srt.name}")
    logger.info("  4. Review and publish!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate subtitles for audiobook"
    )
    parser.add_argument(
        "--input", required=True, help="Input audio file (MP3, WAV)"
    )
    parser.add_argument(
        "--output", help="Output SRT file (default: input_name.srt)"
    )
    parser.add_argument(
        "--model",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: medium)",
    )

    args = parser.parse_args()

    input_file = Path(args.input)

    if not input_file.exists():
        print(f"❌ ERROR: {input_file} not found!")
        exit(1)

    # Default output name
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = input_file.with_suffix(".srt")

    generate_subtitles(input_file, output_file, model_size=args.model)
