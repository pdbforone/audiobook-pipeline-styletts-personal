#!/usr/bin/env python3
"""
Phase 4 Audio Sample Downloader for Chatterbox TTS Extended Voice Cloning

Downloads 20-30 second voice samples from public domain sources (LibriVox, Archive.org),
preprocesses to optimal format (WAV 44.1kHz, 16-bit, mono), and extracts clean segments.

CRITICAL: Chatterbox TTS Extended requires 10-30 SECONDS (not minutes) for voice cloning.
All sources are public domain (LibriVox/Archive.org) and commercially usable without restriction.

Usage:
    python download_voice_samples.py --genre philosophy-analytic --narrator "Bob Neufeld"
    python download_voice_samples.py --download-all
    python download_voice_samples.py --list-narrators
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import urllib.error

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Voice sample catalog - PUBLIC DOMAIN ONLY (LibriVox/Archive.org)
# All narrators: Public domain recordings, commercially usable, no restrictions
# Sample target: 20-30 seconds optimal for Chatterbox TTS Extended
# NOTE: Using Book/Chapter 2-3 to avoid translator prefaces/notes in Book 1
VOICE_CATALOG = {
    "philosophy-analytic": {
        "Bob Neufeld": {
            "work": "Plato's The Republic (Book 2)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                # Book 2 - avoids translator preface
                "https://archive.org/download/republic_version_2_1310_librivox/republic_02_plato_64kb.mp3"
            ],
            "extract_segment": {"start": 15, "duration": 25},  # Skip chapter intro
            "quality": "excellent",
            "commercial_use": True
        }
    },
    "philosophy-continental": {
        "D.E. Wittkower": {
            "work": "Descartes' Meditations (Meditation 2)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                # Meditation 2 - main philosophical content
                "https://archive.org/download/meditations_descartes_dew_librivox/descartes-02-meditations.mp3"
            ],
            "extract_segment": {"start": 10, "duration": 25},
            "quality": "excellent",
            "commercial_use": True
        }
    },
    "philosophy-classical": {
        "Geoffrey Edwards": {
            "work": "Aristotle's Nicomachean Ethics (Book 2)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                # Book 2 - main text (Book 1 often has preface)
                "https://archive.org/download/nicomachean_ethics_ge_librivox/nicomacheanethics_02_aristotle.mp3"
            ],
            "extract_segment": {"start": 15, "duration": 25},
            "quality": "high",
            "commercial_use": True
        }
    },
    "theology-modern": {
        "David Leeson": {
            "work": "A.W. Tozer's The Pursuit of God (Chapter 2)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                # Chapter 2 - main content (NO _64kb suffix for this one!)
                "https://archive.org/download/pursuit_of_god_1105_librivox/pursuitofgod_02_tozer.mp3"
            ],
            "extract_segment": {"start": 20, "duration": 25},
            "quality": "clean",
            "commercial_use": True
        }
    },
    "theology-historical": {
        "MaryAnn Spiegel": {
            "work": "Augustine's The Confessions (Book 2)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                # Book 2 = file 03 (confessions_03 is Book 2, confessions_02 is preface)
                "https://archive.org/download/confessions_1510_librivox/confessions_03_augustine_64kb.mp3"
            ],
            "extract_segment": {"start": 20, "duration": 25},
            "quality": "excellent",
            "commercial_use": True
        }
    },
    "horror": {
        "Vincent Price": {
            "work": "The Price of Fear BBC (Episode 1)",
            "license": "BBC Radio Archive - Check usage rights",
            "source_type": "archive_org",
            "urls": [
                "https://archive.org/download/price-of-fearUPGRADES/ThePriceOfFear-01-TheSpecialityOfTheHouse.mp3"
            ],
            "extract_segment": {"start": 60, "duration": 25},  # Skip intro music
            "quality": "high BBC production",
            "commercial_use": False,  # BBC content - verify rights
            "note": "Verify BBC archive usage rights for commercial use"
        }
    },
    "british-male": {
        "David Clarke": {
            "work": "Sherlock Holmes Adventures (Story 2)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                # Story 2 - The Red-Headed League (adventuressherlockholmes_02 is story 2)
                "https://archive.org/download/adventuressherlockholmes_v4_1501_librivox/adventuressherlockholmes_02_doyle.mp3"
            ],
            "extract_segment": {"start": 30, "duration": 25},
            "quality": "professional",
            "commercial_use": True
        }
    },
    "british-female": {
        "Ruth Golding": {
            "work": "Wuthering Heights (Chapter 2)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                # Chapter 2 - main narrative
                "https://archive.org/download/wuthering_heights_rg_librivox/wutheringheights_02_bronte.mp3"
            ],
            "extract_segment": {"start": 25, "duration": 25},
            "quality": "excellent",
            "commercial_use": True
        }
    }
}


class AudioDownloader:
    """Download and preprocess audio samples for voice cloning."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = output_dir / "raw"
        self.processed_dir = output_dir / "processed"
        self.raw_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
        
    def check_dependencies(self) -> bool:
        """Check if required tools are installed."""
        missing = []
        
        # Check ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append("ffmpeg")
            
        # Check ffprobe
        try:
            subprocess.run(["ffprobe", "-version"], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append("ffprobe")
            
        if missing:
            logger.error(f"Missing required tools: {', '.join(missing)}")
            logger.error("Install ffmpeg: https://ffmpeg.org/download.html")
            logger.error("  Windows: choco install ffmpeg")
            logger.error("  macOS: brew install ffmpeg")
            logger.error("  Linux: sudo apt install ffmpeg")
            return False
        return True
    
    def download_file(self, url: str, output_path: Path) -> bool:
        """Download file from URL."""
        try:
            logger.info(f"Downloading: {url}")
            urllib.request.urlretrieve(url, output_path)
            logger.info(f"Downloaded to: {output_path}")
            return True
        except urllib.error.URLError as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def extract_segment(self, input_path: Path, output_path: Path,
                       start: float, duration: float) -> bool:
        """Extract specific time segment from audio file."""
        try:
            logger.info(f"Extracting {duration}s segment starting at {start}s...")
            cmd = [
                "ffmpeg", "-i", str(input_path),
                "-ss", str(start),  # Start time
                "-t", str(duration),  # Duration
                "-ar", "44100",  # 44.1kHz
                "-ac", "1",  # Mono
                "-sample_fmt", "s16",  # 16-bit
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Extracted segment: {output_path}")
                return True
            else:
                logger.error(f"Segment extraction failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return False
    
    def trim_silence(self, input_path: Path, output_path: Path) -> bool:
        """
        Trim silence from beginning and end of audio.
        Uses ffmpeg silenceremove filter for clean segment edges.
        """
        try:
            logger.info(f"Trimming silence from {input_path.name}...")
            cmd = [
                "ffmpeg", "-i", str(input_path),
                "-af", (
                    "silenceremove="
                    "start_periods=1:"      # Remove silence at start
                    "start_duration=0.1:"   # Detect 0.1s silence
                    "start_threshold=-50dB:"  # -50dB threshold
                    "stop_periods=-1:"      # Remove silence at end
                    "stop_duration=0.1:"    # Detect 0.1s silence
                    "stop_threshold=-50dB"  # -50dB threshold
                ),
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Silence trimmed: {output_path}")
                return True
            else:
                logger.warning(f"Silence trimming failed (continuing anyway): {result.stderr}")
                # Copy original if trimming fails
                if input_path != output_path:
                    import shutil
                    shutil.copy2(input_path, output_path)
                return True
                
        except Exception as e:
            logger.warning(f"Silence trimming error (continuing): {e}")
            return True
    
    def validate_sample(self, audio_path: Path) -> dict:
        """
        Validate audio sample quality for Chatterbox TTS Extended.
        
        Returns dict with:
        - valid: bool
        - duration: float
        - sample_rate: int
        - channels: int
        - bit_depth: int
        - issues: list of warning strings
        """
        issues = []
        
        try:
            # Get audio properties with ffprobe
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=sample_rate,channels,bits_per_sample,duration",
                "-of", "json",
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {
                    "valid": False,
                    "issues": ["Could not read audio file properties"]
                }
            
            import json
            data = json.loads(result.stdout)
            
            if not data.get("streams"):
                return {
                    "valid": False,
                    "issues": ["No audio stream found"]
                }
            
            stream = data["streams"][0]
            
            # Extract properties
            sample_rate = int(stream.get("sample_rate", 0))
            channels = int(stream.get("channels", 0))
            bit_depth = int(stream.get("bits_per_sample", 16))
            duration = float(stream.get("duration", 0))
            
            # Validation checks
            if duration < 10:
                issues.append(f"Duration too short: {duration:.1f}s (minimum 10s)")
            elif duration > 35:
                issues.append(f"Duration too long: {duration:.1f}s (optimal 10-30s)")
            elif duration < 15:
                issues.append(f"Duration low: {duration:.1f}s (recommended 20-30s)")
            
            if sample_rate < 24000:
                issues.append(f"Sample rate low: {sample_rate}Hz (recommended 44100Hz+)")
            
            if channels != 1:
                issues.append(f"Not mono: {channels} channels (must be mono)")
            
            if bit_depth != 16:
                issues.append(f"Bit depth: {bit_depth}-bit (recommended 16-bit)")
            
            # Check for clipping (peaks at max amplitude)
            cmd_stats = [
                "ffmpeg", "-i", str(audio_path),
                "-af", "volumedetect",
                "-f", "null", "-"
            ]
            result_stats = subprocess.run(cmd_stats, capture_output=True, text=True)
            
            # Parse max volume from stderr
            import re
            max_volume_match = re.search(r'max_volume: ([-\d.]+) dB', result_stats.stderr)
            if max_volume_match:
                max_volume = float(max_volume_match.group(1))
                if max_volume > -0.5:
                    issues.append(f"Possible clipping: max volume {max_volume:.1f}dB (should be < -1dB)")
            
            # Check for silence (mean volume too low)
            mean_volume_match = re.search(r'mean_volume: ([-\d.]+) dB', result_stats.stderr)
            if mean_volume_match:
                mean_volume = float(mean_volume_match.group(1))
                if mean_volume < -30:
                    issues.append(f"Audio very quiet: mean volume {mean_volume:.1f}dB")
            
            return {
                "valid": len(issues) == 0,
                "duration": duration,
                "sample_rate": sample_rate,
                "channels": channels,
                "bit_depth": bit_depth,
                "issues": issues
            }
            
        except Exception as e:
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"]
            }
    
    def download_narrator(self, genre: str, narrator: str, 
                         skip_validation: bool = False) -> bool:
        """Download and extract 20-30s voice sample for a narrator."""
        if genre not in VOICE_CATALOG:
            logger.error(f"Unknown genre: {genre}")
            return False
            
        if narrator not in VOICE_CATALOG[genre]:
            logger.error(f"Unknown narrator: {narrator}")
            return False
            
        narrator_data = VOICE_CATALOG[genre][narrator]
        
        # Check commercial use
        if not narrator_data.get("commercial_use", False):
            logger.warning(f"⚠️  {narrator} - {narrator_data['work']}")
            logger.warning(f"License: {narrator_data.get('license', 'Unknown')}")
            logger.warning(f"Note: {narrator_data.get('note', 'Verify commercial usage rights')}")
            return False
        
        # Create narrator directory
        narrator_dir = self.raw_dir / f"{genre}_{narrator.replace(' ', '_')}"
        narrator_dir.mkdir(exist_ok=True)
        
        success_count = 0
        for i, url in enumerate(narrator_data["urls"], 1):
            filename = Path(url).name
            raw_path = narrator_dir / filename
            
            # Download if not exists
            if not raw_path.exists():
                if not self.download_file(url, raw_path):
                    continue
            else:
                logger.info(f"Already downloaded: {raw_path}")
            
            # Extract 20-30s segment
            segment_info = narrator_data.get("extract_segment", {"start": 0, "duration": 25})
            temp_filename = f"{narrator.replace(' ', '_')}_{i:02d}_temp.wav"
            temp_path = narrator_dir / temp_filename
            
            processed_filename = f"{narrator.replace(' ', '_')}_{i:02d}_sample.wav"
            processed_path = self.processed_dir / processed_filename
            
            if not processed_path.exists():
                # Step 1: Extract segment
                if not self.extract_segment(
                    raw_path, 
                    temp_path,
                    segment_info["start"],
                    segment_info["duration"]
                ):
                    continue
                
                # Step 2: Trim silence from edges
                if not self.trim_silence(temp_path, processed_path):
                    continue
                
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()
                
                # Step 3: Validate
                if not skip_validation:
                    validation = self.validate_sample(processed_path)
                    
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Validation Report: {processed_filename}")
                    logger.info(f"{'='*60}")
                    logger.info(f"Duration: {validation.get('duration', 0):.1f}s")
                    logger.info(f"Sample Rate: {validation.get('sample_rate', 0)}Hz")
                    logger.info(f"Channels: {validation.get('channels', 0)}")
                    logger.info(f"Bit Depth: {validation.get('bit_depth', 0)}-bit")
                    
                    if validation.get("issues"):
                        logger.warning(f"\n⚠️  Quality Issues:")
                        for issue in validation["issues"]:
                            logger.warning(f"  • {issue}")
                    
                    if validation.get("valid"):
                        logger.info(f"\n✓ PASSED: Sample meets Chatterbox TTS Extended requirements")
                        success_count += 1
                    else:
                        logger.warning(f"\n✗ FAILED: Sample has quality issues (usable but not optimal)")
                        success_count += 1  # Still count as success
                    
                    logger.info(f"{'='*60}\n")
                else:
                    success_count += 1
            else:
                logger.info(f"Already processed: {processed_path}")
                success_count += 1
        
        logger.info(f"Successfully processed {success_count}/{len(narrator_data['urls'])} samples")
        logger.info(f"✓ All samples are Public Domain (LibriVox) - commercially usable")
        return success_count > 0
    
    def list_narrators(self):
        """Print all available narrators by genre with licensing info."""
        print("\n=== Available Voice Samples (Public Domain, Commercially Usable) ===\n")
        print("Target: 20-30 seconds optimal for Chatterbox TTS Extended\n")
        print("NOTE: Using Book/Chapter 2-3 to avoid translator prefaces in Book 1\n")
        
        for genre, narrators in VOICE_CATALOG.items():
            print(f"\n{genre.upper().replace('-', ' ')}:")
            for narrator, data in narrators.items():
                commercial = data.get("commercial_use", False)
                status = "✓" if commercial else "⚠"
                print(f"  {status} {narrator}")
                print(f"     Work: {data['work']}")
                print(f"     License: {data.get('license', 'Unknown')}")
                print(f"     Quality: {data['quality']}")
                if not commercial:
                    print(f"     ⚠️  {data.get('note', 'Verify usage rights')}")
                if data.get("extract_segment"):
                    seg = data["extract_segment"]
                    print(f"     Sample: {seg['duration']}s extracted from {seg['start']}s mark")
        
        print("\n")
        print("Legend:")
        print("  ✓ = Public Domain (LibriVox) - Free commercial use")
        print("  ⚠ = Verify licensing before commercial use")
        print("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download and preprocess voice samples for Phase 4 TTS"
    )
    parser.add_argument(
        "--genre",
        help="Genre to download (e.g., philosophy-analytic, horror, poetry)"
    )
    parser.add_argument(
        "--narrator",
        help="Specific narrator name"
    )
    parser.add_argument(
        "--download-all",
        action="store_true",
        help="Download all available samples"
    )
    parser.add_argument(
        "--list-narrators",
        action="store_true",
        help="List all available narrators"
    )
    parser.add_argument(
        "--validate-only",
        type=Path,
        help="Validate existing sample without downloading"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip quality validation (faster)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("voice_samples"),
        help="Output directory (default: voice_samples/)"
    )
    
    args = parser.parse_args()
    
    downloader = AudioDownloader(args.output_dir)
    
    # Validate existing sample
    if args.validate_only:
        if not args.validate_only.exists():
            logger.error(f"File not found: {args.validate_only}")
            return 1
        
        logger.info(f"Validating: {args.validate_only}")
        validation = downloader.validate_sample(args.validate_only)
        
        print(f"\n{'='*60}")
        print(f"Validation Report: {args.validate_only.name}")
        print(f"{'='*60}")
        print(f"Duration: {validation.get('duration', 0):.1f}s")
        print(f"Sample Rate: {validation.get('sample_rate', 0)}Hz")
        print(f"Channels: {validation.get('channels', 0)}")
        print(f"Bit Depth: {validation.get('bit_depth', 0)}-bit")
        
        if validation.get("issues"):
            print(f"\n⚠️  Quality Issues:")
            for issue in validation["issues"]:
                print(f"  • {issue}")
        
        if validation.get("valid"):
            print(f"\n✓ PASSED: Sample meets Chatterbox TTS Extended requirements")
            return 0
        else:
            print(f"\n✗ FAILED: Sample has quality issues (see above)")
            return 1
    
    # List narrators
    if args.list_narrators:
        downloader.list_narrators()
        return 0
    
    # Check dependencies
    if not downloader.check_dependencies():
        return 1
    
    # Download specific narrator
    if args.genre and args.narrator:
        success = downloader.download_narrator(
            args.genre, 
            args.narrator,
            skip_validation=args.skip_validation
        )
        return 0 if success else 1
    
    # Download all
    if args.download_all:
        logger.info("Downloading all available voice samples...")
        success_count = 0
        total_count = 0
        
        for genre, narrators in VOICE_CATALOG.items():
            for narrator in narrators:
                total_count += 1
                if downloader.download_narrator(
                    genre, 
                    narrator,
                    skip_validation=args.skip_validation
                ):
                    success_count += 1
        
        logger.info(f"Downloaded {success_count}/{total_count} narrators")
        return 0
    
    # No action specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
