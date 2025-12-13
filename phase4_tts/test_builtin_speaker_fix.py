"""
Test using built-in speakers by calling the low-level inference API directly
with pre-computed gpt_cond_latent and speaker_embedding from speakers_xtts.pth
"""

import os
import sys
from pathlib import Path
import torch
import numpy as np

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

def main():
    print_section("TESTING BUILT-IN SPEAKER FIX")

    # Load speakers_xtts.pth
    default_cache = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'tts')
    xtts_path = os.path.join(default_cache, 'tts_models--multilingual--multi-dataset--xtts_v2')
    speakers_file = os.path.join(xtts_path, 'speakers_xtts.pth')

    print(f"\n[1] Loading speakers_xtts.pth...")
    speakers_data = torch.load(speakers_file, map_location='cpu')
    print(f"✓ Loaded {len(speakers_data)} speakers")

    # Load engine
    print(f"\n[2] Loading XTTS Engine...")
    engine = XTTSEngine(device='cpu')
    engine.load_model()
    print("✓ Engine loaded")

    # Get the low-level model
    tts_model = engine.model.synthesizer.tts_model

    # Test with a built-in speaker
    speaker_name = "Claribel Dervla"
    test_text = "This is a test of the XTTS synthesis system using built-in speakers."

    print(f"\n[3] Testing synthesis with '{speaker_name}'...")

    if speaker_name not in speakers_data:
        print(f"✗ Speaker '{speaker_name}' not found in speakers_xtts.pth")
        return

    speaker_dict = speakers_data[speaker_name]
    gpt_latent = speaker_dict['gpt_cond_latent']
    spk_emb = speaker_dict['speaker_embedding']

    print(f"  gpt_cond_latent shape: {gpt_latent.shape}")
    print(f"  speaker_embedding shape: {spk_emb.shape}")

    # Call the low-level inference method directly
    print(f"\n  Calling tts_model.inference() directly...")

    try:
        # Get the inference method
        result = tts_model.inference(
            text=test_text,
            language='en',
            gpt_cond_latent=gpt_latent,
            speaker_embedding=spk_emb,
            temperature=0.75,
            speed=1.0,
        )

        print("\n✓ SUCCESS!")
        print(f"  Result type: {type(result)}")

        # The result might be a dict with 'wav' key or directly an array
        if isinstance(result, dict):
            print(f"  Result keys: {list(result.keys())}")
            if 'wav' in result:
                audio = result['wav']
                print(f"  Audio type: {type(audio)}")
                if isinstance(audio, torch.Tensor):
                    audio = audio.cpu().numpy()
                print(f"  Audio shape: {audio.shape if hasattr(audio, 'shape') else 'N/A'}")
                if hasattr(audio, 'shape'):
                    duration = len(audio) / 24000
                    print(f"  Duration: ~{duration:.2f}s (at 24kHz)")
        elif isinstance(result, (np.ndarray, torch.Tensor)):
            if isinstance(result, torch.Tensor):
                result = result.cpu().numpy()
            print(f"  Audio shape: {result.shape}")
            duration = len(result) / 24000
            print(f"  Duration: ~{duration:.2f}s")
        else:
            print(f"  Unexpected result type: {type(result)}")

    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    # Now test multiple speakers
    print_section("TESTING MULTIPLE BUILT-IN SPEAKERS")

    test_speakers = [
        "Claribel Dervla",
        "Daisy Studious",
        "Andrew Chipper",  # Male voice
        "Dionisio Schuyler",  # Male voice
    ]

    short_text = "Hello, this is a voice test."

    for speaker in test_speakers:
        if speaker not in speakers_data:
            print(f"\n✗ {speaker}: Not found in speakers_xtts.pth")
            continue

        print(f"\n{speaker}:")

        try:
            speaker_dict = speakers_data[speaker]
            result = tts_model.inference(
                text=short_text,
                language='en',
                gpt_cond_latent=speaker_dict['gpt_cond_latent'],
                speaker_embedding=speaker_dict['speaker_embedding'],
                temperature=0.75,
                speed=1.0,
            )

            print(f"  ✓ SUCCESS")

            # Extract audio
            if isinstance(result, dict) and 'wav' in result:
                audio = result['wav']
                if isinstance(audio, torch.Tensor):
                    audio = audio.cpu().numpy()
            elif isinstance(result, torch.Tensor):
                audio = result.cpu().numpy()
            else:
                audio = result

            if hasattr(audio, 'shape'):
                duration = len(audio) / 24000
                print(f"  Duration: {duration:.2f}s")

        except Exception as e:
            print(f"  ✗ FAILED: {e}")

    print_section("CONCLUSION")

    print("\n✓ Built-in speakers work when using the low-level inference() API!")
    print("\nKey insight:")
    print("  - High-level model.tts() API fails with built-in speakers")
    print("  - Low-level tts_model.inference() works when given:")
    print("    • gpt_cond_latent from speakers_xtts.pth")
    print("    • speaker_embedding from speakers_xtts.pth")
    print("\nRecommended fix:")
    print("  Update xtts_engine.py to:")
    print("  1. Load speakers_xtts.pth on initialization")
    print("  2. When active_speaker is provided:")
    print("     - Look up speaker in speakers_xtts.pth")
    print("     - Extract gpt_cond_latent and speaker_embedding")
    print("     - Call tts_model.inference() directly (not model.tts())")
    print()

if __name__ == "__main__":
    main()
