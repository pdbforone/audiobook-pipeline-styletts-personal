"""
Audio Phrase Cleaner - Core Implementation

Detects and removes specific phrases from audio files using:
1. Whisper for speech-to-text with word-level timestamps
2. Pattern matching to find target phrases
3. pydub for surgical audio removal

This module is designed to be standalone but follows the audiobook-pipeline
conventions for potential future integration.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from faster_whisper import WhisperModel
from pydub import AudioSegment
import yaml
import time

logger = logging.getLogger(__name__)


class AudiobookCleaner:
    """
    Automated phrase detection and removal for audiobook files.
    
    Uses Whisper for transcription with word-level timestamps,
    then removes matching audio segments with surgical precision.
    """
    
    def __init__(
        self,
        target_phrases: List[str],
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        """
        Initialize cleaner with target phrases and Whisper model.
        
        Args:
            target_phrases: List of phrases to detect and remove
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: "cpu" or "cuda"
            compute_type: "int8" for CPU optimization, "float16" for GPU
        """
        self.target_phrases = [p.lower().strip() for p in target_phrases]
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        
        logger.info(f"Initializing Whisper model: {model_size} on {device} with {compute_type}")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        
    @classmethod
    def from_config(cls, config_path: Path) -> "AudiobookCleaner":
        """
        Create cleaner from YAML config file.
        
        Args:
            config_path: Path to phrases.yaml config
            
        Returns:
            Configured AudiobookCleaner instance
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return cls(
            target_phrases=config.get('target_phrases', []),
            model_size=config.get('whisper', {}).get('model_size', 'base'),
            device=config.get('whisper', {}).get('device', 'cpu'),
            compute_type=config.get('whisper', {}).get('compute_type', 'int8')
        )
    
    def transcribe_with_timestamps(
        self,
        audio_path: Path,
        save_transcript: bool = True
    ) -> Tuple[List[Dict], Optional[Path]]:
        """
        Transcribe audio and return segments with word-level timestamps.
        
        Args:
            audio_path: Path to audio file
            save_transcript: Whether to save SRT transcript file
            
        Returns:
            (segments_list, transcript_path)
        """
        start_time = time.perf_counter()
        logger.info(f"Transcribing: {audio_path.name}")
        
        segments, info = self.model.transcribe(
            str(audio_path),
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,  # Remove silence for faster processing
            language="en"
        )
        
        # Convert generator to list
        segments_list = []
        for segment in segments:
            segments_list.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text,
                'words': segment.words if hasattr(segment, 'words') else None
            })
        
        elapsed = time.perf_counter() - start_time
        logger.info(f"Transcription complete: {len(segments_list)} segments in {elapsed:.1f}s")
        
        transcript_path = None
        if save_transcript:
            transcript_path = audio_path.parent / f"{audio_path.stem}.srt"
            self._save_srt(segments_list, transcript_path)
            logger.info(f"Saved transcript: {transcript_path}")
        
        return segments_list, transcript_path
    
    def _save_srt(self, segments: List[Dict], output_path: Path):
        """Save segments as SRT subtitle file for manual review."""
        def format_timestamp(seconds: float) -> str:
            """Convert seconds to SRT timestamp format HH:MM:SS,mmm"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, start=1):
                f.write(f"{i}\n")
                f.write(f"{format_timestamp(segment['start'])} --> "
                       f"{format_timestamp(segment['end'])}\n")
                f.write(f"{segment['text'].strip()}\n\n")
    
    def find_target_phrases(self, segments: List[Dict]) -> List[Dict]:
        """
        Search transcribed segments for target phrases.
        
        Args:
            segments: List of transcription segments with timestamps
            
        Returns:
            List of matches with start/end times and matched phrase
        """
        matches = []
        
        for segment in segments:
            segment_text = segment['text'].lower().strip()
            
            for phrase in self.target_phrases:
                if phrase in segment_text:
                    match = {
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text'],
                        'phrase': phrase,
                        'confidence': 1.0  # Could add confidence scoring later
                    }
                    matches.append(match)
                    logger.info(
                        f"Found '{phrase}' at {segment['start']:.2f}s - {segment['end']:.2f}s"
                    )
                    break  # Don't double-count segments
        
        return matches
    
    def remove_audio_segments(
        self,
        audio_path: Path,
        segments_to_remove: List[Dict],
        crossfade_ms: int = 200
    ) -> Optional[AudioSegment]:
        """
        Remove specified segments from audio with crossfading.
        
        Args:
            audio_path: Path to audio file
            segments_to_remove: List of segments with start/end times
            crossfade_ms: Crossfade duration to avoid clicks
            
        Returns:
            Cleaned AudioSegment or None if nothing to remove
        """
        if not segments_to_remove:
            logger.info("No segments to remove")
            return None
        
        logger.info(f"Loading audio: {audio_path.name}")
        audio = AudioSegment.from_file(str(audio_path))
        original_duration = len(audio) / 1000.0  # Convert to seconds
        
        # Sort segments by start time
        segments = sorted(segments_to_remove, key=lambda x: x['start'])
        
        # Build clean audio by keeping parts between removed segments
        result = AudioSegment.empty()
        last_end_ms = 0
        
        for segment in segments:
            start_ms = int(segment['start'] * 1000)
            end_ms = int(segment['end'] * 1000)
            
            # Keep audio from last_end to current segment start
            if start_ms > last_end_ms:
                chunk = audio[last_end_ms:start_ms]
                
                if len(result) > 0 and crossfade_ms > 0:
                    # Crossfade with previous chunk
                    result = result.append(chunk, crossfade=crossfade_ms)
                else:
                    result += chunk
            
            last_end_ms = end_ms
        
        # Add remaining audio after last segment
        if last_end_ms < len(audio):
            chunk = audio[last_end_ms:]
            if len(result) > 0 and crossfade_ms > 0:
                result = result.append(chunk, crossfade=crossfade_ms)
            else:
                result += chunk
        
        cleaned_duration = len(result) / 1000.0
        removed_duration = original_duration - cleaned_duration
        
        logger.info(
            f"Removed {len(segments)} segment(s), "
            f"total duration reduced by {removed_duration:.1f}s "
            f"({original_duration:.1f}s → {cleaned_duration:.1f}s)"
        )
        
        return result
    
    def process_file(
        self,
        input_path: Path,
        output_path: Path,
        save_transcript: bool = True,
        crossfade_ms: int = 200,
        dry_run: bool = False
    ) -> Dict:
        """
        Complete pipeline: transcribe → detect → remove → export.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for cleaned audio output
            save_transcript: Whether to save SRT transcript
            crossfade_ms: Crossfade duration for smooth edits
            dry_run: If True, detect but don't modify audio
            
        Returns:
            Dictionary with results and metrics
        """
        start_time = time.perf_counter()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {input_path.name}")
        logger.info(f"{'='*60}")
        
        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            return {
                'status': 'error',
                'error': 'File not found'
            }
        
        try:
            # Step 1: Transcribe
            segments, transcript_path = self.transcribe_with_timestamps(
                input_path,
                save_transcript=save_transcript
            )
            
            # Step 2: Find target phrases
            matches = self.find_target_phrases(segments)
            
            if not matches:
                logger.info("✓ No target phrases found - file is clean")
                return {
                    'status': 'clean',
                    'segments_removed': 0,
                    'transcript_path': str(transcript_path) if transcript_path else None
                }
            
            # Step 3: Remove segments (unless dry run)
            if dry_run:
                logger.info(f"DRY RUN: Would remove {len(matches)} segment(s)")
                return {
                    'status': 'dry_run',
                    'segments_found': len(matches),
                    'matches': matches,
                    'transcript_path': str(transcript_path) if transcript_path else None
                }
            
            cleaned_audio = self.remove_audio_segments(
                input_path,
                matches,
                crossfade_ms=crossfade_ms
            )
            
            # Step 4: Export
            if cleaned_audio:
                logger.info(f"Exporting to: {output_path}")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                cleaned_audio.export(
                    str(output_path),
                    format="mp3",
                    bitrate="192k",
                    parameters=["-q:a", "0"]  # Highest quality
                )
                
                elapsed = time.perf_counter() - start_time
                logger.info(f"✓ Processing complete in {elapsed:.1f}s")
                
                return {
                    'status': 'success',
                    'segments_removed': len(matches),
                    'matches': matches,
                    'output_path': str(output_path),
                    'transcript_path': str(transcript_path) if transcript_path else None,
                    'processing_time': elapsed
                }
            
        except Exception as e:
            logger.error(f"✗ Error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def batch_process(
        self,
        input_dir: Path,
        output_dir: Path,
        pattern: str = "*.mp3",
        **kwargs
    ) -> Dict:
        """
        Process multiple audio files in a directory.
        
        Args:
            input_dir: Directory containing audio files
            output_dir: Directory for cleaned outputs
            pattern: File pattern to match (default: *.mp3)
            **kwargs: Additional arguments passed to process_file
            
        Returns:
            Summary dictionary with batch results
        """
        audio_files = list(input_dir.glob(pattern))
        
        if not audio_files:
            logger.warning(f"No files matching '{pattern}' in {input_dir}")
            return {'status': 'no_files', 'files_processed': 0}
        
        logger.info(f"Found {len(audio_files)} files to process")
        
        results = []
        for audio_path in audio_files:
            output_path = output_dir / audio_path.name
            result = self.process_file(audio_path, output_path, **kwargs)
            result['file'] = audio_path.name
            results.append(result)
        
        # Summary
        successful = sum(1 for r in results if r['status'] == 'success')
        clean = sum(1 for r in results if r['status'] == 'clean')
        errors = sum(1 for r in results if r['status'] == 'error')
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Batch complete: {successful} cleaned, {clean} already clean, {errors} errors")
        logger.info(f"{'='*60}")
        
        return {
            'status': 'complete',
            'total_files': len(audio_files),
            'successful': successful,
            'clean': clean,
            'errors': errors,
            'results': results
        }
