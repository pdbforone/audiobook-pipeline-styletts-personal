"""
Complete workflow for preparing audiobook for YouTube.
Handles cleaning, subtitle generation, and video creation.
"""

import logging
import argparse
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if required dependencies are installed."""
    missing = []
    
    try:
        import faster_whisper
    except ImportError:
        missing.append("faster-whisper")
    
    try:
        import pydub
    except ImportError:
        missing.append("pydub")
    
    try:
        import srt
    except ImportError:
        missing.append("srt")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")
    
    if missing:
        logger.error("❌ Missing required packages:")
        for pkg in missing:
            logger.error(f"  - {pkg}")
        logger.error("\nInstall with: pip install " + " ".join(missing))
        return False
    
    # Check FFmpeg
    import subprocess
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ FFmpeg not found!")
        logger.error("Install from: https://ffmpeg.org/download.html")
        logger.error("Or use: winget install ffmpeg")
        return False
    
    logger.info("✅ All requirements satisfied")
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Complete audiobook to YouTube workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full workflow (clean → subtitles → video)
  python youtube_workflow.py --audio meditations_audiobook.mp3 --all
  
  # Just clean the audio
  python youtube_workflow.py --audio meditations_audiobook.mp3 --clean-only
  
  # Clean with dry run first
  python youtube_workflow.py --audio meditations_audiobook.mp3 --clean-only --dry-run
  
  # Skip cleaning, just create subtitles and video
  python youtube_workflow.py --audio meditations_cleaned.mp3 --skip-clean
        """
    )
    
    parser.add_argument("--audio", required=True, help="Input audio file")
    parser.add_argument("--title", default="The Meditations", help="Book title")
    parser.add_argument("--author", default="Marcus Aurelius", help="Author name")
    
    # Workflow control
    parser.add_argument("--all", action="store_true", help="Run complete workflow")
    parser.add_argument("--clean-only", action="store_true", help="Only clean audio")
    parser.add_argument("--skip-clean", action="store_true", help="Skip cleaning step")
    parser.add_argument("--dry-run", action="store_true", help="Dry run for cleaning")
    
    # Optional overrides
    parser.add_argument("--output-dir", help="Output directory (default: ./youtube_ready)")
    parser.add_argument("--cover", help="Custom cover image")
    
    args = parser.parse_args()
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Setup paths
    audio_file = Path(args.audio)
    if not audio_file.exists():
        logger.error(f"❌ Audio file not found: {audio_file}")
        return 1
    
    # Output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path("youtube_ready")
    
    output_dir.mkdir(exist_ok=True)
    
    # Generate timestamp for files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 60)
    logger.info("AUDIOBOOK TO YOUTUBE WORKFLOW")
    logger.info("=" * 60)
    logger.info(f"Input: {audio_file}")
    logger.info(f"Title: {args.title}")
    logger.info(f"Author: {args.author}")
    logger.info(f"Output: {output_dir}/")
    logger.info("=" * 60)
    
    # Step 1: Clean audio (unless skipped)
    cleaned_audio = audio_file
    
    if not args.skip_clean:
        logger.info("\n📝 STEP 1: Cleaning Audio")
        logger.info("-" * 60)
        
        from clean_audiobook_v2 import clean_audiobook
        
        cleaned_audio = output_dir / f"{audio_file.stem}_cleaned_{timestamp}.mp3"
        
        try:
            clean_audiobook(audio_file, cleaned_audio, dry_run=args.dry_run)
            
            if args.dry_run:
                logger.info("\n🔍 Dry run complete. Review the report above.")
                logger.info("If it looks good, run without --dry-run")
                return 0
            
            logger.info(f"✅ Cleaned audio: {cleaned_audio}")
            
        except Exception as e:
            logger.error(f"❌ Cleaning failed: {e}")
            return 1
    else:
        logger.info("\n⏭️  STEP 1: Skipping audio cleaning")
        logger.info(f"Using: {cleaned_audio}")
    
    if args.clean_only:
        logger.info("\n✅ Clean-only mode complete!")
        logger.info(f"Cleaned file: {cleaned_audio}")
        return 0
    
    # Step 2: Generate subtitles
    logger.info("\n📝 STEP 2: Generating Subtitles")
    logger.info("-" * 60)
    
    from generate_subtitles import generate_subtitles
    
    srt_file = output_dir / f"{audio_file.stem}_{timestamp}.srt"
    
    try:
        generate_subtitles(cleaned_audio, srt_file, model_size="medium")
        logger.info(f"✅ Subtitles: {srt_file}")
    except Exception as e:
        logger.error(f"❌ Subtitle generation failed: {e}")
        return 1
    
    # Step 3: Create video
    logger.info("\n🎬 STEP 3: Creating YouTube Video")
    logger.info("-" * 60)
    
    from create_youtube_video import create_youtube_video, create_cover_image
    
    # Cover image
    if args.cover:
        cover_image = Path(args.cover)
        if not cover_image.exists():
            logger.error(f"❌ Cover image not found: {cover_image}")
            return 1
    else:
        cover_image = output_dir / "cover.jpg"
        if not cover_image.exists():
            logger.info("Creating default cover image...")
            create_cover_image(cover_image, title=args.title, author=args.author)
    
    video_file = output_dir / f"{audio_file.stem}_{timestamp}.mp4"
    
    try:
        create_youtube_video(
            audio_file=cleaned_audio,
            cover_image=cover_image,
            output_video=video_file,
            title=args.title,
            author=args.author
        )
        logger.info(f"✅ Video: {video_file}")
    except Exception as e:
        logger.error(f"❌ Video creation failed: {e}")
        return 1
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("✅ WORKFLOW COMPLETE!")
    logger.info("=" * 60)
    logger.info("\n📦 YouTube Ready Files:")
    logger.info(f"  Video:     {video_file}")
    logger.info(f"  Subtitles: {srt_file}")
    logger.info(f"  Cover:     {cover_image}")
    
    logger.info("\n📺 Upload to YouTube:")
    logger.info("  1. Go to YouTube Studio → Create → Upload videos")
    logger.info(f"  2. Upload: {video_file.name}")
    logger.info("  3. Add title, description, tags")
    logger.info("  4. Go to Subtitles → Upload file")
    logger.info(f"  5. Upload: {srt_file.name}")
    logger.info("  6. Review and publish!")
    
    logger.info("\n✨ Done! Your audiobook is ready for YouTube.")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit(main())
