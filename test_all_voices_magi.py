"""
Test All Voices on Gift of the Magi Chunk
==========================================
This script tests ALL available voices (both URL-based and local processed samples)
on a single chunk to compare voice quality and cloning effectiveness.

Usage:
    python test_all_voices_magi.py
    
Output:
    - audio_chunks/voice_test_<voice_id>.wav for each voice
    - voice_test_results.json with metrics
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add phase4_tts to path
sys.path.insert(0, str(Path(__file__).parent / "phase4_tts"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Test configuration
CHUNK_PATH = Path("phase3-chunking/chunks/Gift of the Magi_chunk_001.txt")
OUTPUT_DIR = Path("phase4_tts/voice_comparison_test")
VOICE_CONFIG = Path("phase4_tts/configs/voice_references.json")

def read_chunk() -> str:
    """Read the test chunk text."""
    if not CHUNK_PATH.exists():
        raise FileNotFoundError(f"Chunk not found: {CHUNK_PATH}")
    
    with open(CHUNK_PATH, 'r', encoding='utf-8') as f:
        text = f.read().strip()
    
    logger.info(f"Loaded chunk: {len(text)} characters")
    logger.info(f"Text preview: {text[:100]}...")
    return text

def load_voice_config() -> Dict:
    """Load voice references configuration."""
    if not VOICE_CONFIG.exists():
        raise FileNotFoundError(f"Voice config not found: {VOICE_CONFIG}")
    
    with open(VOICE_CONFIG, 'r') as f:
        config = json.load(f)
    
    voices = config.get("voice_references", {})
    logger.info(f"Loaded {len(voices)} voice configurations")
    return voices

def prepare_all_voices(voices: Dict) -> Dict[str, str]:
    """
    Prepare all voice references (download URLs or use local files).
    Returns: Dict[voice_id -> reference_wav_path]
    """
    from phase4_tts.src.utils import prepare_voice_references
    
    logger.info("Preparing voice references...")
    prepared = prepare_voice_references(
        voice_config_path=str(VOICE_CONFIG),
        cache_dir="phase4_tts/voice_references"
    )
    
    logger.info(f"Successfully prepared {len(prepared)}/{len(voices)} voices")
    for voice_id, path in prepared.items():
        logger.info(f"  ✓ {voice_id}: {path}")
    
    return prepared

def synthesize_with_voice(model, text: str, voice_id: str, ref_path: str, output_path: Path, config) -> Dict:
    """Synthesize chunk with specific voice and return metrics."""
    from phase4_tts.src.utils import synthesize_chunk, evaluate_mos_proxy
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing voice: {voice_id}")
    logger.info(f"Reference: {ref_path}")
    logger.info(f"{'='*60}")
    
    start_time = time.perf_counter()
    
    try:
        # Synthesize
        success, split_meta = synthesize_chunk(
            model, text, ref_path, str(output_path), config, voice_id
        )
        
        duration = time.perf_counter() - start_time
        
        if not success:
            logger.error(f"❌ Synthesis failed for {voice_id}")
            return {
                "voice_id": voice_id,
                "success": False,
                "error": "Synthesis failed",
                "duration": duration
            }
        
        # Evaluate quality
        mos = evaluate_mos_proxy(str(output_path), config.sample_rate)
        
        # Get file size
        file_size = output_path.stat().st_size if output_path.exists() else 0
        
        logger.info(f"✓ Success! MOS: {mos:.2f}, Duration: {duration:.1f}s, Size: {file_size/1024:.1f}KB")
        
        return {
            "voice_id": voice_id,
            "success": True,
            "mos_score": mos,
            "duration": duration,
            "file_size": file_size,
            "output_path": str(output_path),
            "split_metadata": split_meta
        }
        
    except Exception as e:
        logger.error(f"❌ Exception for {voice_id}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        
        return {
            "voice_id": voice_id,
            "success": False,
            "error": str(e),
            "duration": time.perf_counter() - start_time
        }

def main():
    """Main test runner."""
    # Setup
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("="*80)
    logger.info("Voice Comparison Test - Gift of the Magi")
    logger.info("="*80)
    
    # Load chunk
    try:
        text = read_chunk()
    except Exception as e:
        logger.error(f"Failed to load chunk: {e}")
        return 1
    
    # Load voice config
    try:
        voices = load_voice_config()
    except Exception as e:
        logger.error(f"Failed to load voice config: {e}")
        return 1
    
    # Prepare voices
    try:
        prepared_voices = prepare_all_voices(voices)
    except Exception as e:
        logger.error(f"Failed to prepare voices: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1
    
    if not prepared_voices:
        logger.error("No voices prepared successfully!")
        return 1
    
    # Load TTS model
    logger.info("\n" + "="*80)
    logger.info("Loading Chatterbox TTS model (CPU)...")
    logger.info("="*80)
    
    try:
        import torch
        # Ensure Chatterbox package path is importable
        sys.path.insert(0, str(Path(__file__).parent / "phase4_tts" / "Chatterbox-TTS-Extended" / "chatterbox" / "src"))
        from chatterbox.tts import ChatterboxTTS
        from phase4_tts.src.models import TTSConfig
        
        # Force CPU loading
        original_load = torch.load
        def cpu_load(*args, **kwargs):
            kwargs['map_location'] = 'cpu'
            return original_load(*args, **kwargs)
        torch.load = cpu_load
        
        model = ChatterboxTTS.from_pretrained(device="cpu")
        torch.load = original_load
        
        # Load config
        import yaml
        config_path = Path("phase4_tts/config.yaml")
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        config = TTSConfig(**config_data)
        
        logger.info("✓ Model loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1
    
    # Test each voice
    results = []
    
    logger.info("\n" + "="*80)
    logger.info(f"Testing {len(prepared_voices)} voices...")
    logger.info("="*80)
    
    for i, (voice_id, ref_path) in enumerate(prepared_voices.items(), 1):
        logger.info(f"\n[{i}/{len(prepared_voices)}] Testing {voice_id}...")
        
        output_path = OUTPUT_DIR / f"voice_test_{voice_id}.wav"
        
        result = synthesize_with_voice(
            model, text, voice_id, ref_path, output_path, config
        )
        results.append(result)
        
        # Brief pause between voices
        time.sleep(0.5)
    
    # Save results
    results_file = OUTPUT_DIR / "voice_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "chunk_path": str(CHUNK_PATH),
            "chunk_text": text,
            "total_voices": len(prepared_voices),
            "results": results
        }, f, indent=2)
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    logger.info(f"✓ Successful: {len(successful)}/{len(results)}")
    logger.info(f"✗ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        logger.info("\nSuccessful voices (sorted by MOS score):")
        sorted_results = sorted(successful, key=lambda x: x.get("mos_score", 0), reverse=True)
        for r in sorted_results:
            logger.info(f"  {r['voice_id']:20s} - MOS: {r.get('mos_score', 0):.2f}, Time: {r['duration']:.1f}s")
    
    if failed:
        logger.info("\nFailed voices:")
        for r in failed:
            logger.info(f"  {r['voice_id']:20s} - Error: {r.get('error', 'Unknown')}")
    
    logger.info(f"\nDetailed results saved to: {results_file}")
    logger.info(f"Audio files saved to: {OUTPUT_DIR}")
    logger.info("="*80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
