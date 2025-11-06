"""
Improved audiobook cleaning with safer phrase removal.
Uses exact phrase matching with context to avoid over-removal.
"""

import logging
from pathlib import Path
from faster_whisper import WhisperModel
from pydub import AudioSegment
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Exact phrases to remove (case-insensitive)
TARGET_PHRASES = [
    "you need to add some text for me to talk",
]

def similarity_ratio(a: str, b: str) -> float:
    """Calculate similarity between two strings (0-1)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def is_exact_match(transcribed_text: str, target_phrase: str, threshold: float = 0.95) -> bool:
    """
    Check if transcribed text is an exact match for target phrase.
    Uses high similarity threshold to avoid false positives.
    """
    transcribed_clean = transcribed_text.lower().strip()
    
    # Check if phrase is completely contained
    if target_phrase in transcribed_clean:
        return True
    
    # Check with high similarity threshold
    ratio = similarity_ratio(transcribed_clean, target_phrase)
    return ratio >= threshold

def clean_audiobook(input_mp3: Path, output_mp3: Path, dry_run: bool = False):
    """
    Remove target phrases from audiobook with safety checks.
    
    Args:
        input_mp3: Input audiobook file
        output_mp3: Output cleaned file
        dry_run: If True, only report matches without modifying file
    """
    
    logger.info(f"Loading audio: {input_mp3}")
    audio = AudioSegment.from_mp3(str(input_mp3))
    original_duration_min = len(audio) / 1000 / 60
    logger.info(f"Original duration: {original_duration_min:.1f} minutes")
    
    logger.info("Transcribing with Whisper (this may take 10-20 minutes)...")
    logger.info("Using 'base' model with conservative settings...")
    
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(input_mp3),
        beam_size=5,
        word_timestamps=True,  # Enable word-level timestamps for precision
        language="en",
        condition_on_previous_text=True  # Better context awareness
    )
    
    logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2%})")
    
    # Find exact matches with safety checks
    matches = []
    false_positives = []
    
    logger.info("\nScanning for target phrases...")
    logger.info("=" * 60)
    
    for segment in segments:
        text = segment.text.strip()
        
        # Check each target phrase
        for phrase in TARGET_PHRASES:
            if is_exact_match(text, phrase, threshold=0.95):
                # Calculate segment duration
                duration = segment.end - segment.start
                
                match_info = {
                    'start': segment.start,
                    'end': segment.end,
                    'duration': duration,
                    'text': text,
                    'similarity': similarity_ratio(text, phrase)
                }
                
                matches.append(match_info)
                
                logger.info(f"✓ MATCH at {segment.start:.1f}s ({duration:.1f}s)")
                logger.info(f"  Text: '{text}'")
                logger.info(f"  Similarity: {match_info['similarity']:.1%}")
                
                break  # Don't check other phrases for this segment
        else:
            # Check for near-matches that we're NOT removing (safety check)
            for phrase in TARGET_PHRASES:
                ratio = similarity_ratio(text, phrase)
                if 0.7 <= ratio < 0.95:  # Borderline similarity
                    false_positives.append({
                        'start': segment.start,
                        'text': text,
                        'similarity': ratio
                    })
    
    logger.info("=" * 60)
    logger.info(f"Found {len(matches)} exact matches")
    
    if false_positives:
        logger.warning(f"Found {len(false_positives)} near-matches (NOT removing):")
        for fp in false_positives[:5]:  # Show first 5
            logger.warning(f"  {fp['start']:.1f}s: '{fp['text']}' (similarity: {fp['similarity']:.1%})")
    
    if not matches:
        logger.warning("\n⚠ No exact matches found!")
        logger.warning("Possible reasons:")
        logger.warning("  1. Phrase already removed")
        logger.warning("  2. Transcription didn't catch it")
        logger.warning("  3. Phrase wording is slightly different")
        return
    
    # Calculate total time to be removed
    total_removed_seconds = sum(m['duration'] for m in matches)
    total_removed_minutes = total_removed_seconds / 60
    
    logger.info(f"\n📊 Summary:")
    logger.info(f"  Matches: {len(matches)}")
    logger.info(f"  Total removal: {total_removed_minutes:.2f} minutes ({total_removed_seconds:.1f}s)")
    logger.info(f"  Original duration: {original_duration_min:.1f} minutes")
    logger.info(f"  Expected final duration: {original_duration_min - total_removed_minutes:.1f} minutes")
    logger.info(f"  Percentage removed: {(total_removed_minutes / original_duration_min * 100):.2f}%")
    
    if dry_run:
        logger.info("\n🔍 DRY RUN - No changes made")
        logger.info(f"Run without --dry-run to create cleaned file")
        return
    
    # Build clean audio
    logger.info("\n🔨 Building cleaned audio...")
    result = AudioSegment.empty()
    last_end_ms = 0
    
    for i, match in enumerate(sorted(matches, key=lambda x: x['start']), 1):
        start_ms = int(match['start'] * 1000)
        end_ms = int(match['end'] * 1000)
        
        # Keep audio before this phrase
        if start_ms > last_end_ms:
            chunk = audio[last_end_ms:start_ms]
            
            # Add chunk with crossfade for smooth transition
            if len(result) > 0:
                # Use shorter crossfade to preserve pacing
                result = result.append(chunk, crossfade=150)
            else:
                result += chunk
            
            logger.info(f"  Keeping: {last_end_ms/1000:.1f}s to {start_ms/1000:.1f}s")
        
        logger.info(f"  Removing {i}/{len(matches)}: {start_ms/1000:.1f}s to {end_ms/1000:.1f}s")
        last_end_ms = end_ms
    
    # Add remaining audio after last phrase
    if last_end_ms < len(audio):
        chunk = audio[last_end_ms:]
        if len(result) > 0:
            result = result.append(chunk, crossfade=150)
        else:
            result += chunk
        logger.info(f"  Keeping: {last_end_ms/1000:.1f}s to end")
    
    # Export cleaned audio
    logger.info(f"\n💾 Exporting cleaned audio to: {output_mp3}")
    result.export(
        str(output_mp3),
        format="mp3",
        bitrate="192k",
        parameters=["-q:a", "0"],  # Highest quality
        tags={
            "title": "The Meditations (Cleaned)",
            "artist": "Marcus Aurelius",
            "album": "Philosophy",
            "comment": f"Cleaned with {len(matches)} phrases removed"
        }
    )
    
    # Final report
    cleaned_duration_min = len(result) / 1000 / 60
    removed_duration_min = original_duration_min - cleaned_duration_min
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ CLEANING COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"  Removed: {len(matches)} phrases ({removed_duration_min:.2f} minutes)")
    logger.info(f"  Original: {original_duration_min:.1f} minutes")
    logger.info(f"  Cleaned:  {cleaned_duration_min:.1f} minutes")
    logger.info(f"  Saved:    {(len(audio) - len(result)) / 1024 / 1024:.1f} MB")
    logger.info("=" * 60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean repetitive phrases from audiobook")
    parser.add_argument("--input", default="processed/meditations_audiobook.mp3", help="Input MP3 file")
    parser.add_argument("--output", default="processed/meditations_cleaned_v2.mp3", help="Output MP3 file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without making changes")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_file = Path(args.output)
    
    if not input_file.exists():
        print(f"❌ ERROR: {input_file} not found!")
        exit(1)
    
    clean_audiobook(input_file, output_file, dry_run=args.dry_run)
