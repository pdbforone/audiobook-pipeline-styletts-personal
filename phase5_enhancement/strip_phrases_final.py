"""
Emergency script to remove phrases from FINAL audiobook MP3.
Uses Whisper to find and cut out "You need to add some text for me to talk"
"""

import logging
from pathlib import Path
from faster_whisper import WhisperModel
from pydub import AudioSegment
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

TARGET_PHRASES = [
    "you need to add some text for me to talk",
    "you need to add text for me to talk",
]

def strip_phrases(input_mp3: Path, output_mp3: Path):
    """Remove target phrases from final audiobook."""
    
    logger.info(f"Loading audio: {input_mp3}")
    audio = AudioSegment.from_mp3(str(input_mp3))
    
    logger.info("Transcribing with Whisper (this will take ~10-20 minutes)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        str(input_mp3),
        beam_size=5,
        word_timestamps=False,
        language="en"
    )
    
    # Find matches
    matches = []
    logger.info("Scanning for target phrases...")
    for segment in segments:
        text = segment.text.lower().strip()
        for phrase in TARGET_PHRASES:
            if phrase in text:
                matches.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text
                })
                logger.info(f"  FOUND at {segment.start:.1f}s: '{segment.text}'")
                break
    
    if not matches:
        logger.warning("No phrases found! Check if transcription is accurate.")
        return
    
    logger.info(f"Found {len(matches)} instances. Removing...")
    
    # Build clean audio
    result = AudioSegment.empty()
    last_end_ms = 0
    
    for match in sorted(matches, key=lambda x: x['start']):
        start_ms = int(match['start'] * 1000)
        end_ms = int(match['end'] * 1000)
        
        # Keep audio before this phrase
        if start_ms > last_end_ms:
            chunk = audio[last_end_ms:start_ms]
            if len(result) > 0:
                result = result.append(chunk, crossfade=200)
            else:
                result += chunk
        
        last_end_ms = end_ms
    
    # Add remaining audio
    if last_end_ms < len(audio):
        chunk = audio[last_end_ms:]
        if len(result) > 0:
            result = result.append(chunk, crossfade=200)
        else:
            result += chunk
    
    logger.info(f"Exporting cleaned audio to: {output_mp3}")
    result.export(
        str(output_mp3),
        format="mp3",
        bitrate="192k",
        tags={
            "title": "Meditations (Cleaned)",
            "artist": "Marcus Aurelius"
        }
    )
    
    original_mins = len(audio) / 1000 / 60
    cleaned_mins = len(result) / 1000 / 60
    removed_mins = original_mins - cleaned_mins
    
    logger.info("=" * 60)
    logger.info(f"DONE! Removed {len(matches)} phrases ({removed_mins:.1f} minutes)")
    logger.info(f"Original: {original_mins:.1f} min → Cleaned: {cleaned_mins:.1f} min")
    logger.info("=" * 60)

if __name__ == "__main__":
    input_file = Path("processed/meditations_audiobook.mp3")
    output_file = Path("processed/meditations_CLEANED.mp3")
    
    if not input_file.exists():
        print(f"ERROR: {input_file} not found!")
        exit(1)
    
    strip_phrases(input_file, output_file)
