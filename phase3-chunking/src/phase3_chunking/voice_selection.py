"""
Voice selection logic for TTS synthesis with multi-level override support.

Reads from configs/voices.json and selects appropriate voice based on:
1. CLI override (--voice flag) - HIGHEST PRIORITY
2. File-level override (pipeline.json voice_overrides.{file_id})
3. Global override (pipeline.json tts_voice)
4. Genre profile match
5. Default voice (fallback) - LOWEST PRIORITY
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from pipeline_common import PipelineState

logger = logging.getLogger(__name__)


def find_voice_registry() -> Path:
    """
    Find the voices.json configuration file.

    Searches in:
    1. Project root configs/ directory
    2. Phase3 configs/ directory (fallback)

    Returns:
        Path to voices.json

    Raises:
        FileNotFoundError: If voices.json not found
    """
    # Try to find monorepo root
    current = Path(__file__).resolve().parent

    # Search upward for configs/voices.json
    for _ in range(5):  # Max 5 levels up
        configs_path = current / "configs" / "voices.json"
        if configs_path.exists():
            logger.debug(f"Found voice registry: {configs_path}")
            return configs_path

        # Try parent configs
        parent_configs = current.parent / "configs" / "voices.json"
        if parent_configs.exists():
            logger.debug(f"Found voice registry: {parent_configs}")
            return parent_configs

        current = current.parent

    # Fallback: Check in phase3 directory
    phase3_configs = (
        Path(__file__).resolve().parent / "configs" / "voices.json"
    )
    if phase3_configs.exists():
        logger.debug(f"Found voice registry in phase3: {phase3_configs}")
        return phase3_configs

    raise FileNotFoundError(
        "voices.json not found. Expected location: <monorepo_root>/configs/voices.json"
    )


def load_voice_registry() -> Dict:
    """
    Load voice registry from voices.json.

    Returns:
        Dictionary with voice configurations

    Raises:
        FileNotFoundError: If voices.json not found
        json.JSONDecodeError: If voices.json is invalid
    """
    voice_file = find_voice_registry()

    try:
        with open(voice_file, "r", encoding="utf-8") as f:
            registry = json.load(f)

        logger.info(f"Loaded voice registry from: {voice_file}")
        logger.debug(
            f"Available voices: {list(registry.get('voices', {}).keys())}"
        )

        return registry

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in voices.json: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load voice registry: {e}")
        raise


def normalize_voice_id(voice_id: str) -> str:
    """
    Normalize voice ID to match registry key format.

    Args:
        voice_id: Voice identifier (e.g., "Baldur Sanjin" or "baldur_sanjin")

    Returns:
        Normalized voice ID (e.g., "baldur_sanjin")
    """
    return voice_id.lower().replace(' ', '_')


def validate_voice_id(voice_id: str) -> bool:
    """
    Check if a voice ID exists in the registry.

    Args:
        voice_id: Voice identifier to validate

    Returns:
        True if voice exists, False otherwise
    """
    try:
        registry = load_voice_registry()
        voices = registry.get("voices", {})
        # Normalize voice_id to match key format (lowercase with underscores)
        normalized_id = normalize_voice_id(voice_id)
        return normalized_id in voices or voice_id in voices
    except Exception as e:
        logger.error(f"Failed to validate voice ID: {e}")
        return False


def select_voice(
    profile_name: str,
    file_id: Optional[str] = None,
    pipeline_data: Optional[Dict] = None,
    cli_override: Optional[str] = None,
) -> str:
    """
    Select appropriate voice using priority cascade.

    Selection priority (highest to lowest):
    1. CLI override (--voice flag)
    2. File-level override (pipeline_data['voice_overrides'][file_id])
    3. Global override (pipeline_data['tts_voice'])
    4. Genre profile match
    5. Default voice from registry

    Args:
        profile_name: Genre profile (e.g., 'philosophy', 'fiction')
        file_id: File identifier for file-level overrides (optional)
        pipeline_data: pipeline.json data with overrides (optional)
        cli_override: Voice ID from --voice CLI flag (optional)

    Returns:
        Voice ID (e.g., 'jim_locke', 'neutral_narrator')
    """
    selected_voice = None
    selection_reason = ""

    # Priority 1: CLI override (--voice flag)
    if cli_override:
        if validate_voice_id(cli_override):
            selected_voice = normalize_voice_id(cli_override)
            selection_reason = f"CLI override (--voice {cli_override})"
        else:
            logger.warning(
                f"Invalid CLI voice '{cli_override}' not found in registry, ignoring"
            )

    # Priority 2: File-level override
    if not selected_voice and pipeline_data and file_id:
        voice_overrides = pipeline_data.get("voice_overrides", {})
        file_override = voice_overrides.get(file_id)

        if file_override:
            if validate_voice_id(file_override):
                selected_voice = normalize_voice_id(file_override)
                selection_reason = f"File-level override for {file_id}"
            else:
                logger.warning(
                    f"Invalid file override '{file_override}' for {file_id}, ignoring"
                )

    # Priority 3: Global override
    if not selected_voice and pipeline_data:
        global_override = pipeline_data.get("tts_voice")

        if global_override:
            if validate_voice_id(global_override):
                selected_voice = normalize_voice_id(global_override)
                selection_reason = "Global override (tts_voice)"
            else:
                logger.warning(
                    f"Invalid global override '{global_override}', ignoring"
                )

    # Priority 4: Genre profile match
    if not selected_voice:
        try:
            registry = load_voice_registry()
            voices = registry.get("voices", {})

            # Find voices that prefer this profile
            matching_voices = []
            for voice_id, voice_data in voices.items():
                preferred = voice_data.get("preferred_profiles", [])
                if profile_name in preferred:
                    matching_voices.append(voice_id)

            if matching_voices:
                # Use first matching voice
                selected_voice = matching_voices[0]
                selection_reason = (
                    f"Profile match ({profile_name} → {selected_voice})"
                )

        except Exception as e:
            logger.error(f"Profile matching failed: {e}")

    # Priority 5: Default voice (fallback)
    if not selected_voice:
        try:
            registry = load_voice_registry()
            default_voice = registry.get("default_voice", "neutral_narrator")
            selected_voice = default_voice
            selection_reason = (
                f"Default fallback (no match for '{profile_name}')"
            )
        except Exception as e:
            logger.error(f"Failed to get default voice: {e}")
            selected_voice = "neutral_narrator"
            selection_reason = "Hardcoded fallback (registry error)"

    logger.info(f"Voice selection: {selected_voice} ({selection_reason})")
    return selected_voice


def get_voice_params(voice_id: str) -> Dict:
    """
    Get TTS engine parameters for a voice.

    Args:
        voice_id: Voice ID (e.g., 'jim_locke')

    Returns:
        Dictionary with TTS parameters (pitch, rate, etc.)
    """
    try:
        registry = load_voice_registry()
        voices = registry.get("voices", {})

        if voice_id not in voices:
            logger.warning(
                f"Voice '{voice_id}' not found, using default params"
            )
            return {}

        params = voices[voice_id].get("tts_engine_params", {})
        logger.debug(f"Voice '{voice_id}' params: {params}")
        return params

    except Exception as e:
        logger.error(f"Failed to get voice params: {e}")
        return {}


def list_available_voices(profile: Optional[str] = None) -> Dict[str, Dict]:
    """
    Get list of available voices with full details.

    Args:
        profile: Optional genre profile to filter by

    Returns:
        Dictionary mapping voice IDs to voice data
    """
    try:
        registry = load_voice_registry()
        voices = registry.get("voices", {})

        if profile:
            # Filter by profile
            return {
                voice_id: voice_data
                for voice_id, voice_data in voices.items()
                if profile in voice_data.get("preferred_profiles", [])
            }

        return voices

    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        return {}


def set_file_override(
    pipeline_path: Path, file_id: str, voice_id: str
) -> None:
    """
    Set file-level voice override in pipeline.json.

    Args:
        pipeline_path: Path to pipeline.json
        file_id: File identifier
        voice_id: Voice ID to use for this file

    Example:
        >>> set_file_override(
        ...     Path("pipeline.json"),
        ...     "file_abc123",
        ...     "landon_elkind"
        ... )

        Updates pipeline.json:
        {
          "voice_overrides": {
            "file_abc123": "landon_elkind"
          }
        }
    """
    # Validate voice exists
    if not validate_voice_id(voice_id):
        raise ValueError(f"Voice ID '{voice_id}' not found in registry")

    state = PipelineState(pipeline_path, validate_on_read=False)
    with state.transaction(operation="phase3_set_file_voice") as txn:
        overrides = txn.data.setdefault("voice_overrides", {})
        overrides[file_id] = voice_id
    logger.info(f"Set file-level override: {file_id} → {voice_id}")


def set_global_override(pipeline_path: Path, voice_id: str) -> None:
    """
    Set global voice override in pipeline.json.

    This applies to ALL files unless overridden at file level.

    Args:
        pipeline_path: Path to pipeline.json
        voice_id: Voice ID to use globally

    Example:
        >>> set_global_override(Path("pipeline.json"), "tom_weiss")

        Updates pipeline.json:
        {
          "tts_voice": "tom_weiss"
        }
    """
    # Validate voice exists
    if not validate_voice_id(voice_id):
        raise ValueError(f"Voice ID '{voice_id}' not found in registry")

    state = PipelineState(pipeline_path, validate_on_read=False)
    with state.transaction(operation="phase3_set_global_voice") as txn:
        txn.data["tts_voice"] = voice_id
    logger.info(f"Set global voice override: {voice_id}")


def clear_override(pipeline_path: Path, file_id: Optional[str] = None) -> None:
    """
    Clear voice override.

    Args:
        pipeline_path: Path to pipeline.json
        file_id: File ID to clear override for (None = clear global)

    Examples:
        >>> # Clear global override
        >>> clear_override(Path("pipeline.json"))

        >>> # Clear file-level override
        >>> clear_override(Path("pipeline.json"), "file_abc123")
    """
    state = PipelineState(pipeline_path, validate_on_read=False)
    with state.transaction(operation="phase3_clear_voice") as txn:
        if file_id:
            overrides = txn.data.get("voice_overrides", {})
            if file_id in overrides:
                del overrides[file_id]
                txn.data["voice_overrides"] = overrides
                logger.info(f"Cleared file-level override for {file_id}")
            else:
                logger.warning(f"No file-level override found for {file_id}")
        else:
            if "tts_voice" in txn.data:
                txn.data["tts_voice"] = None
                logger.info("Cleared global voice override")
            else:
                logger.warning("No global voice override set")


def print_voice_info(voice_id: Optional[str] = None) -> None:
    """
    Print voice information to console.

    Args:
        voice_id: Specific voice to show (None = show all)
    """
    try:
        registry = load_voice_registry()
        voices = registry.get("voices", {})

        if voice_id:
            # Show specific voice
            if voice_id not in voices:
                print(f"❌ Voice '{voice_id}' not found")
                return

            voice_data = voices[voice_id]
            print(f"\n🎤 {voice_id}")
            print(f"{'='*60}")
            print(f"Description: {voice_data.get('description', 'N/A')}")
            print(f"Narrator: {voice_data.get('narrator_name', 'N/A')}")
            print(f"Source: {voice_data.get('source', 'N/A')}")
            print(
                f"Profiles: {', '.join(voice_data.get('preferred_profiles', []))}"
            )
            print(f"TTS Params: {voice_data.get('tts_engine_params', {})}")

        else:
            # Show all voices
            print(f"\n{'='*60}")
            print("Available Voices:")
            print(f"{'='*60}\n")

            for vid, vdata in voices.items():
                print(f"🎤 {vid}")
                print(f"   {vdata.get('description', 'N/A')}")
                print(
                    f"   Profiles: {', '.join(vdata.get('preferred_profiles', []))}"
                )
                print()

            print(f"Default voice: {registry.get('default_voice', 'N/A')}\n")

    except Exception as e:
        print(f"❌ Error loading voice registry: {e}")


# CLI interface for voice management
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Voice Override Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available voices
  python voice_selection.py --list
  
  # Show voices for specific genre
  python voice_selection.py --list --profile philosophy
  
  # Set global voice override
  python voice_selection.py --set-global landon_elkind
  
  # Set file-specific voice override
  python voice_selection.py --set-file file_abc123 tom_weiss
  
  # Clear global override
  python voice_selection.py --clear-global
  
  # Clear file-specific override
  python voice_selection.py --clear-file file_abc123
  
  # Show details for specific voice
  python voice_selection.py --info jim_locke
        """,
    )

    parser.add_argument(
        "--list", action="store_true", help="List available voices"
    )
    parser.add_argument("--profile", help="Filter voices by genre profile")
    parser.add_argument("--info", help="Show details for specific voice")
    parser.add_argument(
        "--set-global", metavar="VOICE_ID", help="Set global voice override"
    )
    parser.add_argument(
        "--set-file",
        nargs=2,
        metavar=("FILE_ID", "VOICE_ID"),
        help="Set file-level voice override",
    )
    parser.add_argument(
        "--clear-global",
        action="store_true",
        help="Clear global voice override",
    )
    parser.add_argument(
        "--clear-file",
        metavar="FILE_ID",
        help="Clear file-level voice override",
    )
    parser.add_argument(
        "--pipeline",
        default="../../pipeline.json",
        help="Path to pipeline.json (default: ../../pipeline.json)",
    )

    args = parser.parse_args()

    # Handle commands
    if args.list:
        voices = list_available_voices(args.profile)
        if args.profile:
            print(f"\n{'='*60}")
            print(f"Voices for profile: {args.profile}")
            print(f"{'='*60}\n")
        else:
            print(f"\n{'='*60}")
            print("All available voices:")
            print(f"{'='*60}\n")

        for voice_id, voice_data in voices.items():
            print(f"🎤 {voice_id}")
            print(f"   {voice_data.get('description', 'N/A')}")
            print(f"   Narrator: {voice_data.get('narrator_name', 'N/A')}")
            print(
                f"   Profiles: {', '.join(voice_data.get('preferred_profiles', []))}"
            )
            print()

    elif args.info:
        print_voice_info(args.info)

    elif args.set_global:
        try:
            set_global_override(Path(args.pipeline), args.set_global)
            print(f"✅ Set global voice override: {args.set_global}")
        except Exception as e:
            print(f"❌ Error: {e}")

    elif args.set_file:
        file_id, voice_id = args.set_file
        try:
            set_file_override(Path(args.pipeline), file_id, voice_id)
            print(f"✅ Set file-level override: {file_id} → {voice_id}")
        except Exception as e:
            print(f"❌ Error: {e}")

    elif args.clear_global:
        try:
            clear_override(Path(args.pipeline))
            print("✅ Cleared global voice override")
        except Exception as e:
            print(f"❌ Error: {e}")

    elif args.clear_file:
        try:
            clear_override(Path(args.pipeline), args.clear_file)
            print(f"✅ Cleared file-level override for {args.clear_file}")
        except Exception as e:
            print(f"❌ Error: {e}")

    else:
        parser.print_help()


# Export
__all__ = [
    "select_voice",
    "get_voice_params",
    "list_available_voices",
    "load_voice_registry",
    "validate_voice_id",
    "set_file_override",
    "set_global_override",
    "clear_override",
    "print_voice_info",
]
