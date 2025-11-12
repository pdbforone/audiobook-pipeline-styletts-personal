# main_multi_engine.py - Phase 4 Multi-Engine TTS
# Why: Unified entry point supporting all TTS engines (F5, XTTS, Kokoro, StyleTTS)
# Run: python src/main_multi_engine.py --file_id book --engine f5 --json_path ../pipeline.json

import argparse
import logging
import sys
import time
import yaml
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Dict, Any, List

MODULE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_ROOT.parent.parent

# Add engines to path
sys.path.insert(0, str(MODULE_ROOT.parent))

from engines.engine_manager import EngineManager
from engines.f5_engine import F5TTSEngine
from engines.xtts_engine import XTTSEngine
from engines.kokoro_engine import KokoroEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> Dict:
    """Load YAML configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_pipeline_json(json_path: Path) -> Dict:
    """Load pipeline.json"""
    if json_path.exists():
        with open(json_path, 'r') as f:
            return json.load(f)
    return {}


def get_chunks_from_phase3(pipeline_data: Dict, file_id: str) -> List[Dict]:
    """Extract chunks from Phase 3 data"""
    if file_id not in pipeline_data:
        raise ValueError(f"File ID '{file_id}' not found in pipeline.json")

    phase3_data = pipeline_data[file_id].get("phase3", {})
    chunks = phase3_data.get("semantic_chunks", [])

    if not chunks:
        raise ValueError(f"No chunks found for file_id '{file_id}'")

    return chunks


def get_voice_id(pipeline_data: Dict, file_id: str, voice_override: str = None) -> str:
    """Get voice ID from Phase 3 or use override"""
    if voice_override:
        return voice_override

    phase3_data = pipeline_data.get(file_id, {}).get("phase3", {})
    voice_id = phase3_data.get("selected_voice", "default_voice")

    return voice_id


def get_reference_audio(voice_id: str, voices_config_path: Path) -> Path:
    """Get reference audio path for voice"""
    with open(voices_config_path, 'r') as f:
        voices_data = json.load(f)

    voice_refs = voices_data.get("voice_references", {})

    if voice_id not in voice_refs:
        raise ValueError(f"Voice '{voice_id}' not found in voice references")

    ref_path = voice_refs[voice_id].get("reference_path")
    if not ref_path:
        raise ValueError(f"No reference path for voice '{voice_id}'")

    ref_full_path = PROJECT_ROOT / ref_path
    if not ref_full_path.exists():
        raise FileNotFoundError(f"Reference audio not found: {ref_full_path}")

    return ref_full_path


def synthesize_chunk_with_engine(
    chunk_text: str,
    chunk_id: int,
    reference_audio: Path,
    engine_manager: EngineManager,
    engine_name: str,
    output_dir: Path,
    **kwargs
) -> Tuple[int, bool, str]:
    """
    Synthesize a single chunk using specified engine

    Returns:
        (chunk_id, success, output_path_or_error)
    """
    try:
        logger.info(f"[Chunk {chunk_id}] Synthesizing with {engine_name}...")

        # Synthesize
        audio = engine_manager.synthesize(
            text=chunk_text,
            reference_audio=reference_audio,
            engine=engine_name,
            fallback=True,  # Enable fallback to other engines
            **kwargs
        )

        # Save audio
        output_path = output_dir / f"chunk_{chunk_id:04d}.wav"

        # Convert to int16 for WAV
        import soundfile as sf
        audio_int16 = (audio * 32767).astype('int16')

        # Get sample rate from engine
        engine = engine_manager.get_engine(engine_name)
        sample_rate = engine.get_sample_rate()

        sf.write(output_path, audio_int16, sample_rate)

        logger.info(f"[Chunk {chunk_id}] ✓ Saved to {output_path}")
        return (chunk_id, True, str(output_path))

    except Exception as e:
        logger.error(f"[Chunk {chunk_id}] ✗ Failed: {e}")
        return (chunk_id, False, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Phase 4: Multi-Engine TTS Synthesis"
    )
    parser.add_argument("--file_id", required=True, help="File identifier")
    parser.add_argument(
        "--engine",
        default="kokoro",
        choices=["f5", "xtts", "kokoro"],
        help="TTS engine to use"
    )
    parser.add_argument("--json_path", required=True, help="Path to pipeline.json")
    parser.add_argument("--config", default="config.yaml", help="Config file")
    parser.add_argument("--voice", help="Voice ID override")
    parser.add_argument("--device", default="cpu", help="Device (cpu/cuda)")
    parser.add_argument("--workers", type=int, default=2, help="Parallel workers")

    args = parser.parse_args()

    # Resolve paths
    json_path = Path(args.json_path).resolve()
    config_path = MODULE_ROOT.parent / args.config
    voices_config = MODULE_ROOT.parent / "configs" / "voice_references.json"

    logger.info("=" * 60)
    logger.info(f"Phase 4: Multi-Engine TTS Synthesis")
    logger.info(f"Engine: {args.engine}")
    logger.info(f"Device: {args.device}")
    logger.info("=" * 60)

    # Load data
    config = load_config(config_path)
    pipeline_data = load_pipeline_json(json_path)
    chunks = get_chunks_from_phase3(pipeline_data, args.file_id)
    voice_id = get_voice_id(pipeline_data, args.file_id, args.voice)
    reference_audio = get_reference_audio(voice_id, voices_config)

    logger.info(f"Voice: {voice_id}")
    logger.info(f"Reference: {reference_audio}")
    logger.info(f"Chunks: {len(chunks)}")

    # Create output directory
    output_dir = Path(config.get("audio_chunks_dir", "audio_chunks"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize engine manager
    logger.info(f"Initializing engine manager...")
    manager = EngineManager(device=args.device)

    # Register all engines
    manager.register_engine("f5", F5TTSEngine)
    manager.register_engine("xtts", XTTSEngine)
    manager.register_engine("kokoro", KokoroEngine)

    manager.set_default_engine(args.engine)

    # List capabilities
    capabilities = manager.list_engines()
    logger.info("Available engines:")
    for name, caps in capabilities.items():
        logger.info(f"  - {name}: {caps['name']} (languages: {', '.join(caps['languages'])})")

    # Process chunks in parallel
    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                synthesize_chunk_with_engine,
                chunk["text"],
                chunk["chunk_id"],
                reference_audio,
                manager,
                args.engine,
                output_dir
            ): chunk["chunk_id"]
            for chunk in chunks
        }

        for future in as_completed(futures):
            chunk_id, success, result = future.result()
            results.append({
                "chunk_id": chunk_id,
                "success": success,
                "result": result
            })

    # Summary
    duration = time.time() - start_time
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful

    logger.info("=" * 60)
    logger.info(f"TTS Synthesis Complete")
    logger.info(f"Total: {len(chunks)}, Success: {successful}, Failed: {failed}")
    logger.info(f"Duration: {duration:.1f}s ({duration/len(chunks):.1f}s/chunk)")
    logger.info("=" * 60)

    # Update pipeline.json
    if args.file_id not in pipeline_data:
        pipeline_data[args.file_id] = {}

    pipeline_data[args.file_id]["phase4"] = {
        "status": "success" if failed == 0 else "partial",
        "engine": args.engine,
        "voice_id": voice_id,
        "chunks_processed": successful,
        "chunks_failed": failed,
        "output_dir": str(output_dir),
        "duration_seconds": duration
    }

    with open(json_path, 'w') as f:
        json.dump(pipeline_data, f, indent=2)

    logger.info(f"Updated pipeline.json")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
