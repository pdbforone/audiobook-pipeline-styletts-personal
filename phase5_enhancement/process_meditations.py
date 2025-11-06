"""
One-time script to process Meditations chunks directly from folder.
Includes phrase cleanup, noise reduction, and normalization.
"""

import logging
import time
import re
from pathlib import Path
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import yaml

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from phase5_enhancement.main import (
    load_config,
    setup_logging,
    reduce_noise,
    normalize_lufs,
    concatenate_with_crossfades,
    normalize_volume
)
from phase5_enhancement.phrase_cleaner import PhraseCleaner, PhraseCleanerConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def extract_chunk_number(filename: str) -> int:
    """Extract chunk number from: 'the meditations, by Marcus Aurelius_chunk_899.wav'"""
    match = re.search(r'_chunk_(\d+)\.wav$', filename)
    if match:
        return int(match.group(1))
    return 0


def main():
    # Config
    chunks_dir = Path(__file__).parent / "meditations_chunks"
    output_dir = Path(__file__).parent / "processed"
    output_dir.mkdir(exist_ok=True)
    
    # Load config for settings
    config = load_config("config.yaml")
    setup_logging(config)
    
    logger.info("=" * 60)
    logger.info("PROCESSING MEDITATIONS - ONE-TIME SCRIPT")
    logger.info("=" * 60)
    
    # Initialize phrase cleaner
    phrase_cleaner = None
    if config.enable_phrase_cleanup:
        logger.info("Initializing phrase cleaner...")
        cleaner_config = PhraseCleanerConfig(
            enabled=True,
            target_phrases=config.cleanup_target_phrases,
            model_size=config.cleanup_whisper_model,
            save_transcripts=config.cleanup_save_transcripts
        )
        phrase_cleaner = PhraseCleaner(cleaner_config)
        logger.info(f"[OK] Phrase cleaner ready (model: {config.cleanup_whisper_model})")
        logger.info(f"  Target phrases: {config.cleanup_target_phrases}")
    else:
        logger.warning("Phrase cleanup is DISABLED in config!")
    
    # Find all chunks
    wav_files = list(chunks_dir.glob("*.wav"))
    logger.info(f"Found {len(wav_files)} .wav files")
    
    if not wav_files:
        logger.error("No .wav files found!")
        return 1
    
    # Sort by chunk number
    sorted_files = sorted(wav_files, key=lambda f: extract_chunk_number(f.name))
    logger.info(f"Processing chunks 1-{extract_chunk_number(sorted_files[-1].name)}")
    
    # Process each chunk
    enhanced_chunks = []
    start_time = time.perf_counter()
    phrases_removed_total = 0
    chunks_cleaned = 0
    
    for i, wav_path in enumerate(sorted_files, 1):
        try:
            chunk_num = extract_chunk_number(wav_path.name)
            
            # STEP 1: Phrase cleanup
            if phrase_cleaner:
                cleaned_audio, sr, cleanup_meta = phrase_cleaner.clean_audio(wav_path)
                
                if cleaned_audio is not None and cleanup_meta.get('status') == 'cleaned':
                    audio = cleaned_audio
                    phrases_removed = cleanup_meta.get('phrases_removed', 0)
                    phrases_removed_total += phrases_removed
                    chunks_cleaned += 1
                    if phrases_removed > 0:
                        logger.info(f"  Chunk {chunk_num}: Removed {phrases_removed} phrase(s)")
                else:
                    # No phrase found or error - load original
                    import librosa
                    audio, sr = librosa.load(wav_path, sr=config.sample_rate, mono=True)
            else:
                # No cleaner - load original
                import librosa
                audio, sr = librosa.load(wav_path, sr=config.sample_rate, mono=True)
            
            # STEP 2: Volume normalization
            if config.enable_volume_normalization:
                audio, _, _ = normalize_volume(audio, sr, config.volume_norm_headroom)
            
            # STEP 3: Noise reduction
            enhanced = reduce_noise(audio, sr, config.noise_reduction_factor)
            
            # STEP 4: LUFS normalization
            enhanced, lufs = normalize_lufs(enhanced, sr, config.lufs_target)
            
            # STEP 5: Safety limiter
            peak = np.max(np.abs(enhanced))
            if peak > 0.95:
                enhanced = enhanced * (0.95 / peak)
            
            enhanced_chunks.append(enhanced)
            
            if i % 50 == 0:
                logger.info(f"Processed {i}/{len(sorted_files)} chunks...")
            
        except Exception as e:
            logger.error(f"Failed on chunk {chunk_num}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    logger.info(f"Successfully enhanced {len(enhanced_chunks)}/{len(sorted_files)} chunks")
    if phrase_cleaner:
        logger.info(f"Phrase cleanup: {phrases_removed_total} phrases removed from {chunks_cleaned} chunks")
    
    # Concatenate with crossfades
    logger.info("Stitching chunks together...")
    combined_audio = concatenate_with_crossfades(
        enhanced_chunks, 
        config.sample_rate, 
        config.crossfade_duration
    )
    
    # Export to MP3
    mp3_path = output_dir / "meditations_audiobook.mp3"
    logger.info(f"Exporting to: {mp3_path}")
    
    audio_int16 = (combined_audio * 32767).astype(np.int16)
    audio_segment = AudioSegment(
        audio_int16.tobytes(),
        frame_rate=config.sample_rate,
        sample_width=2,
        channels=1,
    )
    
    audio_segment.export(
        mp3_path,
        format="mp3",
        bitrate=config.mp3_bitrate,
        tags={
            "title": "Meditations",
            "artist": "Marcus Aurelius",
            "album": "Audiobook",
            "genre": "Philosophy",
        },
    )
    
    duration_sec = len(combined_audio) / config.sample_rate
    duration_min = duration_sec / 60
    
    total_time = time.perf_counter() - start_time
    
    logger.info("=" * 60)
    logger.info("COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Final audiobook: {mp3_path}")
    logger.info(f"Duration: {duration_min:.1f} minutes ({duration_sec:.0f} seconds)")
    logger.info(f"Phrases removed: {phrases_removed_total} from {chunks_cleaned} chunks")
    logger.info(f"Processing time: {total_time:.1f} seconds")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
