"""
Check the actual XTTS API signature
"""

import inspect
from TTS.api import TTS

# Load model
model = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    progress_bar=False,
    gpu=False
)

# Check the tts() method signature
print("=" * 80)
print("TTS.tts() method signature:")
print("=" * 80)
sig = inspect.signature(model.tts)
print(sig)
print()

print("Parameters:")
for param_name, param in sig.parameters.items():
    default = param.default
    if default == inspect.Parameter.empty:
        default_str = "(required)"
    else:
        default_str = f"= {repr(default)}"
    print(f"  {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'} {default_str}")

# Also check if there's a separate method for multi-speaker
print("\n" + "=" * 80)
print("Available methods on TTS object:")
print("=" * 80)
methods = [m for m in dir(model) if not m.startswith('_') and callable(getattr(model, m))]
for method in methods:
    print(f"  {method}")

# Check synthesizer.tts method
print("\n" + "=" * 80)
print("Synthesizer.tts() method signature:")
print("=" * 80)
sig2 = inspect.signature(model.synthesizer.tts)
print(sig2)
print()

print("Parameters:")
for param_name, param in sig2.parameters.items():
    default = param.default
    if default == inspect.Parameter.empty:
        default_str = "(required)"
    else:
        default_str = f"= {repr(default)}"
    print(f"  {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'} {default_str}")
