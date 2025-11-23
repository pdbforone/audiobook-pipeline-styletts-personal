#!/usr/bin/env python3
"""
Phase 6.5: Simplified Video Assembly
Single-file solution for creating ELL-optimized audiobook videos

Usage:
    python phase65_video_assembly.py --audio audiobook.mp3 --subtitles subs.srt --title "Book" --author "Author"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont

    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("WARNING: Pillow not installed - cover art unavailable")


def create_cover_art(title, author, output_path, width=1920, height=1080):
    """Generate simple cover art with gradient background."""
    if not PIL_OK:
        print("Skipping cover art - Pillow not installed")
        return None

    # Create gradient background (deep blue)
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(25 + (15 - 25) * y / height)
        g = int(25 + (15 - 25) * y / height)
        b = int(50 + (30 - 50) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Add text
    try:
        title_font = ImageFont.truetype("arial.ttf", 80)
        author_font = ImageFont.truetype("arial.ttf", 50)
    except:
        title_font = ImageFont.load_default()
        author_font = ImageFont.load_default()

    # Draw title
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (width - title_w) // 2
    title_y = height // 3

    # Outline
    for dx in [-2, 0, 2]:
        for dy in [-2, 0, 2]:
            draw.text(
                (title_x + dx, title_y + dy),
                title,
                font=title_font,
                fill=(0, 0, 0),
            )
    draw.text((title_x, title_y), title, font=title_font, fill=(255, 215, 0))

    # Draw author
    author_text = f"by {author}"
    author_bbox = draw.textbbox((0, 0), author_text, font=author_font)
    author_w = author_bbox[2] - author_bbox[0]
    author_x = (width - author_w) // 2
    author_y = title_y + 150

    for dx in [-2, 0, 2]:
        for dy in [-2, 0, 2]:
            draw.text(
                (author_x + dx, author_y + dy),
                author_text,
                font=author_font,
                fill=(0, 0, 0),
            )
    draw.text(
        (author_x, author_y),
        author_text,
        font=author_font,
        fill=(200, 200, 200),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    print(f"✓ Cover art created: {output_path}")
    return output_path


def create_video(audio_path, cover_path, subtitle_path, output_path):
    """Create video with cover art and styled subtitles."""

    subtitle_style = (
        "force_style='FontName=Arial,"
        "FontSize=32,"
        "PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H000000&,"
        "Outline=3,"
        "Shadow=2,"
        "Bold=1,"
        "Alignment=2,"
        "MarginV=80'"
    )

    subtitle_escaped = str(subtitle_path).replace("\\", "/")

    if cover_path and cover_path.exists():
        # Use cover art
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(cover_path),
            "-i",
            str(audio_path),
            "-vf",
            f"subtitles={subtitle_escaped}:{subtitle_style}",
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-c:a",
            "copy",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
    else:
        # Use black background
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:r=25",
            "-i",
            str(audio_path),
            "-vf",
            f"subtitles={subtitle_escaped}:{subtitle_style}",
            "-c:v",
            "libx264",
            "-c:a",
            "copy",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]

    print("\n[Video Assembly] Starting FFmpeg...")
    print(f"  Audio: {audio_path.name}")
    print(f"  Subtitles: {subtitle_path.name}")
    print(f"  Output: {output_path}")
    print("\n  This will take 5-10 minutes...")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600
        )

        if result.returncode != 0:
            print("\nERROR: FFmpeg failed")
            print(f"Error: {result.stderr[-500:]}")
            return False

        print(f"\n✓ Video created successfully: {output_path}")
        return True

    except subprocess.TimeoutExpired:
        print("\nERROR: FFmpeg timeout (1 hour)")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False


def generate_youtube_metadata(title, author, output_path):
    """Generate YouTube metadata JSON."""

    metadata = {
        "title": f"{title} by {author} | Full Audiobook with Subtitles | ELL",
        "description": f"""📖 {title}
✍️ by {author}

✅ Professional narration with synchronized subtitles
✅ Optimized for English Language Learners (ELL)
✅ High-quality audio production
📚 Public domain literature | Free to share

Perfect for:
• English language learners
• Literature students
• Classic book enthusiasts
• Audiobook listeners

#Audiobook #ClassicLiterature #ELL #PublicDomain #EnglishLearning""",
        "tags": [
            "audiobook",
            "full audiobook",
            "audiobook with subtitles",
            "classic literature",
            "public domain",
            "ELL",
            "English language learning",
            title.lower(),
            author.lower(),
        ],
        "category": 27,  # Education
        "privacy": "public",
        "made_for_kids": False,
        "language": "en",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ YouTube metadata saved: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Phase 6.5: Simplified Video Assembly"
    )
    parser.add_argument(
        "--audio", type=Path, required=True, help="Audio file path"
    )
    parser.add_argument(
        "--subtitles", type=Path, required=True, help="SRT subtitle file"
    )
    parser.add_argument("--title", type=str, required=True, help="Book title")
    parser.add_argument(
        "--author", type=str, required=True, help="Book author"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory",
    )
    parser.add_argument(
        "--no-cover", action="store_true", help="Skip cover art generation"
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.audio.exists():
        print(f"ERROR: Audio file not found: {args.audio}")
        return 1

    if not args.subtitles.exists():
        print(f"ERROR: Subtitle file not found: {args.subtitles}")
        return 1

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    file_id = args.title.replace(" ", "_").replace("/", "_")

    print("=" * 60)
    print("Phase 6.5: Video Assembly")
    print("=" * 60)
    print(f"Title: {args.title}")
    print(f"Author: {args.author}")
    print(f"Audio: {args.audio}")
    print(f"Subtitles: {args.subtitles}")
    print("=" * 60)

    # Step 1: Generate cover art
    cover_path = None
    if not args.no_cover and PIL_OK:
        print("\n[1/3] Generating cover art...")
        cover_path = args.output_dir / f"{file_id}_cover.png"
        cover_path = create_cover_art(args.title, args.author, cover_path)
    else:
        print("\n[1/3] Skipping cover art (using black background)")

    # Step 2: Create video
    print("\n[2/3] Assembling video...")
    video_path = args.output_dir / f"{file_id}_FINAL.mp4"

    if not create_video(args.audio, cover_path, args.subtitles, video_path):
        return 1

    # Step 3: Generate metadata
    print("\n[3/3] Generating YouTube metadata...")
    metadata_path = args.output_dir / f"{file_id}_youtube_metadata.json"
    generate_youtube_metadata(args.title, args.author, metadata_path)

    # Success summary
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"Video:    {video_path}")
    if cover_path:
        print(f"Cover:    {cover_path}")
    print(f"Metadata: {metadata_path}")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Preview the video")
    print("2. Use metadata file for YouTube upload")
    print("3. Enable monetization ($0.50-$2 per 1K views)")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
