#!/usr/bin/env python3
"""
Generate voice samples for all available TTS voices.

Usage:
    python tools/generate_voice_samples.py                    # All voices
    python tools/generate_voice_samples.py --engine xtts      # Only XTTS voices
    python tools/generate_voice_samples.py --engine kokoro    # Only Kokoro voices
    python tools/generate_voice_samples.py --builtin-only     # Only built-in voices
    python tools/generate_voice_samples.py --custom-only      # Only custom voices
    python tools/generate_voice_samples.py --voice "Claribel Dervla"  # Specific voice
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Engine virtual environment paths
ENGINE_ENV_ROOT = PROJECT_ROOT / "phase4_tts" / ".engine_envs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Short, complex poetry sample - tests punctuation, emotion, pacing
SAMPLE_TEXT = """Do not go gentle into that good night.
Rage, rage against the dying of the light.
Though wise men at their end know dark is right,
Because their words had forked no lightning they
Do not go gentle into that good night."""

VOICE_CONFIG_PATH = PROJECT_ROOT / "phase4_tts" / "configs" / "voice_references.json"
OUTPUT_DIR = PROJECT_ROOT / "voice_samples" / "previews"


def get_engine_python(engine: str) -> Path:
    """Get the Python executable for an engine's virtual environment."""
    env_dir = ENGINE_ENV_ROOT / engine
    if os.name == "nt":
        python_path = env_dir / "Scripts" / "python.exe"
    else:
        python_path = env_dir / "bin" / "python"
    return python_path


def load_voice_config():
    """Load voice configuration."""
    with open(VOICE_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_voices_to_sample(config, args):
    """Get list of voices to sample based on filters."""
    voices = []

    # Custom voice references
    if not args.builtin_only:
        for voice_id, data in config.get("voice_references", {}).items():
            if args.voice and args.voice.lower() != voice_id.lower():
                continue
            voices.append({
                "voice_id": voice_id,
                "engine": "xtts",  # Custom voices use XTTS for cloning
                "built_in": False,
                "local_path": data.get("local_path"),
                "narrator_name": data.get("narrator_name", voice_id),
            })

    # Built-in voices
    if not args.custom_only:
        for engine_name, engine_voices in config.get("built_in_voices", {}).items():
            if args.engine and args.engine.lower() != engine_name.lower():
                continue
            for voice_name, data in engine_voices.items():
                if args.voice and args.voice.lower() != voice_name.lower():
                    continue
                voices.append({
                    "voice_id": voice_name,
                    "engine": engine_name,
                    "built_in": True,
                    "local_path": None,
                    "narrator_name": voice_name,
                    "gender": data.get("gender"),
                    "accent": data.get("accent"),
                })

    return voices


def synthesize_with_xtts(text: str, voice_id: str, output_path: Path, reference_audio: Path = None):
    """Synthesize using XTTS engine."""
    try:
        from TTS.api import TTS
        import soundfile as sf
        import numpy as np

        logger.info(f"Loading XTTS model...")
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False, gpu=False)

        if reference_audio and reference_audio.exists():
            logger.info(f"Using voice clone from: {reference_audio}")
            wav = tts.tts(text=text, speaker_wav=str(reference_audio), language="en")
        else:
            logger.info(f"Using built-in speaker: {voice_id}")
            wav = tts.tts(text=text, speaker=voice_id, language="en")

        audio = np.array(wav, dtype=np.float32)
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio)) * 0.95

        sf.write(str(output_path), audio, 24000)
        return True
    except Exception as e:
        logger.error(f"XTTS synthesis failed: {e}")
        return False


