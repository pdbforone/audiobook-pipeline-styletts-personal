"""
Create YouTube video from audiobook and cover image.
Uses FFmpeg to combine audio with static image.
"""

import logging
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def create_cover_image(
    output_path: Path,
    title: str = "The Meditations",
    author: str = "Marcus Aurelius",
    width: int = 1920,
    height: int = 1080
):
    """
    Create a simple cover image for YouTube video.
    
    Args:
        output_path: Where to save the cover image
        title: Book title
        author: Author name
        width: Image width in pixels
        height: Image height in pixels
    """
    
    logger.info(f"Creating cover image: {width}x{height}")
    
    # Create image with gradient background
    img = Image.new('RGB', (width, height), color='#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default if not available
    try:
        title_font = ImageFont.truetype("arial.ttf", 120)
        author_font = ImageFont.truetype("arial.ttf", 80)
    except:
        title_font = ImageFont.load_default()
        author_font = ImageFont.load_default()
    
    # Add title and author text
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    
    author_bbox = draw.textbbox((0, 0), author, font=author_font)
    author_width = author_bbox[2] - author_bbox[0]
    
    # Center title
    title_x = (width - title_width) // 2
    title_y = (height - title_height) // 2 - 100
    
    # Center author below title
    author_x = (width - author_width) // 2
    author_y = title_y + title_height + 50
    
    # Draw text with shadow for better readability
    shadow_offset = 3
    draw.text((title_x + shadow_offset, title_y + shadow_offset), title, 
              fill='#000000', font=title_font)
    draw.text((title_x, title_y), title, fill='#ffffff', font=title_font)
    
    draw.text((author_x + shadow_offset, author_y + shadow_offset), author,
              fill='#000000', font=author_font)
    draw.text((author_x, author_y), author, fill='#8b9dc3', font=author_font)
    
    img.save(str(output_path), quality=95)
    logger.info(f"✓ Saved cover image to: {output_path}")

def create_youtube_video(
    audio_file: Path,
    cover_image: Path,
    output_video: Path,
    title: str = "The Meditations",
    author: str = "Marcus Aurelius"
):
    """
    Create YouTube video from audio + static image using FFmpeg.
    
    Args:
        audio_file: Input audio file (MP3, WAV, etc.)
        cover_image: Cover image file (JPG, PNG)
        output_video: Output video file (MP4)
        title: Book title for metadata
        author: Author name for metadata
    """
    
    logger.info("=" * 60)
    logger.info("Creating YouTube Video")
    logger.info("=" * 60)
    
    # Create cover image if it doesn't exist
    if not cover_image.exists():
        logger.info("Cover image not found, creating default...")
        create_cover_image(cover_image, title=title, author=author)
    
    logger.info(f"Audio: {audio_file}")
    logger.info(f"Image: {cover_image}")
    logger.info(f"Output: {output_video}")
    
    # FFmpeg command to create video
    # -loop 1: Loop the image
    # -i: Input image and audio
    # -c:v libx264: H.264 video codec (YouTube compatible)
    # -tune stillimage: Optimize for static image
    # -c:a aac: AAC audio codec (YouTube compatible)
    # -b:a 192k: Audio bitrate
    # -pix_fmt yuv420p: Pixel format (YouTube compatible)
    # -shortest: End video when audio ends
    
    cmd = [
        'ffmpeg',
        '-loop', '1',
        '-i', str(cover_image),
        '-i', str(audio_file),
        '-c:v', 'libx264',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        '-movflags', '+faststart',  # Optimize for web streaming
        '-metadata', f'title={title}',
        '-metadata', f'artist={author}',
        str(output_video)
    ]
    
    logger.info("Running FFmpeg...")
    logger.info("This may take 10-20 minutes for a full audiobook")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("=" * 60)
        logger.info("✅ VIDEO CREATED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info(f"Output: {output_video}")
        logger.info(f"Size: {output_video.stat().st_size / 1024 / 1024:.1f} MB")
        
        logger.info("\n📺 Next Steps:")
        logger.info("  1. Generate subtitles (if not done yet):")
        logger.info(f"     python generate_subtitles.py --input {audio_file}")
        logger.info("  2. Upload video to YouTube")
        logger.info("  3. Add the SRT subtitle file")
        logger.info("  4. Add description, tags, and publish!")
        
    except subprocess.CalledProcessError as e:
        logger.error("❌ FFmpeg failed!")
        logger.error(f"Error: {e.stderr}")
        logger.error("\nMake sure FFmpeg is installed:")
        logger.error("  Download: https://ffmpeg.org/download.html")
        logger.error("  Or install with: winget install ffmpeg")
        raise
    except FileNotFoundError:
        logger.error("❌ FFmpeg not found!")
        logger.error("Please install FFmpeg:")
        logger.error("  Download: https://ffmpeg.org/download.html")
        logger.error("  Or install with: winget install ffmpeg")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create YouTube video from audiobook")
    parser.add_argument("--audio", required=True, help="Input audio file (MP3, WAV)")
    parser.add_argument("--image", help="Cover image (default: creates one)")
    parser.add_argument("--output", help="Output video file (default: video.mp4)")
    parser.add_argument("--title", default="The Meditations", help="Book title")
    parser.add_argument("--author", default="Marcus Aurelius", help="Author name")
    
    args = parser.parse_args()
    
    audio_file = Path(args.audio)
    
    if not audio_file.exists():
        print(f"❌ ERROR: Audio file not found: {audio_file}")
        exit(1)
    
    # Default cover image path
    if args.image:
        cover_image = Path(args.image)
    else:
        cover_image = audio_file.parent / "cover.jpg"
    
    # Default output path
    if args.output:
        output_video = Path(args.output)
    else:
        output_video = audio_file.with_suffix('.mp4')
    
    create_youtube_video(
        audio_file=audio_file,
        cover_image=cover_image,
        output_video=output_video,
        title=args.title,
        author=args.author
    )
