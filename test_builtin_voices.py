#!/usr/bin/env python3
"""
Quick test to verify built-in voice handling is working correctly.
"""

import json
import sys
from pathlib import Path

# Add phase4_tts/src to path
sys.path.insert(0, str(Path(__file__).parent / "phase4_tts" / "src"))

from main_multi_engine import build_voice_assets, select_voice


def test_builtin_voices():
    """Test that built-in voices are loaded correctly."""

    # Load voices.json
    voices_path = Path(__file__).parent / "configs" / "voices.json"
    with open(voices_path, "r", encoding="utf-8") as f:
        voices_config = json.load(f)

    # Build voice assets (no prepared refs needed for built-in voices)
    voice_assets = build_voice_assets(voices_config, prepared_refs={})

    print("=" * 80)
    print("BUILT-IN VOICE TEST RESULTS")
    print("=" * 80)
    print("\nPart 1: Testing build_voice_assets() (per-chunk overrides)")
    print("-" * 80)

    # Test cases: built-in XTTS voices
    test_voices = [
        ("alison_dietlinde", "xtts", "Alison Dietlinde"),
        ("baldur_sanjin", "xtts", "Baldur Sanjin"),
        ("af_heart", "kokoro", "af_heart"),
        ("bf_emma", "kokoro", "bf_emma"),
    ]

    errors = []

    for normalized_name, expected_engine, display_name in test_voices:
        print(f"\nTesting: {display_name} (normalized: {normalized_name})")
        print("-" * 80)

        if normalized_name not in voice_assets:
            errors.append(f"❌ FAIL: {normalized_name} not found in voice_assets")
            print(f"❌ FAIL: Not found in voice_assets")
            continue

        asset = voice_assets[normalized_name]

        # Check 1: reference_audio should be None for built-in voices
        if asset.reference_audio is not None:
            errors.append(f"FAIL: {normalized_name} has reference_audio={asset.reference_audio} (should be None)")
            print(f"[FAIL] reference_audio={asset.reference_audio} (should be None)")
        else:
            print(f"[PASS] reference_audio=None")

        # Check 2: preferred_engine should match
        if asset.preferred_engine != expected_engine:
            errors.append(f"FAIL: {normalized_name} has engine={asset.preferred_engine} (expected {expected_engine})")
            print(f"[FAIL] preferred_engine={asset.preferred_engine} (expected {expected_engine})")
        else:
            print(f"[PASS] preferred_engine={expected_engine}")

        # Check 3: engine_params should have correct speaker/voice key
        if expected_engine == "xtts":
            expected_key = "speaker"
        elif expected_engine == "kokoro":
            expected_key = "voice"

        if expected_key not in asset.engine_params:
            errors.append(f"FAIL: {normalized_name} missing '{expected_key}' in engine_params")
            print(f"[FAIL] Missing '{expected_key}' in engine_params")
        else:
            param_value = asset.engine_params[expected_key]
            print(f"[PASS] engine_params['{expected_key}']={param_value}")

        print(f"   voice_id: {asset.voice_id}")
        print(f"   engine_params: {asset.engine_params}")

    # Part 2: Test select_voice() function (default voice selection)
    print("\n" + "=" * 80)
    print("Part 2: Testing select_voice() (default voice selection)")
    print("-" * 80)

    # Test select_voice with built-in voices
    dummy_pipeline_json = Path(__file__).parent / "pipeline.json"
    test_select_voices = [
        ("baldur_sanjin", "xtts", "speaker"),
        ("alison_dietlinde", "xtts", "speaker"),
        ("af_heart", "kokoro", "voice"),
        ("bf_emma", "kokoro", "voice"),
    ]

    for voice_name, expected_engine, expected_param_key in test_select_voices:
        print(f"\nTesting select_voice('{voice_name}')")
        print("-" * 80)

        try:
            voice_id, reference_path, engine_params = select_voice(
                pipeline_json=dummy_pipeline_json,
                file_id="test_file",
                voice_override=voice_name,
                prepared_refs={},
                voices_config_path=voices_path,
                voices_config=voices_config,
            )

            # Check 1: reference_path should be None for built-in voices
            if reference_path is not None:
                errors.append(f"FAIL: select_voice({voice_name}) returned reference_path={reference_path} (should be None)")
                print(f"[FAIL] reference_path={reference_path} (should be None)")
            else:
                print(f"[PASS] reference_path=None")

            # Check 2: engine_params should have correct key
            if expected_param_key not in engine_params:
                errors.append(f"FAIL: select_voice({voice_name}) missing '{expected_param_key}' in engine_params")
                print(f"[FAIL] Missing '{expected_param_key}' in engine_params")
            else:
                param_value = engine_params[expected_param_key]
                print(f"[PASS] engine_params['{expected_param_key}']={param_value}")

            print(f"   voice_id: {voice_id}")
            print(f"   reference_path: {reference_path}")
            print(f"   engine_params: {engine_params}")

        except Exception as e:
            errors.append(f"FAIL: select_voice({voice_name}) raised exception: {e}")
            print(f"[FAIL] Exception: {e}")

    print("\n" + "=" * 80)
    if errors:
        print(f"[FAIL] TEST FAILED with {len(errors)} error(s):")
        for error in errors:
            print(f"   {error}")
        return False
    else:
        print("[PASS] ALL TESTS PASSED!")
        print("\nBuilt-in voices are now correctly configured:")
        print("  - build_voice_assets() creates VoiceAssets with reference_audio=None")
        print("  - select_voice() returns reference_path=None for built-in voices")
        print("  - Both functions set correct speaker/voice parameters")
        print("  - Will use XTTS/Kokoro built-in voices instead of cloning")
        return True


if __name__ == "__main__":
    success = test_builtin_voices()
    sys.exit(0 if success else 1)
