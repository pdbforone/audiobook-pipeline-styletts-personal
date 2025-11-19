#!/usr/bin/env python3
"""
Phase 5.5: Subtitle Generation
Generates .srt and .vtt subtitles from final audiobook with quality validation.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import argparse
import tempfile
from functools import lru_cache

from faster_whisper import WhisperModel
from pydub import AudioSegment
import webvtt

from .models import SubtitleConfig
from .subtitle_aligner import align_timestamps, detect_drift
from .subtitle_validator import calculate_wer, validate_coverage, format_srt, format_vtt
from .subtitle_karaoke import KaraokeGenerator

logger = logging.getLogger(__name__)


@lru_cache(maxsize=3)
def _load_whisper_model(model_size: str, device: str, compute_type: str) -> WhisperModel:
    """Cache Whisper models to avoid repeated downloads/initialization."""
    return WhisperModel(model_size, device=device, compute_type=compute_type)


class SubtitleGenerator:
    """Generate subtitles from audiobook with quality validation."""

    def __init__(self, config: SubtitleConfig, enable_karaoke: bool = False):
        self.config = config
        self.enable_karaoke = enable_karaoke
        self.model = None
        self.audio_duration = None
        self.segments = []
        self.metrics = {}

    def initialize(self):
        """Initialize Whisper model and validate inputs."""
        logger.info(f"Initializing Whisper model: {self.config.model_size}")
        start = time.perf_counter()

        # Load Whisper model
        self.model = _load_whisper_model(
            self.config.model_size,
            self.config.device,
            self.config.compute_type,
        )

        load_time = time.perf_counter() - start
        logger.info(f"Model loaded in {load_time:.2f}s")

        # Get audio duration
        audio = AudioSegment.from_file(str(self.config.audio_path))
        self.audio_duration = len(audio) / 1000.0  # Convert to seconds
        logger.info(f"Audio duration: {self.audio_duration:.2f}s ({self.audio_duration/60:.1f} minutes)")

        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def transcribe(self) -> List[Dict[str, Any]]:
        """Transcribe audio with checkpoint support."""
        logger.info("Starting transcription...")
        start = time.perf_counter()

        segments_data = []
        checkpoint_path = self.config.output_dir / f"{self.config.file_id}_checkpoint.json"

        # Resume from checkpoint if exists
        if self.config.enable_checkpoints and checkpoint_path.exists():
            logger.info(f"Resuming from checkpoint: {checkpoint_path}")
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
                segments_data = checkpoint_data['segments']
                last_end = checkpoint_data['last_end']
                logger.info(f"Resuming from {last_end:.2f}s")

        # Transcribe with faster-whisper
        # Enable word-level timestamps for karaoke mode
        segments_iter, info = self.model.transcribe(
            str(self.config.audio_path),
            language=self.config.language,
            beam_size=self.config.beam_size,
            temperature=self.config.temperature,
            vad_filter=True,  # Voice Activity Detection
            vad_parameters=dict(
                min_silence_duration_ms=500,
                threshold=0.5
            ),
            word_timestamps=self.enable_karaoke  # Enable word-level timestamps for karaoke
        )

        logger.info(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")

        # Process segments
        checkpoint_counter = 0
        for segment in segments_iter:
            segment_data = {
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip(),
                'no_speech_prob': segment.no_speech_prob
            }

            # Capture word-level timestamps for karaoke mode
            if self.enable_karaoke and hasattr(segment, 'words') and segment.words:
                segment_data['words'] = [
                    {
                        'word': word.word,
                        'start': word.start,
                        'end': word.end,
                        'probability': word.probability
                    }
                    for word in segment.words
                ]
                logger.debug(f"Captured {len(segment_data['words'])} words at {segment.start:.2f}s")

            # Handle silence/non-speech
            if segment.no_speech_prob > 0.8 and (segment.end - segment.start) > 3.0:
                segment_data['text'] = '[pause]'
                logger.debug(f"Detected silence at {segment.start:.2f}s")

            segments_data.append(segment_data)

            # Checkpoint every N seconds
            if self.config.enable_checkpoints:
                checkpoint_counter += (segment.end - segment.start)
                if checkpoint_counter >= self.config.checkpoint_interval:
                    self._save_checkpoint(checkpoint_path, segments_data, segment.end)
                    checkpoint_counter = 0

        duration = time.perf_counter() - start
        logger.info(f"Transcription complete: {len(segments_data)} segments in {duration:.2f}s")

        # Clean up checkpoint
        if checkpoint_path.exists():
            checkpoint_path.unlink()

        self.segments = segments_data
        return segments_data

    def _save_checkpoint(self, path: Path, segments: List[Dict], last_end: float):
        """Save checkpoint for resume."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'segments': segments,
                'last_end': last_end,
                'timestamp': time.time()
            }, f, indent=2)
        logger.debug(f"Checkpoint saved at {last_end:.2f}s")

    def process_segments(self) -> List[Dict[str, Any]]:
        """Process segments for optimal subtitle display."""
        logger.info("Processing segments for subtitle display...")

        processed = []
        current_text = ""
        current_start = None
        current_end = None

        for seg in self.segments:
            text = seg['text']

            # Skip empty or pause-only segments
            if not text or text == '[pause]':
                if current_text:
                    processed.append({
                        'start': current_start,
                        'end': current_end,
                        'text': current_text.strip()
                    })
                    current_text = ""
                continue

            # Start new segment
            if not current_text:
                current_start = seg['start']
                current_text = text
                current_end = seg['end']
                continue

            # Check if we should continue or split
            duration = seg['end'] - current_start
            combined_length = len(current_text) + len(text) + 1  # +1 for space

            # Split if: too long, too much duration, or sentence boundary
            should_split = (
                combined_length > self.config.max_chars or
                duration > self.config.max_duration or
                text.endswith(('.', '!', '?'))
            )

            if should_split:
                # Save current segment
                processed.append({
                    'start': current_start,
                    'end': current_end,
                    'text': current_text.strip()
                })
                # Start new segment
                current_text = text
                current_start = seg['start']
                current_end = seg['end']
            else:
                # Continue building segment
                current_text += " " + text
                current_end = seg['end']

        # Add final segment
        if current_text:
            processed.append({
                'start': current_start,
                'end': current_end,
                'text': current_text.strip()
            })

        logger.info(f"Processed {len(processed)} subtitle segments")
        return processed

    def align_with_aeneas(self, reference_text: Path) -> Optional[List[Dict]]:
        """Optional forced alignment using aeneas when reference text is available."""
        try:
            from aeneas.executetask import ExecuteTask
            from aeneas.task import Task
        except ImportError:
            logger.warning("aeneas not installed; skipping forced alignment")
            return None

        task = Task(config_string="task_language=en|is_text_type=plain|os_task_file_format=json")
        task.audio_file_path = str(self.config.audio_path)
        task.text_file_path = str(reference_text)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            sync_map_path = tmp.name
        task.sync_map_file_path = sync_map_path

        try:
            ExecuteTask(task).execute()
            task.output_sync_map_file()
            with open(sync_map_path, "r", encoding="utf-8") as f:
                sync_map = json.load(f)
            fragments = sync_map.get("fragments", [])
            aligned_segments = []
            for frag in fragments:
                try:
                    start = float(frag["begin"])
                    end = float(frag["end"])
                    text = frag.get("lines", [""])[0].strip()
                    if text:
                        aligned_segments.append({"start": start, "end": end, "text": text})
                except (KeyError, ValueError):
                    continue
            if aligned_segments:
                logger.info(f"aeneas aligned {len(aligned_segments)} segments")
                return aligned_segments
            logger.warning("aeneas produced no segments; falling back to Whisper timestamps")
            return None
        except Exception as exc:
            logger.warning(f"aeneas alignment failed: {exc}")
            return None
        finally:
            try:
                Path(sync_map_path).unlink(missing_ok=True)
            except Exception:
                pass

    def align_and_validate(self, segments: List[Dict]) -> Tuple[List[Dict], Dict[str, Any]]:
        """Align timestamps and validate quality."""
        logger.info("Validating subtitle quality...")

        metrics = {}

        if (
            self.config.use_aeneas_alignment
            and self.config.reference_text_path
            and self.config.reference_text_path.exists()
        ):
            aligned = self.align_with_aeneas(self.config.reference_text_path)
            if aligned:
                segments = aligned
                metrics["aligned_with_aeneas"] = True
            else:
                metrics["aligned_with_aeneas"] = False
        else:
            metrics["aligned_with_aeneas"] = False

        # 1. Check coverage
        last_timestamp = segments[-1]['end'] if segments else 0
        coverage = last_timestamp / self.audio_duration if self.audio_duration > 0 else 0
        metrics['coverage'] = coverage
        metrics['last_timestamp'] = last_timestamp

        coverage_ok = validate_coverage(coverage, self.config.min_coverage)
        if not coverage_ok:
            logger.warning(f"Low coverage: {coverage:.2%} (target: {self.config.min_coverage:.0%})")

        # 2. Detect and correct timestamp drift
        if self.config.enable_drift_correction:
            drift = detect_drift(segments, self.audio_duration)
            metrics['timestamp_drift'] = drift

            if abs(drift) > self.config.drift_correction_threshold:
                logger.info(f"Correcting timestamp drift: {drift:.2f}s")
                segments = align_timestamps(segments, self.audio_duration)
                metrics['drift_corrected'] = True
            else:
                metrics['drift_corrected'] = False

        # 3. Calculate WER if reference text provided
        if self.config.reference_text_path and self.config.reference_text_path.exists():
            with open(self.config.reference_text_path, 'r', encoding='utf-8') as f:
                reference_text = f.read()

            transcribed_text = " ".join(seg['text'] for seg in segments)
            wer = calculate_wer(reference_text, transcribed_text)
            metrics['wer'] = wer

            if wer > self.config.max_wer:
                logger.warning(f"High WER: {wer:.2%} (target: <{self.config.max_wer:.0%})")
        else:
            metrics['wer'] = None
            logger.info("No reference text provided - WER not calculated")

        # 4. Calculate segment statistics
        durations = [seg['end'] - seg['start'] for seg in segments]
        lengths = [len(seg['text']) for seg in segments]

        metrics['segment_count'] = len(segments)
        metrics['avg_segment_duration'] = sum(durations) / len(durations) if durations else 0
        metrics['avg_segment_length'] = sum(lengths) / len(lengths) if lengths else 0
        metrics['max_segment_length'] = max(lengths) if lengths else 0

        return segments, metrics

    def save_subtitles(self, segments: List[Dict], raw_segments: List[Dict] = None):
        """Save subtitles in SRT, VTT, and optionally ASS (karaoke) formats."""
        logger.info("Saving subtitle files...")

        # Generate filenames
        srt_path = self.config.output_dir / f"{self.config.file_id}.srt"
        vtt_path = self.config.output_dir / f"{self.config.file_id}.vtt"

        # Save SRT
        srt_content = format_srt(segments)
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        logger.info(f"Saved SRT: {srt_path}")

        # Save VTT
        vtt_content = format_vtt(segments)
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write(vtt_content)
        logger.info(f"Saved VTT: {vtt_path}")

        # Save ASS (karaoke) if enabled
        ass_path = None
        if self.enable_karaoke:
            ass_path = self.config.output_dir / f"{self.config.file_id}_karaoke.ass"
            karaoke_gen = KaraokeGenerator(style_config={
                'fontname': 'Arial',
                'fontsize': 32,
                'primary_color': '&H0000FFFF',  # Yellow (currently being read/highlighted)
                'secondary_color': '&H00FFFFFF',  # White (not yet read)
                'outline': 3,
                'shadow': 2,
                'alignment': 2,  # Bottom center
                'margin_v': 80
            })

            # Use raw_segments (with word data) for karaoke, not processed segments
            segments_for_karaoke = raw_segments if raw_segments is not None else segments
            karaoke_stats = karaoke_gen.generate_ass(segments_for_karaoke, ass_path)
            logger.info(f"Saved karaoke ASS: {ass_path}")

            # Add karaoke stats to metrics
            self.metrics['karaoke_enabled'] = True
            self.metrics['karaoke_stats'] = karaoke_stats
        else:
            self.metrics['karaoke_enabled'] = False

        return srt_path, vtt_path, ass_path

    def save_metrics(self):
        """Save metrics to JSON."""
        metrics_path = self.config.output_dir / f"{self.config.file_id}_metrics.json"

        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2)

        logger.info(f"Saved metrics: {metrics_path}")

    def generate(self) -> Dict[str, Any]:
        """Main generation pipeline."""
        logger.info("=== Phase 5.5: Subtitle Generation ===")
        total_start = time.perf_counter()

        try:
            # Initialize
            self.initialize()

            # Transcribe (captures word-level data for karaoke)
            raw_segments = self.transcribe()

            # Process for display (optimizes for subtitle readability)
            processed_segments = self.process_segments()

            # Align and validate (uses processed segments for timing)
            final_segments, metrics = self.align_and_validate(processed_segments)
            self.metrics = metrics

            # Save outputs (use raw_segments for karaoke to preserve word data)
            srt_path, vtt_path, ass_path = self.save_subtitles(
                final_segments, 
                raw_segments=raw_segments if self.enable_karaoke else None
            )
            self.save_metrics()

            # Calculate total time
            total_duration = time.perf_counter() - total_start
            self.metrics['processing_time'] = total_duration
            self.metrics['status'] = 'success'

            logger.info(f"=== Subtitle generation complete in {total_duration:.2f}s ===")
            logger.info(f"Coverage: {metrics['coverage']:.2%}")
            if metrics['wer'] is not None:
                logger.info(f"WER: {metrics['wer']:.2%}")
            logger.info(f"Segments: {metrics['segment_count']}")
            if self.enable_karaoke:
                logger.info(f"Karaoke mode: ENABLED (ASS file generated)")

            result = {
                'status': 'success',
                'srt_path': str(srt_path),
                'vtt_path': str(vtt_path),
                'metrics': self.metrics
            }

            if ass_path:
                result['ass_path'] = str(ass_path)

            return result

        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate subtitles from audiobook")

    parser.add_argument('--audio', type=Path, required=True,
                       help='Path to audiobook audio file')
    parser.add_argument('--file-id', type=str, required=True,
                       help='File identifier for output naming')
    parser.add_argument('--output-dir', type=Path, default=Path('subtitles'),
                       help='Output directory for subtitle files')
    parser.add_argument('--model', type=str, default='small',
                       choices=['tiny', 'small', 'base'],
                       help='Whisper model size (tiny=fast, base=accurate)')
    parser.add_argument('--reference-text', type=Path, default=None,
                       help='Reference text file for WER calculation')
    parser.add_argument('--use-aeneas', action='store_true',
                       help='Use aeneas forced alignment when reference text is provided')
    parser.add_argument('--no-checkpoints', action='store_true',
                       help='Disable checkpoint/resume')
    parser.add_argument('--no-drift-correction', action='store_true',
                       help='Disable timestamp drift correction')
    parser.add_argument('--karaoke', action='store_true',
                       help='Generate karaoke-style word highlighting (ASS format)')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create config
    config = SubtitleConfig(
        audio_path=args.audio,
        output_dir=args.output_dir,
        file_id=args.file_id,
        model_size=args.model,
        reference_text_path=args.reference_text,
        use_aeneas_alignment=args.use_aeneas,
        enable_checkpoints=not args.no_checkpoints,
        enable_drift_correction=not args.no_drift_correction
    )

    # Generate subtitles
    generator = SubtitleGenerator(config, enable_karaoke=args.karaoke)
    result = generator.generate()

    # Print result
    if result['status'] == 'success':
        print(f"\n✅ Subtitles generated successfully!")
        print(f"SRT: {result['srt_path']}")
        print(f"VTT: {result['vtt_path']}")
        if 'ass_path' in result:
            print(f"ASS (Karaoke): {result['ass_path']}")
        print(f"\nMetrics:")
        print(f"  Coverage: {result['metrics']['coverage']:.2%}")
        if result['metrics']['wer'] is not None:
            print(f"  WER: {result['metrics']['wer']:.2%}")
        print(f"  Segments: {result['metrics']['segment_count']}")
        if result['metrics'].get('karaoke_enabled'):
            karaoke_stats = result['metrics'].get('karaoke_stats', {})
            print(f"  Karaoke words: {karaoke_stats.get('total_words', 0)}")
            print(f"  Avg word duration: {karaoke_stats.get('avg_word_duration', 0):.3f}s")
        print(f"  Processing time: {result['metrics']['processing_time']:.1f}s")
    else:
        print(f"\n❌ Failed: {result['error']}")
        exit(1)


if __name__ == '__main__':
    main()
