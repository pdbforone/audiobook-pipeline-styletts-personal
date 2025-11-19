"""
Setup and Run Voice Test
=========================
Prepares the environment and runs voice testing on Gift of the Magi chunk.

This script:
1. Verifies all prerequisites
2. Converts Agnes MP3 to WAV if needed
3. Creates test pipeline.json entry
4. Runs the voice test

Usage:
    python setup_and_run_voice_test.py
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def check_conda_environment():
    """Verify conda environment is activated."""
    conda_env = subprocess.run(
        ["conda", "info", "--envs"],
        capture_output=True,
        text=True
    )
    
    if "phase4_tts" not in conda_env.stdout:
        logger.error("❌ Conda environment 'phase4_tts' not found")
        logger.error("Create it with: conda create -n phase4_tts python=3.11")
        return False
    
    # Check if currently activated
    current_env = subprocess.run(
        ["conda", "info", "--json"],
        capture_output=True,
        text=True
    )
    
    env_data = json.loads(current_env.stdout)
    active_prefix = env_data.get("active_prefix", "")
    
    if "phase4_tts" not in active_prefix:
        logger.warning("⚠️  Conda environment 'phase4_tts' not activated")
        logger.warning("Activate it with: conda activate phase4_tts")
        return False
    
    logger.info("✅ Conda environment 'phase4_tts' is active")
    return True

def check_dependencies():
    """Verify required Python packages are installed."""
    # Note: Some packages have different import names than package names
    required = {
        "torch": "torch",
        "librosa": "librosa",
        "soundfile": "soundfile",
        "yaml": "pyyaml",  # PyYAML imports as 'yaml'
        "requests": "requests",
        "nltk": "nltk"
    }
    
    missing = []
    for import_name, package_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        logger.error(f"❌ Missing packages: {', '.join(missing)}")
        logger.error("Install with: pip install " + " ".join(missing))
        return False
    
    logger.info("✅ All required packages installed")
    return True

def check_chatterbox_installation():
    """Verify Chatterbox TTS Extended is cloned."""
    chatterbox_dir = Path("phase4_tts/Chatterbox-TTS-Extended")
    
    if not chatterbox_dir.exists():
        logger.error(f"❌ Chatterbox not found at {chatterbox_dir}")
        logger.error("Clone it with:")
        logger.error("  cd phase4_tts")
        logger.error("  git clone https://github.com/resemble-ai/Chatterbox-TTS-Extended.git")
        return False
    
    logger.info("✅ Chatterbox TTS Extended found")
    return True

def convert_agnes_mp3():
    """Convert Agnes Moorehead MP3 to WAV if needed."""
    mp3_file = Path("voice_samples/processed/Agnes_Moorehead_01_sample.mp3")
    wav_file = Path("voice_samples/processed/Agnes_Moorehead_01_sample.wav")
    
    if not mp3_file.exists():
        logger.info("ℹ️  Agnes MP3 not found, skipping conversion")
        return True
    
    if wav_file.exists():
        logger.info("✅ Agnes WAV already exists")
        return True
    
    logger.info("Converting Agnes MP3 to WAV...")
    
    try:
        import librosa
        import soundfile as sf
        
        y, sr = librosa.load(str(mp3_file), sr=None, mono=True)
        sf.write(str(wav_file), y, sr)
        
        logger.info(f"✅ Converted: {wav_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")
        return False

def check_test_chunk():
    """Verify test chunk exists."""
    chunk_file = Path("phase3-chunking/chunks/Gift of the Magi_chunk_001.txt")
    
    if not chunk_file.exists():
        logger.error(f"❌ Test chunk not found: {chunk_file}")
        return False
    
    # Read chunk to verify it's valid
    try:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if len(text) < 50:
            logger.error(f"❌ Test chunk too short: {len(text)} chars")
            return False
        
        logger.info(f"✅ Test chunk found: {len(text)} characters")
        logger.info(f"   Preview: {text[:100]}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ Could not read test chunk: {e}")
        return False

def create_test_pipeline_entry():
    """Create pipeline.json entry for testing if needed."""
    pipeline_file = Path("pipeline.json")
    
    if not pipeline_file.exists():
        logger.warning("⚠️  pipeline.json not found, creating minimal version")
        pipeline_data = {
            "pipeline_version": "1.0",
            "tts_profile": "fiction",
            "phase3": {
                "files": {
                    "Gift_of_the_Magi": {
                        "chunk_paths": [
                            "phase3-chunking/chunks/Gift of the Magi_chunk_001.txt"
                        ],
                        "chunk_metrics": {
                            "selected_voice": "auto"
                        }
                    }
                }
            }
        }
        
        with open(pipeline_file, 'w') as f:
            json.dump(pipeline_data, f, indent=2)
        
        logger.info("✅ Created test pipeline.json")
    else:
        logger.info("✅ pipeline.json exists")
    
    return True

def run_voice_test():
    """Execute the voice test script."""
    logger.info("\n" + "="*80)
    logger.info("Running Voice Comparison Test")
    logger.info("="*80 + "\n")
    
    result = subprocess.run(
        [sys.executable, "test_all_voices_magi.py"],
        capture_output=False  # Show output in real-time
    )
    
    return result.returncode == 0

def main():
    """Main setup and test runner."""
    logger.info("="*80)
    logger.info("Voice Test Setup and Runner")
    logger.info("="*80 + "\n")
    
    # Run all checks
    checks = [
        ("Conda Environment", check_conda_environment),
        ("Python Dependencies", check_dependencies),
        ("Chatterbox Installation", check_chatterbox_installation),
        ("Agnes MP3 Conversion", convert_agnes_mp3),
        ("Test Chunk", check_test_chunk),
        ("Pipeline Entry", create_test_pipeline_entry)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        logger.info(f"\nChecking: {check_name}...")
        try:
            if not check_func():
                failed_checks.append(check_name)
        except Exception as e:
            logger.error(f"❌ {check_name} check failed with exception: {e}")
            failed_checks.append(check_name)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("Setup Check Summary")
    logger.info("="*80)
    
    if failed_checks:
        logger.error(f"\n❌ Failed checks: {len(failed_checks)}/{len(checks)}")
        for check in failed_checks:
            logger.error(f"   - {check}")
        logger.error("\nPlease fix the issues above before running the test.")
        return 1
    
    logger.info(f"\n✅ All checks passed: {len(checks)}/{len(checks)}")
    logger.info("\nProceeding with voice test...\n")
    
    # Run the test
    if run_voice_test():
        logger.info("\n" + "="*80)
        logger.info("✅ Voice test completed successfully!")
        logger.info("="*80)
        logger.info("\nCheck results at: phase4_tts/voice_comparison_test/")
        logger.info("- voice_test_results.json (metrics)")
        logger.info("- voice_test_*.wav (audio samples)")
        return 0
    else:
        logger.error("\n" + "="*80)
        logger.error("❌ Voice test failed")
        logger.error("="*80)
        logger.error("\nCheck the logs above for errors.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
