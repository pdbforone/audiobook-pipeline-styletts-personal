"""
Audio Cleanup - CLI Entry Point

Command-line interface for phrase detection and removal from audio files.
Designed to work standalone or integrate with audiobook-pipeline.
"""

import argparse
import logging
import sys
from pathlib import Path
from .cleaner import AudiobookCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Audio Phrase Cleaner - Remove specific phrases from audio files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single file
  poetry run python -m audio_cleanup.main \\
    --input chunk_004.mp3 \\
    --output chunk_004_cleaned.mp3

  # Process with custom config
  poetry run python -m audio_cleanup.main \\
    --input chunk_004.mp3 \\
    --output chunk_004_cleaned.mp3 \\
    --config config/phrases.yaml

  # Batch process directory
  poetry run python -m audio_cleanup.main \\
    --input-dir ../audio_chunks \\
    --output-dir ../audio_chunks_cleaned \\
    --batch

  # Dry run (detect only, don't modify)
  poetry run python -m audio_cleanup.main \\
    --input chunk_004.mp3 \\
    --dry-run

  # Verbose logging
  poetry run python -m audio_cleanup.main \\
    --input chunk_004.mp3 \\
    --output chunk_004_cleaned.mp3 \\
    --verbose
        """
    )
    
    # Input/Output arguments
    parser.add_argument(
        "--input",
        type=str,
        help="Input audio file path"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output audio file path (cleaned version)"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Input directory for batch processing"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for batch processing"
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        default="config/phrases.yaml",
        help="Path to config file (default: config/phrases.yaml)"
    )
    parser.add_argument(
        "--phrases",
        nargs="+",
        help="Override config with custom phrases to remove"
    )
    
    # Processing options
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all audio files in input directory"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.mp3",
        help="File pattern for batch processing (default: *.mp3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect phrases but don't modify audio (for testing)"
    )
    parser.add_argument(
        "--no-transcript",
        action="store_true",
        help="Don't save SRT transcript files"
    )
    
    # Model options
    parser.add_argument(
        "--model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )
    
    # Logging
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.batch:
        if not args.input_dir or not args.output_dir:
            parser.error("--batch requires --input-dir and --output-dir")
    else:
        if not args.input:
            parser.error("--input is required (or use --batch mode)")
        if not args.output and not args.dry_run:
            parser.error("--output is required (or use --dry-run)")
    
    # Find config file
    config_path = Path(args.config)
    if not config_path.is_absolute():
        # Try relative to script location
        script_dir = Path(__file__).parent.parent.parent
        config_path = script_dir / args.config
    
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.info("Run from phase_audio_cleanup directory or provide absolute path")
        sys.exit(1)
    
    # Initialize cleaner
    logger.info(f"Loading configuration from: {config_path}")
    
    if args.phrases:
        # Use custom phrases from command line
        cleaner = AudiobookCleaner(
            target_phrases=args.phrases,
            model_size=args.model
        )
        logger.info(f"Using custom phrases: {args.phrases}")
    else:
        # Load from config
        cleaner = AudiobookCleaner.from_config(config_path)
        logger.info(f"Loaded {len(cleaner.target_phrases)} target phrase(s) from config")
    
    # Process files
    try:
        if args.batch:
            # Batch processing
            input_dir = Path(args.input_dir)
            output_dir = Path(args.output_dir)
            
            if not input_dir.exists():
                logger.error(f"Input directory not found: {input_dir}")
                sys.exit(1)
            
            result = cleaner.batch_process(
                input_dir=input_dir,
                output_dir=output_dir,
                pattern=args.pattern,
                save_transcript=not args.no_transcript,
                dry_run=args.dry_run
            )
            
            # Print summary
            print("\n" + "="*60)
            print("BATCH PROCESSING SUMMARY")
            print("="*60)
            print(f"Total files: {result['total_files']}")
            print(f"Successfully cleaned: {result['successful']}")
            print(f"Already clean: {result['clean']}")
            print(f"Errors: {result['errors']}")
            print("="*60 + "\n")
            
            sys.exit(0 if result['errors'] == 0 else 1)
        
        else:
            # Single file processing
            input_path = Path(args.input)
            output_path = Path(args.output) if args.output else None
            
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                sys.exit(1)
            
            if not output_path and not args.dry_run:
                logger.error("Output path required (or use --dry-run)")
                sys.exit(1)
            
            # Set default output path for dry run
            if not output_path:
                output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
            
            result = cleaner.process_file(
                input_path=input_path,
                output_path=output_path,
                save_transcript=not args.no_transcript,
                dry_run=args.dry_run
            )
            
            # Print summary
            print("\n" + "="*60)
            print("PROCESSING SUMMARY")
            print("="*60)
            print(f"Status: {result['status']}")
            
            if result['status'] == 'success':
                print(f"Segments removed: {result['segments_removed']}")
                print(f"Output file: {result['output_path']}")
                if result.get('transcript_path'):
                    print(f"Transcript: {result['transcript_path']}")
                print(f"Processing time: {result['processing_time']:.1f}s")
            elif result['status'] == 'clean':
                print("No target phrases found - file is clean")
            elif result['status'] == 'dry_run':
                print(f"Segments found: {result['segments_found']}")
                for match in result['matches']:
                    print(f"  - '{match['phrase']}' at {match['start']:.2f}s")
            elif result['status'] == 'error':
                print(f"Error: {result['error']}")
            
            print("="*60 + "\n")
            
            sys.exit(0 if result['status'] in ['success', 'clean', 'dry_run'] else 1)
    
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
