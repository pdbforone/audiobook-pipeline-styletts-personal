import json
from pathlib import Path

# Show where we're running from
print("Current working directory:", Path.cwd())
print("Script location:", Path(__file__).resolve().parent)
print()

# Check if Phase 5's input_dir resolves correctly from here
phase5_dir = Path(__file__).resolve().parent.parent / "phase5_enhancement"
config_input_dir = Path("../phase4_tts/audio_chunks")

print("Phase 5 directory:", phase5_dir)
print("Config input_dir (relative):", config_input_dir)

# Resolve from phase5_enhancement directory
resolved_from_phase5 = (phase5_dir / config_input_dir).resolve()
print("Resolved from phase5_enhancement:", resolved_from_phase5)
print("Exists:", resolved_from_phase5.exists())
print()

if resolved_from_phase5.exists():
    files = list(resolved_from_phase5.glob("*.wav"))
    print(f"Found {len(files)} WAV files in that directory")
else:
    print("ERROR: Directory does not exist!")

# Check what Phase 5's main.py actually does with the path
print()
print("=" * 60)
print("SIMULATING Phase 5 path resolution:")
print("=" * 60)

# Read first chunk path from pipeline.json
with open("../pipeline.json", "r") as f:
    data = json.load(f)

phase4 = data["phase4"]["files"]["The_Analects_of_Confucius_20240228"]
first_chunk_path = phase4["chunk_audio_paths"][0]

print(f"First chunk from pipeline.json: {first_chunk_path}")
print(f"Is absolute: {Path(first_chunk_path).is_absolute()}")

# What Phase 5 actually does (from main.py line 360):
filename = Path(first_chunk_path).name
print(f"Extracted filename: {filename}")

# Combine with input_dir
combined = Path("../phase4_tts/audio_chunks") / filename
print(f"Combined path: {combined}")
print(f"Resolves to: {combined.resolve()}")
print(f"Exists: {combined.exists()}")