def synthesize_with_kokoro(text: str, voice_id: str, output_path: Path):
    """Synthesize using Kokoro engine."""
    try:
        import soundfile as sf

        # Try to import kokoro
        kokoro_path = PROJECT_ROOT / "phase4_tts" / ".engine_envs" / "kokoro"
        if kokoro_path.exists():
            sys.path.insert(0, str(kokoro_path))

        from kokoro import KPipeline

        logger.info(f"Loading Kokoro model with voice: {voice_id}")
        pipeline = KPipeline(lang_code="a")

        generator = pipeline(text, voice=voice_id, speed=1.0)
        audio_chunks = []
        for _, _, audio in generator:
            audio_chunks.append(audio)

        if audio_chunks:
            import numpy as np
            full_audio = np.concatenate(audio_chunks)
            sf.write(str(output_path), full_audio, 24000)
            return True
        return False
    except Exception as e:
        logger.error(f"Kokoro synthesis failed: {e}")
        return False


def generate_samples(voices: list, output_dir: Path, text: str):
    """Generate samples for all voices."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(voices)

    # Group by engine to minimize model reloading
    xtts_voices = [v for v in voices if v["engine"] == "xtts"]
    kokoro_voices = [v for v in voices if v["engine"] == "kokoro"]

    # Process XTTS voices using venv subprocess
    if xtts_voices:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {len(xtts_voices)} XTTS voices...")
        logger.info(f"{'='*60}\n")

        xtts_python = get_engine_python("xtts")
        if not xtts_python.exists():
            logger.error(f"XTTS venv not found at {xtts_python}")
            logger.error("Run: python phase4_tts/engine_runner.py --engine xtts --file_id test --json_path pipeline.json")
            logger.error("to set up the XTTS environment first.")
            for voice in xtts_voices:
                results.append({"voice": voice["voice_id"], "engine": "xtts", "status": "skipped", "error": "XTTS venv not setup"})
        else:
            # Create a subprocess script to run XTTS synthesis
            for i, voice in enumerate(xtts_voices, 1):
                voice_id = voice["voice_id"]
                safe_name = voice_id.replace(" ", "_").replace("/", "_")
                output_path = output_dir / f"xtts_{safe_name}.wav"

                logger.info(f"[{i}/{len(xtts_voices)}] Generating: {voice_id}")

                # Build inline Python code for subprocess
                if voice["built_in"]:
                    synth_code = f'''
import sys
sys.path.insert(0, r"{PROJECT_ROOT}")
from TTS.api import TTS
import soundfile as sf
import numpy as np

tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False, gpu=False)
wav = tts.tts(text="""{text.replace('"', '\\"')}""", speaker="{voice_id}", language="en")
audio = np.array(wav, dtype=np.float32)
if np.max(np.abs(audio)) > 0:
    audio = audio / np.max(np.abs(audio)) * 0.95
sf.write(r"{output_path}", audio, 24000)
print("SUCCESS")
'''
                else:
                    ref_path = PROJECT_ROOT / voice.get("local_path", "")
                    if not ref_path.exists():
                        logger.warning(f"  Reference not found: {ref_path}")
                        results.append({"voice": voice_id, "engine": "xtts", "status": "failed", "error": "Reference not found"})
                        continue
                    synth_code = f'''
import sys
sys.path.insert(0, r"{PROJECT_ROOT}")
from TTS.api import TTS
import soundfile as sf
import numpy as np

tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False, gpu=False)
wav = tts.tts(text="""{text.replace('"', '\\"')}""", speaker_wav=r"{ref_path}", language="en")
audio = np.array(wav, dtype=np.float32)
if np.max(np.abs(audio)) > 0:
    audio = audio / np.max(np.abs(audio)) * 0.95
sf.write(r"{output_path}", audio, 24000)
print("SUCCESS")
'''

                try:
                    result = subprocess.run(
                        [str(xtts_python), "-c", synth_code],
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5 min timeout per voice
                        cwd=str(PROJECT_ROOT),
                    )
                    if result.returncode == 0 and "SUCCESS" in result.stdout:
                        logger.info(f"  Saved: {output_path.name}")
                        results.append({"voice": voice_id, "engine": "xtts", "status": "success", "path": str(output_path)})
                    else:
                        error = result.stderr or result.stdout or "Unknown error"
                        logger.error(f"  Failed: {error[:200]}")
                        results.append({"voice": voice_id, "engine": "xtts", "status": "failed", "error": error[:500]})
                except subprocess.TimeoutExpired:
                    logger.error(f"  Timeout after 5 minutes")
                    results.append({"voice": voice_id, "engine": "xtts", "status": "failed", "error": "Timeout"})
                except Exception as e:
                    logger.error(f"  Failed: {e}")
                    results.append({"voice": voice_id, "engine": "xtts", "status": "failed", "error": str(e)})

    # Process Kokoro voices
    if kokoro_voices:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {len(kokoro_voices)} Kokoro voices...")
        logger.info(f"{'='*60}\n")

        try:
            import soundfile as sf
            import numpy as np
            from kokoro import KPipeline

            logger.info("Loading Kokoro model (one-time)...")
            pipeline = KPipeline(lang_code="a")

            for i, voice in enumerate(kokoro_voices, 1):
                voice_id = voice["voice_id"]
                safe_name = voice_id.replace(" ", "_").replace("/", "_")
                output_path = output_dir / f"kokoro_{safe_name}.wav"

                logger.info(f"[{i}/{len(kokoro_voices)}] Generating: {voice_id}")

                try:
                    generator = pipeline(text, voice=voice_id, speed=1.0)
                    audio_chunks = []
                    for _, _, audio in generator:
                        audio_chunks.append(audio)

                    if audio_chunks:
                        full_audio = np.concatenate(audio_chunks)
                        sf.write(str(output_path), full_audio, 24000)
                        logger.info(f"  Saved: {output_path.name}")
                        results.append({"voice": voice_id, "engine": "kokoro", "status": "success", "path": str(output_path)})
                    else:
                        results.append({"voice": voice_id, "engine": "kokoro", "status": "failed", "error": "No audio generated"})

                except Exception as e:
                    logger.error(f"  Failed: {e}")
                    results.append({"voice": voice_id, "engine": "kokoro", "status": "failed", "error": str(e)})

        except ImportError as e:
            logger.error(f"Kokoro not available: {e}")
            for voice in kokoro_voices:
                results.append({"voice": voice["voice_id"], "engine": "kokoro", "status": "skipped", "error": "Kokoro not installed"})

    return results


def main():
    parser = argparse.ArgumentParser(description="Generate voice samples for all TTS voices")
    parser.add_argument("--engine", choices=["xtts", "kokoro"], help="Filter by engine")
    parser.add_argument("--builtin-only", action="store_true", help="Only built-in voices")
    parser.add_argument("--custom-only", action="store_true", help="Only custom voices")
    parser.add_argument("--voice", help="Generate sample for specific voice only")
    parser.add_argument("--text", help="Custom text to synthesize (default: Dylan Thomas poetry)")
    parser.add_argument("--output", type=Path, help="Output directory")

    args = parser.parse_args()

    config = load_voice_config()
    voices = get_voices_to_sample(config, args)

    if not voices:
        logger.error("No voices found matching criteria")
        return 1

    logger.info(f"Found {len(voices)} voices to sample")

    text = args.text or SAMPLE_TEXT
    output_dir = args.output or OUTPUT_DIR

    logger.info(f"\nSample text:\n{'-'*40}\n{text}\n{'-'*40}\n")
    logger.info(f"Output directory: {output_dir}\n")

    results = generate_samples(voices, output_dir, text)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total: {len(results)} | Success: {success} | Failed: {failed} | Skipped: {skipped}")
    logger.info(f"Samples saved to: {output_dir}")

    # Save results JSON
    results_path = output_dir / f"sample_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({"text": text, "timestamp": datetime.now().isoformat(), "results": results}, f, indent=2)
    logger.info(f"Results saved to: {results_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
