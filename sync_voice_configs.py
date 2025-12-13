#!/usr/bin/env python3
"""
Sync Voice Configurations

Synchronizes configs/voices.json (Phase 3) with phase4_tts/configs/voice_references.json (Phase 4).
Phase 4 is the canonical source since it has the actual voice files and built-in definitions.

This ensures all voices selectable in Phase 4 are also available for Phase 3 selection.
"""

import json
from pathlib import Path

# Paths
PHASE3_CONFIG = Path("configs/voices.json")
PHASE4_CONFIG = Path("phase4_tts/configs/voice_references.json")
BACKUP_CONFIG = Path("configs/voices.json.backup")

def normalize_voice_id(voice_id: str) -> str:
    """Convert 'Claribel Dervla' to 'claribel_dervla'."""
    return voice_id.lower().replace(' ', '_').replace('-', '_')


def main():
    print("="*70)
    print("Voice Configuration Sync")
    print("="*70)

    # Load configs
    print(f"\n📖 Loading Phase 3 config: {PHASE3_CONFIG}")
    p3_data = json.load(open(PHASE3_CONFIG))
    p3_voices = p3_data['voices']

    print(f"📖 Loading Phase 4 config: {PHASE4_CONFIG}")
    p4_data = json.load(open(PHASE4_CONFIG))

    # Backup Phase 3 config
    print(f"\n💾 Backing up Phase 3 config to: {BACKUP_CONFIG}")
    with open(BACKUP_CONFIG, 'w') as f:
        json.dump(p3_data, f, indent=2)

    # Build new voice registry
    new_voices = {}
    added = []

    # Process custom voices (voice_references)
    print(f"\n📝 Processing custom voices...")
    for voice_id, voice_data in p4_data.get('voice_references', {}).items():
        normalized_id = normalize_voice_id(voice_id)

        if normalized_id in p3_voices:
            # Keep existing Phase 3 entry (it has more metadata)
            new_voices[normalized_id] = p3_voices[normalized_id]
        else:
            # Add new entry from Phase 4
            new_voices[normalized_id] = {
                "description": voice_data.get('description', f"Custom voice: {voice_id}"),
                "narrator": voice_id,
                "reference_audio": voice_data.get('file'),
                "preferred_profiles": voice_data.get('preferred_profiles', ["general"]),
                "source": "LibriVox custom",
            }
            added.append(normalized_id)

    # Process XTTS built-in voices
    print(f"📝 Processing XTTS built-in voices...")
    for voice_id in p4_data.get('built_in_voices', {}).get('xtts', {}).keys():
        normalized_id = normalize_voice_id(voice_id)

        if normalized_id in p3_voices:
            new_voices[normalized_id] = p3_voices[normalized_id]
        else:
            new_voices[normalized_id] = {
                "description": f"XTTS - {voice_id}",
                "narrator": voice_id,
                "source": "XTTS built-in",
                "built_in": True,
                "engine": "xtts",
                "preferred_profiles": ["general"],
            }
            added.append(normalized_id)

    # Process Kokoro built-in voices
    print(f"📝 Processing Kokoro built-in voices...")
    for voice_id, voice_data in p4_data.get('built_in_voices', {}).get('kokoro', {}).items():
        normalized_id = normalize_voice_id(voice_id)

        if normalized_id in p3_voices:
            new_voices[normalized_id] = p3_voices[normalized_id]
        else:
            lang = voice_data.get('language', 'en')
            new_voices[normalized_id] = {
                "description": f"Kokoro - {voice_id}",
                "narrator": voice_id,
                "source": "Kokoro built-in",
                "built_in": True,
                "engine": "kokoro",
                "preferred_profiles": ["general"],
            }
            if lang != 'en':
                new_voices[normalized_id]['language'] = lang
            added.append(normalized_id)

    # Update Phase 3 config
    p3_data['voices'] = new_voices

    # Write updated config
    print(f"\n💾 Writing updated Phase 3 config...")
    with open(PHASE3_CONFIG, 'w') as f:
        json.dump(p3_data, f, indent=2)

    # Summary
    print(f"\n" + "="*70)
    print(f"SYNC COMPLETE")
    print(f"="*70)
    print(f"\n📊 Statistics:")
    print(f"  - Total voices: {len(new_voices)}")
    print(f"  - Added voices: {len(added)}")

    if added:
        print(f"\n✨ Newly added voices:")
        for v in sorted(added)[:20]:
            print(f"  - {v}")
        if len(added) > 20:
            print(f"  ... and {len(added) - 20} more")

    print(f"\n✅ Phase 3 can now select all Phase 4 voices!")
    print(f"💾 Backup saved to: {BACKUP_CONFIG}")


if __name__ == "__main__":
    main()
