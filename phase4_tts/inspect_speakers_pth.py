"""
Inspect speakers_xtts.pth structure and test direct inference API
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

def inspect_tensor(name, tensor):
    """Print information about a tensor"""
    print(f"\n{name}:")
    print(f"  Type: {type(tensor)}")
    if isinstance(tensor, torch.Tensor):
        print(f"  Shape: {tensor.shape}")
        print(f"  Dtype: {tensor.dtype}")
        print(f"  Device: {tensor.device}")
        print(f"  Min/Max: {tensor.min().item():.4f} / {tensor.max().item():.4f}")
    elif isinstance(tensor, np.ndarray):
        print(f"  Shape: {tensor.shape}")
        print(f"  Dtype: {tensor.dtype}")
    else:
        print(f"  Value: {str(tensor)[:200]}")

def main():
    print_section("SPEAKERS_XTTS.PTH INSPECTION")

    # Find the speakers file
    default_cache = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'tts')
    xtts_path = os.path.join(default_cache, 'tts_models--multilingual--multi-dataset--xtts_v2')
    speakers_file = os.path.join(xtts_path, 'speakers_xtts.pth')

    print(f"\nLoading: {speakers_file}")

    try:
        speakers_data = torch.load(speakers_file, map_location='cpu')
        print(f"✓ Loaded successfully")
        print(f"  Type: {type(speakers_data)}")

        if isinstance(speakers_data, dict):
            print(f"  Keys: {list(speakers_data.keys())[:20]}")
            print(f"  Total speakers: {len(speakers_data)}")

            # Inspect one speaker in detail
            test_speaker = "Claribel Dervla"
            if test_speaker in speakers_data:
                print(f"\n{'=' * 80}")
                print(f"  Detailed inspection of '{test_speaker}'")
                print(f"{'=' * 80}")

                speaker_obj = speakers_data[test_speaker]
                print(f"\nSpeaker object type: {type(speaker_obj)}")

                if isinstance(speaker_obj, dict):
                    print(f"Keys in speaker dict: {list(speaker_obj.keys())}")
                    for key, value in speaker_obj.items():
                        inspect_tensor(f"  {key}", value)
                elif isinstance(speaker_obj, torch.Tensor):
                    inspect_tensor("Speaker tensor", speaker_obj)
                else:
                    print(f"Unexpected type: {type(speaker_obj)}")
                    print(f"Value: {speaker_obj}")
            else:
                print(f"\n⚠ '{test_speaker}' not found in speakers_data")
                print(f"Available speakers: {list(speakers_data.keys())[:10]}")
        else:
            print(f"  Unexpected data type: {type(speakers_data)}")

    except Exception as e:
        print(f"✗ Failed to load speakers file: {e}")
        import traceback
        traceback.print_exc()
        return

    # Now test direct inference
    print_section("TESTING DIRECT INFERENCE API")

    print("\n[1] Loading XTTS Engine...")
    try:
        engine = XTTSEngine(device='cpu')
        engine.load_model()
        print("✓ Engine loaded")
    except Exception as e:
        print(f"✗ Failed to load engine: {e}")
        return

    # Check what's in speaker_manager
    print("\n[2] Inspecting speaker_manager...")
    try:
        sm = engine.model.synthesizer.tts_model.speaker_manager
        print(f"Speaker manager type: {type(sm)}")
        print(f"Attributes: {dir(sm)}")

        # Check embeddings
        if hasattr(sm, 'embeddings'):
            print(f"\nEmbeddings type: {type(sm.embeddings)}")
            if isinstance(sm.embeddings, torch.Tensor):
                print(f"Embeddings shape: {sm.embeddings.shape}")
            elif isinstance(sm.embeddings, dict):
                print(f"Embeddings keys: {list(sm.embeddings.keys())[:10]}")

        # Check embeddings_by_names
        if hasattr(sm, 'embeddings_by_names'):
            print(f"\nEmbeddings by names type: {type(sm.embeddings_by_names)}")
            if isinstance(sm.embeddings_by_names, dict):
                print(f"Count: {len(sm.embeddings_by_names)}")
                print(f"Keys: {list(sm.embeddings_by_names.keys())[:10]}")

                # Inspect one embedding
                if "Claribel Dervla" in sm.embeddings_by_names:
                    emb = sm.embeddings_by_names["Claribel Dervla"]
                    inspect_tensor("Claribel Dervla embedding", emb)

        # Check name_to_id
        if hasattr(sm, 'name_to_id'):
            print(f"\nName to ID mapping:")
            print(f"  Type: {type(sm.name_to_id)}")
            if isinstance(sm.name_to_id, dict):
                print(f"  Count: {len(sm.name_to_id)}")
                # Show first few mappings
                for i, (name, idx) in enumerate(list(sm.name_to_id.items())[:5]):
                    print(f"  '{name}' -> {idx}")

    except Exception as e:
        print(f"✗ Error inspecting speaker_manager: {e}")
        import traceback
        traceback.print_exc()

    # Test getting speaker embedding
    print("\n[3] Testing speaker embedding retrieval...")
    try:
        speaker_name = "Claribel Dervla"

        # Try different methods to get the embedding
        methods_tested = []

        # Method 1: embeddings_by_names
        if hasattr(sm, 'embeddings_by_names') and speaker_name in sm.embeddings_by_names:
            emb1 = sm.embeddings_by_names[speaker_name]
            print(f"\n✓ Method 1 (embeddings_by_names): SUCCESS")
            inspect_tensor("  Embedding", emb1)
            methods_tested.append(('embeddings_by_names', emb1))
        else:
            print(f"\n✗ Method 1 (embeddings_by_names): NOT AVAILABLE")

        # Method 2: name_to_id + embeddings array
        if hasattr(sm, 'name_to_id') and hasattr(sm, 'embeddings'):
            if speaker_name in sm.name_to_id:
                idx = sm.name_to_id[speaker_name]
                if isinstance(sm.embeddings, torch.Tensor):
                    emb2 = sm.embeddings[idx]
                    print(f"\n✓ Method 2 (name_to_id + embeddings[{idx}]): SUCCESS")
                    inspect_tensor("  Embedding", emb2)
                    methods_tested.append(('indexed_embeddings', emb2))
                else:
                    print(f"\n✗ Method 2: embeddings is not a tensor")
            else:
                print(f"\n✗ Method 2: speaker not in name_to_id")

        # Method 3: Check if there's a get_embedding method
        if hasattr(sm, 'get_embedding'):
            try:
                emb3 = sm.get_embedding(speaker_name)
                print(f"\n✓ Method 3 (get_embedding): SUCCESS")
                inspect_tensor("  Embedding", emb3)
                methods_tested.append(('get_embedding', emb3))
            except Exception as e:
                print(f"\n✗ Method 3 (get_embedding): {e}")

        if not methods_tested:
            print("\n⚠ No methods succeeded in retrieving speaker embedding")
            return

    except Exception as e:
        print(f"✗ Error retrieving speaker embedding: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test direct inference with speaker embedding
    print_section("TESTING DIRECT MODEL INFERENCE")

    test_text = "This is a test of direct XTTS inference with built-in speaker embeddings."

    print(f"\n[4] Testing model.synthesizer.tts_model.inference()...")
    try:
        tts_model = engine.model.synthesizer.tts_model

        # Check what methods are available
        print("\nAvailable methods on tts_model:")
        methods = [m for m in dir(tts_model) if not m.startswith('_') and callable(getattr(tts_model, m))]
        for m in methods[:20]:
            print(f"  - {m}")

        # Try inference method
        if hasattr(tts_model, 'inference'):
            print("\n✓ tts_model.inference() method exists")

            # Get the signature
            import inspect
            sig = inspect.signature(tts_model.inference)
            print(f"Signature: {sig}")

            # Try to call it with speaker embedding
            # Note: We might need gpt_cond_latent too
            print("\n  Attempting inference with speaker embedding...")

            # We need to check if speakers_xtts.pth has the gpt_cond_latent
            if test_speaker in speakers_data and isinstance(speakers_data[test_speaker], dict):
                speaker_dict = speakers_data[test_speaker]

                if 'gpt_cond_latent' in speaker_dict and 'speaker_embedding' in speaker_dict:
                    print("\n  ✓ Found both gpt_cond_latent and speaker_embedding in speakers_xtts.pth")

                    gpt_latent = speaker_dict['gpt_cond_latent']
                    spk_emb = speaker_dict['speaker_embedding']

                    inspect_tensor("  gpt_cond_latent", gpt_latent)
                    inspect_tensor("  speaker_embedding", spk_emb)

                    # Try to use these for synthesis
                    print("\n  Attempting synthesis with pre-computed latents...")
                    try:
                        # Call high-level API with these latents if possible
                        # Or try the low-level inference

                        # First check if model.tts accepts gpt_cond_latent
                        result = engine.model.tts(
                            text=test_text,
                            language='en',
                            gpt_cond_latent=gpt_latent,
                            speaker_embedding=spk_emb
                        )

                        print("\n  ✓ SUCCESS with gpt_cond_latent + speaker_embedding!")
                        print(f"    Result type: {type(result)}")
                        if isinstance(result, np.ndarray):
                            print(f"    Audio shape: {result.shape}")
                            print(f"    Duration: ~{len(result) / 24000:.2f}s")

                    except Exception as e:
                        print(f"\n  ✗ Synthesis failed: {e}")
                        print("\n  Trying alternative approach...")

                        # Try calling inference_with_config or full_inference directly
                        try:
                            result2 = tts_model.full_inference(
                                text=test_text,
                                ref_audio_path=None,
                                language='en',
                                gpt_cond_latent=gpt_latent,
                                speaker_embedding=spk_emb
                            )
                            print("\n  ✓ SUCCESS with full_inference!")
                            print(f"    Result type: {type(result2)}")
                        except Exception as e2:
                            print(f"\n  ✗ full_inference also failed: {e2}")
                            import traceback
                            traceback.print_exc()
                else:
                    print(f"\n  ✗ speakers_xtts.pth missing required keys")
                    print(f"    Available keys: {list(speaker_dict.keys()) if isinstance(speaker_dict, dict) else 'N/A'}")
            else:
                print(f"\n  ✗ Could not find speaker data in speakers_xtts.pth")

        else:
            print("\n✗ tts_model.inference() method not found")

    except Exception as e:
        print(f"✗ Error during direct inference test: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Inspection complete!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
