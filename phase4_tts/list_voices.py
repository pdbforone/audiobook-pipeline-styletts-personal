"""List all available voices for XTTS and Kokoro engines.

Usage:
    python list_voices.py              # List all voices
    python list_voices.py --engine xtts    # List only XTTS voices
    python list_voices.py --engine kokoro  # List only Kokoro voices
    python list_voices.py --profile philosophy  # Filter by profile
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

def load_voices() -> Dict:
    """Load voice configuration."""
    config_path = Path(__file__).parent / "configs" / "voice_references.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def list_built_in_voices(engine: str = None, profile: str = None):
    """List built-in voices."""
    config = load_voices()
    built_in = config.get("built_in_voices", {})

    print("\n" + "="*80)
    print("BUILT-IN VOICES (No reference audio needed)")
    print("="*80)

    for engine_name, voices in built_in.items():
        if engine and engine != engine_name:
            continue

        print(f"\n{'-'*80}")
        print(f"  {engine_name.upper()} Voices ({len(voices)} available)")
        print(f"{'-'*80}\n")

        for voice_name, voice_data in voices.items():
            if profile and profile.lower() not in [p.lower() for p in voice_data.get("preferred_profiles", [])]:
                continue

            gender = voice_data.get("gender", "unknown")
            accent = voice_data.get("accent", "neutral")
            desc = voice_data.get("description", "No description")
            profiles = ", ".join(voice_data.get("preferred_profiles", []))
            quality = voice_data.get("quality_score", "N/A")

            print(f"  • {voice_name}")
            print(f"    {desc}")
            print(f"    Gender: {gender.capitalize()} | Accent: {accent} | Quality: {quality}")
            print(f"    Best for: {profiles}")
            print()

def list_custom_voices(profile: str = None):
    """List custom voice clones."""
    config = load_voices()
    references = config.get("voice_references", {})

    print("\n" + "="*80)
    print("CUSTOM VOICE CLONES (Require reference audio)")
    print("="*80 + "\n")

    for voice_name, voice_data in references.items():
        if profile and profile.lower() not in [p.lower() for p in voice_data.get("preferred_profiles", [])]:
            continue

        desc = voice_data.get("description", "No description")
        narrator = voice_data.get("narrator_name", "Unknown")
        profiles = ", ".join(voice_data.get("preferred_profiles", []))
        quality = voice_data.get("quality_score", "N/A")

        has_local = "local_path" in voice_data
        has_url = "source_url" in voice_data
        source = "Local file" if has_local else ("URL download" if has_url else "Unknown")

        print(f"  • {voice_name}")
        print(f"    {desc}")
        print(f"    Narrator: {narrator} | Source: {source} | Quality: {quality}")
        print(f"    Best for: {profiles}")
        print()

def main():
    parser = argparse.ArgumentParser(description="List available TTS voices")
    parser.add_argument("--engine", choices=["xtts", "kokoro"], help="Filter by engine")
    parser.add_argument("--profile", help="Filter by profile (e.g., philosophy, fiction)")
    parser.add_argument("--built-in-only", action="store_true", help="Show only built-in voices")
    parser.add_argument("--custom-only", action="store_true", help="Show only custom voice clones")

    args = parser.parse_args()

    if not args.custom_only:
        list_built_in_voices(args.engine, args.profile)

    if not args.built_in_only:
        list_custom_voices(args.profile)

    print("\n" + "="*80)
    print("USAGE")
    print("="*80)
    print("\nTo use a built-in voice:")
    print("  python engine_runner.py --engine xtts --voice \"Claribel Dervla\" --file_id MyBook ...")
    print("  python engine_runner.py --engine kokoro --voice af_sarah --file_id MyBook ...")
    print("\nTo use a custom voice clone:")
    print("  python engine_runner.py --engine xtts --voice bob_neufeld --file_id MyBook ...")
    print("\nVoice cloning (XTTS only):")
    print("  Add your reference audio to voice_references.json with 'local_path'")
    print("  XTTS will clone the voice automatically")
    print()

if __name__ == "__main__":
    main()
