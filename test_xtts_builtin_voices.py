#!/usr/bin/env python3
"""
Test XTTS Built-in Voices

This script tests Phase 4 with different XTTS built-in voices to verify:
1. Voice parameter is correctly passed to XTTS engine
2. Single-speaker vs multi-speaker model handling
3. Audio output is generated successfully

Usage:
    python test_xtts_builtin_voices.py

Output:
    - Audio files in phase4_tts/audio_chunks/test_xtts_voices/
    - Test results printed to console
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Test configuration
TEST_FILE_ID = "test_xtts_voices"
PIPELINE_JSON = Path("c:/Users/myson/Pipeline/audiobook-pipeline-personal/pipeline.json")
PHASE4_DIR = Path("phase4_tts")
OUTPUT_DIR = PHASE4_DIR / "audio_chunks" / TEST_FILE_ID

# XTTS built-in voices to test (representative sample)
TEST_VOICES = [
    "Claribel Dervla",      # Female, clear
    "Daisy Studious",       # Female, young
    "Gracie Wise",          # Female, older
    "Tammie Ema",           # Female, energetic
    "Alison Dietlinde",     # Female, calm
    "Viktor Eka",           # Male, deep
    "Baldur Sanjin",        # Male, authoritative
    "Abrahan Mack",         # Male, warm
    "Adde Michal",          # Male, young
]


def check_prerequisites() -> bool:
    """Check that Phase 3 has completed successfully."""
    if not PIPELINE_JSON.exists():
        print(f"❌ Pipeline JSON not found: {PIPELINE_JSON}")
        return False

    data = json.load(open(PIPELINE_JSON))
    phase3 = data.get("phase3", {}).get("files", {}).get(TEST_FILE_ID, {})

    if phase3.get("status") != "completed":
        print(f"❌ Phase 3 not completed for {TEST_FILE_ID}")
        print(f"   Status: {phase3.get('status', 'unknown')}")
        print(f"\n   Run this first:")
        print(f"   python phase6_orchestrator/orchestrator.py test_xtts_voices.txt --phases 1 2 3 --no-resume")
        return False

    # Get chunk ids
    chunk_ids = phase3.get("chunk_ids") or [
        c.get("chunk_id") for c in phase3.get("chunks", []) if isinstance(c, dict)
    ]
    chunk_ids = [c for c in chunk_ids if c]
    print(f"✓ Phase 3 completed: {len(chunk_ids)} chunks available")
    return True


def normalize_voice_name(voice: str) -> str:
    """Convert 'Claribel Dervla' to 'claribel_dervla' for CLI."""
    return voice.lower().replace(' ', '_')


def run_phase4_for_voice(voice: str, chunk_id: str = "chunk_0001") -> Tuple[bool, str]:
    """
    Run Phase 4 for a single voice on a specific chunk.

    Returns:
        (success, error_message)
    """
    voice_normalized = normalize_voice_name(voice)

    print(f"\n{'='*60}")
    print(f"Testing voice: {voice}")
    print(f"  Normalized: {voice_normalized}")
    print(f"  Chunk: {chunk_id}")
    print(f"{'='*60}")

    # Construct Phase 4 command
    chunk_num = max(int(chunk_id.replace("chunk_", "")) - 1, 0)

    cmd = [
        "python",
        "phase4_tts/engine_runner.py",
        "--engine", "xtts",
        "--file_id", TEST_FILE_ID,
        "--json_path", str(PIPELINE_JSON),
        "--disable_fallback",
        "--device", "cpu",
        "--workers", "1",
        "--voice", voice_normalized,
        "--chunk_id", str(chunk_num),
    ]

    print(f"\nCommand: {' '.join(cmd)}")
    print(f"\nRunning Phase 4...", end="", flush=True)

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutes timeout per chunk
            env=env,
        )

        print(" Done!")

        # Check output
        if result.returncode == 0:
            # Verify audio file exists
            expected_audio = OUTPUT_DIR / f"{chunk_id}.wav"
            if expected_audio.exists():
                size_kb = expected_audio.stat().st_size / 1024
                print(f"✓ Success! Audio generated: {expected_audio.name} ({size_kb:.1f} KB)")

                # Check logs for voice usage
                if "Using built-in XTTS speaker:" in result.stderr:
                    print(f"  ✓ Used built-in speaker (multi-speaker model)")
                elif "single-speaker" in result.stderr.lower():
                    print(f"  ⚠ Single-speaker model detected - used voice cloning fallback")
                elif "Using voice cloning" in result.stderr:
                    print(f"  ⚠ Voice cloning used (fallback)")

                return True, ""
            else:
                error = f"Audio file not created: {expected_audio}"
                print(f"❌ {error}")
                return False, error
        else:
            error = f"Exit code {result.returncode}"
            print(f"❌ Failed: {error}")
            print(f"\nSTDERR:\n{result.stderr[:500]}")
            return False, error

    except subprocess.TimeoutExpired:
        error = "Timeout (>3 minutes)"
        print(f" ❌ {error}")
        return False, error
    except Exception as e:
        error = str(e)
        print(f" ❌ {error}")
        return False, error


def main():
    """Run the voice test suite."""
    print("="*70)
    print("XTTS Built-in Voice Test Suite")
    print("="*70)

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Clean output directory
    if OUTPUT_DIR.exists():
        print(f"\n🗑️  Cleaning previous test output: {OUTPUT_DIR}")
        for f in OUTPUT_DIR.glob("*.wav"):
            f.unlink()

    # Run tests
    results = []
    print(f"\n🎤 Testing {len(TEST_VOICES)} voices...")

    for voice in TEST_VOICES:
        success, error = run_phase4_for_voice(voice)
        results.append({
            "voice": voice,
            "success": success,
            "error": error,
        })

    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\n✓ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"  - {r['voice']}")

    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(results)}")
        for r in failed:
            print(f"  - {r['voice']}: {r['error']}")

    # Check audio files
    if OUTPUT_DIR.exists():
        audio_files = list(OUTPUT_DIR.glob("*.wav"))
        print(f"\n📁 Audio files generated: {len(audio_files)}")
        print(f"   Location: {OUTPUT_DIR}")

        if audio_files:
            print(f"\n   Sample files:")
            for f in sorted(audio_files)[:5]:
                size_kb = f.stat().st_size / 1024
                print(f"   - {f.name} ({size_kb:.1f} KB)")

    # Exit code
    if failed:
        print(f"\n⚠️  Some tests failed. Check logs above for details.")
        sys.exit(1)
    else:
        print(f"\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
