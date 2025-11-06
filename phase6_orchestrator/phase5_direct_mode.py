#!/usr/bin/env python3
"""
Phase 5 Direct Mode - Bypass Pipeline
This script bypasses pipeline.json completely and processes ALL audio files
directly from phase4_tts/audio_chunks/ directory.

Use this when pipeline.json is causing issues but you just want to process the audio.
"""

import sys
import logging
from pathlib import Path

# Add Phase 5 to Python path
phase5_dir = Path(__file__).parent.parent / "phase5_enhancement"
sys.path.insert(0, str(phase5_dir / "src"))

from phase5_enhancement.main import (
    load_config,
    setup_logging,
    enhance_chunk,
    concatenate_with_crossfades,
    AudioMetadata
)
from phase5_enhancement.models import EnhancementConfig

import numpy as np
import soundfile as sf
import time
import tempfile
import shutil
import os
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def scan_phase4_audio_directory(audio_dir: Path) -> list[Path]:
    """
    Scan Phase 4's audio directory and return ALL .wav files, sorted by chunk number.
    
    This completely bypasses pipeline.json.
    """
    if not audio_dir.exists():
        logger.error(f"Audio directory not found: {audio_dir}")
        return []
    
    # Get all .wav files
    audio_files = list(audio_dir.glob("*.wav"))
    
    if not audio_files:
        logger.error(f"No .wav files found in {audio_dir}")
        return []
    
    logger.info(f"Found {len(audio_files)} audio files in {audio_dir}")
    
    # Sort by chunk number (extract number from filename)
    import re
    def extract_chunk_num(path: Path) -> int:
        match = re.search(r'chunk[_-](\d+)', path.stem)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+)', path.stem)
        return int(match.group(1)) if match else 0
    
    audio_files = sorted(audio_files, key=extract_chunk_num)
    
    logger.info(f"First file: {audio_files[0].name}")
    logger.info(f"Last file:  {audio_files[-1].name}")
    
    return audio_files


def process_direct_mode(
    audio_dir: Path,
    output_dir: Path,
    config: EnhancementConfig,
    temp_dir: str
) -> tuple[list[AudioMetadata], list[np.ndarray]]:
    """
    Process all audio files directly without consulting pipeline.json.
    
    Returns:
        (metadata_list, enhanced_audio_list)
    """
    # Scan for audio files
    audio_files = scan_phase4_audio_directory(audio_dir)
    
    if not audio_files:
        return [], []
    
    # Create metadata objects
    chunks = [
        AudioMetadata(chunk_id=i, wav_path=str(audio_file))
        for i, audio_file in enumerate(audio_files)
    ]
    
    logger.info(f"Processing {len(chunks)} audio chunks in direct mode...")
    
    processed_metadata = []
    enhanced_chunks = []
    
    # Process with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Enhancing {len(chunks)} chunks...", total=len(chunks))
        
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futures = {
                executor.submit(enhance_chunk, chunk, config, temp_dir): chunk
                for chunk in chunks
            }
            
            for future in as_completed(futures):
                try:
                    metadata, enhanced_audio = future.result(timeout=config.processing_timeout)
                except Exception as e:
                    metadata = futures[future]
                    metadata.status = "failed"
                    metadata.error_message = str(e)
                    enhanced_audio = np.array([], dtype=np.float32)
                    logger.error(f"Chunk {metadata.chunk_id} failed: {e}")
                
                processed_metadata.append(metadata)
                
                # Save enhanced audio
                if metadata.status.startswith("complete") and len(enhanced_audio) > 0:
                    enhanced_path = output_dir / f"enhanced_{metadata.chunk_id:04d}.wav"
                    sf.write(
                        enhanced_path,
                        enhanced_audio,
                        config.sample_rate,
                        format="WAV",
                        subtype="PCM_24",
                    )
                    metadata.enhanced_path = str(enhanced_path)
                    enhanced_chunks.append(enhanced_audio)
                    logger.info(f"✓ Saved: {enhanced_path.name}")
                
                progress.update(task, advance=1)
    
    return processed_metadata, enhanced_chunks


