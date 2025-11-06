"""
Diagnostic Script - Check what Whisper is actually transcribing
This will help us understand why the phrase isn't being detected.
"""

import logging
from pathlib import Path
from faster_whisper import WhisperModel
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def diagnose_transcription(input_mp3: Path, sample_timestamp: float = 203.7):
    """
    Check what Whisper transcribes around a known phrase location.
    
    Args:
        input_mp3: Path to audio file
        sample_timestamp: Known timestamp where phrase occurs (from previous log)
    """
    
    logger.info(f"Loading audio: {input_mp3}")
    audio = AudioSegment.from_mp3(str(input_mp3))
    
    # Extract 30-second sample around the known phrase
    start_ms = int((sample_timestamp - 10) * 1000)
    end_ms = int((sample_timestamp + 20) * 1000)
    sample = audio[start_ms:end_ms]
    
    # Save sample
    sample_path = Path("temp_sample.wav")
    sample.export(str(sample_path), format="wav")
    logger.info(f"Extracted 30-second sample around {sample_timestamp}s")
    
    # Transcribe sample with word-level timestamps
    logger.info("Transcribing sample with word-level timestamps...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(sample_path),
        beam_size=5,
        word_timestamps=True,
        language="en"
    )
    
    # Print detailed word-by-word output
    logger.info("\n" + "=" * 70)
    logger.info("WORD-BY-WORD TRANSCRIPTION:")
    logger.info("=" * 70)
    
    word_count = 0
    for segment in segments:
        logger.info(f"\nSegment {segment.start:.1f}s - {segment.end:.1f}s:")
        logger.info(f"  Full text: '{segment.text}'")
        
        if hasattr(segment, 'words') and segment.words:
            logger.info(f"  Words ({len(segment.words)} total):")
            for word in segment.words:
                word_count += 1
                # Show word with its exact format, including spaces
                word_str = repr(word.word)  # Shows quotes and escape chars
                logger.info(f"    [{word_count}] {word.start:.2f}s-{word.end:.2f}s: {word_str}")
    
    logger.info("\n" + "=" * 70)
    logger.info("ANALYSIS:")
    logger.info("=" * 70)
    
    # Try to find target phrase with different matching strategies
    all_words = []
    for segment in segments:
        if hasattr(segment, 'words') and segment.words:
            for word in segment.words:
                all_words.append(word.word)
    
    # Strategy 1: Exact match with spaces stripped
    words_stripped = [w.strip() for w in all_words]
    text_stripped = ' '.join(words_stripped).lower()
    logger.info(f"\n1. Full text (spaces stripped, lowercase):")
    logger.info(f"   '{text_stripped}'")
    
    if 'you need to add some text for me to talk' in text_stripped:
        logger.info("   ✅ FOUND with Strategy 1 (exact match)")
    elif 'you need to add text for me to talk' in text_stripped:
        logger.info("   ✅ FOUND with Strategy 1 (without 'some')")
    else:
        logger.info("   ❌ NOT FOUND with Strategy 1")
    
    # Strategy 2: Check individual words
    logger.info(f"\n2. Individual words (stripped, lowercase):")
    for i, word in enumerate(words_stripped):
        logger.info(f"   [{i}] '{word.lower()}'")
    
    # Strategy 3: Look for partial matches
    target_words = ["you", "need", "to", "add", "text", "for", "me", "to", "talk"]
    logger.info(f"\n3. Looking for word sequence: {target_words}")
    
    for i in range(len(words_stripped) - len(target_words) + 1):
        window = [w.lower().strip('.,!?;:') for w in words_stripped[i:i+len(target_words)]]
        if window == target_words:
            logger.info(f"   ✅ FOUND at index {i}!")
            break
    else:
        logger.info(f"   ❌ NOT FOUND")
    
    # Clean up
    sample_path.unlink()
    logger.info("\n" + "=" * 70)


if __name__ == "__main__":
    input_file = Path("processed/meditations_audiobook.mp3")
    
    if not input_file.exists():
        print(f"ERROR: {input_file} not found!")
        exit(1)
    
    # Test with known timestamp from previous log (203.7s)
    diagnose_transcription(input_file, sample_timestamp=203.7)
