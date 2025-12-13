"""
XTTS Engine Diagnostic Script
Inspects model state and tests different synthesis modes
"""

import os
import sys
import json
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from engines.xtts_engine import XTTSEngine

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def inspect_attribute(obj, attr_path, description):
    """Safely inspect a nested attribute"""
    print(f"\n{description}:")
    print(f"  Path: {attr_path}")

    try:
        parts = attr_path.split('.')
        current = obj
        for part in parts:
            current = getattr(current, part)

        print(f"  EXISTS: True")
        print(f"  Type: {type(current).__name__}")

        # Print value based on type
        if isinstance(current, bool):
            print(f"  Value: {current}")
        elif isinstance(current, (str, int, float)):
            print(f"  Value: {current}")
        elif isinstance(current, list):
            print(f"  Length: {len(current)}")
            if len(current) > 0 and len(current) <= 20:
                print(f"  Items: {current}")
            elif len(current) > 20:
                print(f"  First 10 items: {current[:10]}")
                print(f"  Last 10 items: {current[-10:]}")
        elif isinstance(current, dict):
            print(f"  Keys count: {len(current)}")
            if len(current) <= 10:
                print(f"  Keys: {list(current.keys())}")
            else:
                keys = list(current.keys())
                print(f"  First 10 keys: {keys[:10]}")
                print(f"  Last 10 keys: {keys[-10:]}")
        elif hasattr(current, '__dict__'):
            print(f"  Attributes: {list(vars(current).keys())[:10]}")
        else:
            print(f"  Value: {str(current)[:200]}")

        return current

    except AttributeError as e:
        print(f"  EXISTS: False")
        print(f"  Error: {e}")
        return None
    except Exception as e:
        print(f"  EXISTS: True (but error accessing)")
        print(f"  Error: {type(e).__name__}: {e}")
        return None