def create_final_audiobook(
    enhanced_chunks: list[np.ndarray],
    output_dir: Path,
    config: EnhancementConfig
):
    """Create the final concatenated audiobook."""
    if not enhanced_chunks:
        logger.error("No enhanced chunks to concatenate")
        return False
    
    logger.info("Creating final audiobook...")
    
    # Concatenate with crossfades
    combined_audio = concatenate_with_crossfades(
        enhanced_chunks,
        config.sample_rate,
        config.crossfade_duration
    )
    
    # Export as MP3
    mp3_path = output_dir / "audiobook.mp3"
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
            "title": config.audiobook_title,
            "artist": config.audiobook_author,
            "album": "Audiobook",
            "genre": "Audiobook",
        },
    )
    
    duration_sec = len(combined_audio) / config.sample_rate
    logger.info(f"✅ Final audiobook created: {mp3_path}")
    logger.info(f"   Duration: {duration_sec:.1f} seconds ({duration_sec/60:.1f} minutes)")
    logger.info(f"   Size: {mp3_path.stat().st_size / (1024*1024):.1f} MB")
    
    return True


def main():
    """Run Phase 5 in direct mode - bypass pipeline.json completely."""
    
    console.print("\n[bold cyan]" + "="*70 + "[/bold cyan]")
    console.print("[bold cyan]Phase 5 Direct Mode - Bypassing Pipeline[/bold cyan]")
    console.print("[bold cyan]" + "="*70 + "[/bold cyan]\n")
    
    # Paths
    project_root = Path(__file__).parent.parent
    phase4_audio_dir = project_root / "phase4_tts" / "audio_chunks"
    phase5_dir = project_root / "phase5_enhancement"
    processed_dir = phase5_dir / "processed"
    output_dir = phase5_dir / "output"
    
    console.print(f"[yellow]Phase 4 audio:[/yellow] {phase4_audio_dir}")
    console.print(f"[yellow]Phase 5 output:[/yellow] {processed_dir}")
    console.print(f"[yellow]Final audiobook:[/yellow] {output_dir}\n")
    
    # Load config
    config_path = phase5_dir / "config.yaml"
    if not config_path.exists():
        console.print(f"[red]Error: config.yaml not found at {config_path}[/red]")
        return 1
    
    config = load_config(str(config_path.name))
    setup_logging(config)
    
    # Override config to disable resume and validation
    config.resume_on_failure = False
    config.quality_validation_enabled = False
    
    console.print(f"[green]✓[/green] Config loaded")
    console.print(f"[green]✓[/green] Resume disabled (processing ALL chunks)")
    console.print(f"[green]✓[/green] Quality validation disabled (no chunks skipped)\n")
    
    # Create output directories
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="phase5_direct_", dir=phase5_dir / "temp")
    logger.info(f"Temp directory: {temp_dir}")
    
    try:
        # Process all audio files
        start_time = time.perf_counter()
        
        processed_metadata, enhanced_chunks = process_direct_mode(
            phase4_audio_dir,
            processed_dir,
            config,
            temp_dir
        )
        
        if not enhanced_chunks:
            console.print("\n[red]❌ No chunks were successfully processed[/red]")
            return 1
        
        # Create final audiobook
        if not create_final_audiobook(enhanced_chunks, output_dir, config):
            console.print("\n[red]❌ Failed to create final audiobook[/red]")
            return 1
        
        # Summary
        duration = time.perf_counter() - start_time
        successful = sum(1 for m in processed_metadata if m.status.startswith("complete"))
        failed = len(processed_metadata) - successful
        
        console.print("\n[bold green]" + "="*70 + "[/bold green]")
        console.print("[bold green]SUCCESS![/bold green]")
        console.print("[bold green]" + "="*70 + "[/bold green]\n")
        console.print(f"[green]Processed:[/green] {successful}/{len(processed_metadata)} chunks")
        console.print(f"[green]Failed:[/green]    {failed} chunks")
        console.print(f"[green]Duration:[/green]  {duration:.1f}s ({duration/60:.1f} minutes)")
        console.print(f"\n[cyan]Enhanced chunks:[/cyan] {processed_dir}")
        console.print(f"[cyan]Final audiobook:[/cyan] {output_dir / 'audiobook.mp3'}\n")
        
        return 0
        
    finally:
        # Cleanup temp
        if config.cleanup_temp_files and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory")


if __name__ == "__main__":
    sys.exit(main())
