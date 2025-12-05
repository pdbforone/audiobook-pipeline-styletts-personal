"""Test XTTS built-in voice synthesis"""
import sys
sys.path.insert(0, 'phase4_tts')

from pathlib import Path
from phase4_tts.engines.xtts_engine import XTTSEngine

# Test built-in voice with speaker parameter
engine = XTTSEngine(device="cpu")
engine.load_model()

print("Testing XTTS with built-in voice 'Claribel Dervla'...")
try:
    audio = engine.synthesize(
        text="This is a test of the built-in voice system.",
        reference_audio=None,  # No reference for built-in
        language="en",
        speaker="Claribel Dervla"  # Built-in speaker name
    )
    print(f"✅ Success! Generated {len(audio)} audio samples")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nTesting XTTS with built-in voice 'Baldur Sanjin'...")
try:
    audio = engine.synthesize(
        text="This is a test of Baldur Sanjin's voice.",
        reference_audio=None,
        language="en",
        speaker="Baldur Sanjin"
    )
    print(f"✅ Success! Generated {len(audio)} audio samples")
except Exception as e:
    print(f"❌ Error: {e}")