def check_file_exists(filepath, description):
    """Check if a file exists"""
    print(f"\n{description}:")
    print(f"  Path: {filepath}")
    exists = os.path.exists(filepath)
    print(f"  EXISTS: {exists}")
    if exists:
        size = os.path.getsize(filepath)
        print(f"  Size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
    return exists

def test_synthesis(engine, mode_name, active_speaker=None, ref_to_use=None):
    """Test synthesis with specific parameters"""
    print(f"\n{'-' * 80}")
    print(f"Testing: {mode_name}")
    print(f"  active_speaker={repr(active_speaker)}")
    print(f"  ref_to_use={repr(ref_to_use)}")
    print(f"{'-' * 80}")

    test_text = "This is a test of the XTTS synthesis system."

    try:
        # Try to trace which code path is taken
        print("\nAttempting synthesis...")

        # Call the synthesis method
        audio_result = engine._synthesize_single_segment(
            text=test_text,
            ref_to_use=ref_to_use,
            active_speaker=active_speaker,
            language='en',
            speed=1.0,
            temperature=0.75
        )

        print("✓ SUCCESS")
        print(f"  Audio array shape: {audio_result.shape if hasattr(audio_result, 'shape') else 'N/A'}")
        print(f"  Audio array type: {type(audio_result)}")
        if hasattr(audio_result, 'shape'):
            print(f"  Audio duration: ~{len(audio_result) / 24000:.2f}s (assuming 24kHz)")

        return True, None

    except Exception as e:
        print("✗ FAILED")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error message: {str(e)}")

        # Print traceback for more details
        import traceback
        print("\n  Traceback:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                print(f"    {line}")

        return False, e

def main():
    """Main diagnostic routine"""

    print_section("XTTS Engine Diagnostics")

    # Initialize engine
    print("\n[1] Initializing XTTS Engine...")
    try:
        engine = XTTSEngine(device='cpu')
        print("✓ Engine instance created")
    except Exception as e:
        print(f"✗ Failed to create engine: {e}")
        return

    # Load model
    print("\n[2] Loading XTTS Model...")
    try:
        engine.load_model()
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return

    print_section("MODEL ATTRIBUTE INSPECTION")

    # Inspect key attributes
    inspect_attribute(engine, 'model', 'Main model object')

    # Check multi-speaker flag
    is_multi = inspect_attribute(engine, 'model.is_multi_speaker',
                                  'is_multi_speaker flag')

    # Check speakers list
    speakers = inspect_attribute(engine, 'model.speakers',
                                  'speakers list')

    # Check speaker_manager at model level
    inspect_attribute(engine, 'model.speaker_manager',
                     'speaker_manager at model level')

    # Check synthesizer
    inspect_attribute(engine, 'model.synthesizer',
                     'synthesizer object')

    # Check TTS model
    inspect_attribute(engine, 'model.synthesizer.tts_model',
                     'TTS model inside synthesizer')

    # Check speaker_manager in TTS model
    sm = inspect_attribute(engine, 'model.synthesizer.tts_model.speaker_manager',
                           'speaker_manager in TTS model')

    # If speaker_manager exists, check name_to_id
    if sm is not None:
        inspect_attribute(engine, 'model.synthesizer.tts_model.speaker_manager.name_to_id',
                         'name_to_id mapping in speaker_manager')

    # Check TTS config
    inspect_attribute(engine, 'model.synthesizer.tts_config',
                     'TTS config object')

    # Check use_d_vector_file
    inspect_attribute(engine, 'model.synthesizer.tts_config.use_d_vector_file',
                     'use_d_vector_file flag in config')

    # Check for speakers_xtts.pth file
    print_section("FILE SYSTEM CHECKS")

    # Try to find the model directory
    model_path = None
    try:
        # XTTS models are typically stored in ~/.local/share/tts or similar
        if hasattr(engine.model, 'model_name'):
            print(f"\nModel name: {engine.model.model_name}")

        # Try to get the actual model path from the TTS object
        if hasattr(engine.model, 'model_path'):
            model_path = engine.model.model_path
        elif hasattr(engine.model, 'manager'):
            if hasattr(engine.model.manager, 'output_path'):
                model_path = engine.model.manager.output_path

        # Default TTS cache location
        import platform
        if platform.system() == 'Windows':
            default_cache = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'tts')
        else:
            default_cache = os.path.join(os.path.expanduser('~'), '.local', 'share', 'tts')

        print(f"\nDefault TTS cache location: {default_cache}")
        if os.path.exists(default_cache):
            print("  EXISTS: True")
            # Try to find XTTS model
            xtts_path = os.path.join(default_cache, 'tts_models--multilingual--multi-dataset--xtts_v2')
            if os.path.exists(xtts_path):
                model_path = xtts_path
                print(f"  Found XTTS v2 model at: {xtts_path}")
        else:
            print("  EXISTS: False")

    except Exception as e:
        print(f"Error finding model path: {e}")

    if model_path and os.path.exists(model_path):
        print(f"\n\nModel directory contents ({model_path}):")
        try:
            items = os.listdir(model_path)
            for item in sorted(items):
                full_path = os.path.join(model_path, item)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    print(f"  {item} ({size:,} bytes)")
                else:
                    print(f"  {item}/ (directory)")

            # Check for speakers_xtts.pth specifically
            speakers_file = os.path.join(model_path, 'speakers_xtts.pth')
            check_file_exists(speakers_file, '\nChecking speakers_xtts.pth')

        except Exception as e:
            print(f"  Error listing directory: {e}")
    else:
        print("\n⚠ Could not determine model directory path")

    # Synthesis tests
    print_section("SYNTHESIS MODE TESTS")

    # Find a reference audio file for testing
    reference_wav = None
    reference_search_paths = [
        "reference_audio",
        "../reference_audio",
        "audio_chunks",
    ]

    for search_path in reference_search_paths:
        if os.path.exists(search_path):
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if file.endswith('.wav'):
                        reference_wav = os.path.join(root, file)
                        break
                if reference_wav:
                    break
        if reference_wav:
            break

    if reference_wav:
        print(f"\nFound reference audio: {reference_wav}")
    else:
        print("\n⚠ No reference audio found - will skip Mode B test")

    # Test Mode A: Built-in speaker only
    result_a, error_a = test_synthesis(
        engine,
        "Mode A: Built-in speaker only",
        active_speaker="Claribel Dervla",
        ref_to_use=None
    )

    # Test Mode B: Voice cloning only (if we have reference audio)
    if reference_wav:
        result_b, error_b = test_synthesis(
            engine,
            "Mode B: Voice cloning only",
            active_speaker=None,
            ref_to_use=Path(reference_wav)
        )
    else:
        result_b, error_b = None, "No reference audio available"
        print(f"\n{'-' * 80}")
        print("Skipping Mode B: No reference audio found")
        print(f"{'-' * 80}")

    # Test Mode C: Both parameters
    if reference_wav:
        result_c, error_c = test_synthesis(
            engine,
            "Mode C: Both active_speaker and ref_to_use",
            active_speaker="Claribel Dervla",
            ref_to_use=Path(reference_wav)
        )
    else:
        result_c, error_c = None, "No reference audio available"
        print(f"\n{'-' * 80}")
        print("Skipping Mode C: No reference audio found")
        print(f"{'-' * 80}")

    # Summary
    print_section("DIAGNOSTIC SUMMARY")

    print("\nModel State:")
    print(f"  is_multi_speaker: {is_multi}")
    print(f"  Has speakers list: {speakers is not None}")
    if speakers:
        print(f"  Number of speakers: {len(speakers) if isinstance(speakers, list) else 'N/A'}")
    print(f"  Has speaker_manager: {sm is not None}")

    print("\nSynthesis Test Results:")
    print(f"  Mode A (built-in only): {'✓ SUCCESS' if result_a else '✗ FAILED'}")
    if not result_a and error_a:
        print(f"    Error: {error_a}")

    print(f"  Mode B (cloning only): {'✓ SUCCESS' if result_b else '✗ FAILED' if error_b != 'No reference audio available' else '⊘ SKIPPED'}")
    if not result_b and error_b and error_b != "No reference audio available":
        print(f"    Error: {error_b}")

    print(f"  Mode C (both params): {'✓ SUCCESS' if result_c else '✗ FAILED' if error_c != 'No reference audio available' else '⊘ SKIPPED'}")
    if not result_c and error_c and error_c != "No reference audio available":
        print(f"    Error: {error_c}")

    print("\nKey Findings:")

    # Analysis
    if is_multi is True and speakers:
        print("  • Model reports as multi-speaker with built-in voices")
    elif is_multi is False:
        print("  • Model reports as NOT multi-speaker (single speaker model)")

    if sm:
        print("  • speaker_manager exists in the model hierarchy")
    else:
        print("  • speaker_manager is NOT found in expected locations")

    if result_a and not result_b:
        print("  • Built-in speakers work, but voice cloning fails")
    elif result_b and not result_a:
        print("  • Voice cloning works, but built-in speakers fail")
    elif result_a and result_b:
        print("  • Both modes work successfully")
    elif not result_a and not result_b:
        print("  • Both modes fail - possible model loading issue")

    print("\n" + "=" * 80)
    print("Diagnostics complete!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
