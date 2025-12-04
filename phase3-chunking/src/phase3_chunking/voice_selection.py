"""
Voice selection logic for TTS synthesis with multi-level override support.

Reads from phase4_tts/configs/voice_references.json (unified config) and selects
appropriate voice based on:
1. CLI override (--voice flag) - HIGHEST PRIORITY
2. File-level override (pipeline.json voice_overrides.{file_id})
3. Global override (pipeline.json tts_voice)
4. Genre profile match (prefer built-in voices)
5. Default voice (fallback) - LOWEST PRIORITY

IMPORTANT: Phase 3 and Phase 4 now share the same voice configuration.
- Custom voices (voice_references) require audio files in phase4_tts/voice_references/
- Built-in voices (xtts, kokoro) are always available - no audio files needed
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pipeline_common import PipelineState

logger = logging.getLogger(__name__)


def find_project_root() -> Path:
    """
    Find the project root directory.

    Searches upward for pipeline.json or phase4_tts directory.

    Returns:
        Path to project root directory
    """
    current = Path(__file__).resolve().parent

    for _ in range(6):  # Max 6 levels up
        if (current / "pipeline.json").exists():
            return current
        if (current / "phase4_tts").exists():
            return current
        current = current.parent

    # Fallback: assume 4 levels up from this file
    return Path(__file__).resolve().parent.parent.parent.parent


def find_voice_registry() -> Path:
    """
    Find the unified voice configuration file.

    Searches in order of priority:
    1. phase4_tts/configs/voice_references.json (unified config - PREFERRED)
    2. configs/voices.json (legacy fallback)

    Returns:
        Path to voice configuration file

    Raises:
        FileNotFoundError: If no voice config found
    """
    project_root = find_project_root()

    # Priority 1: Phase 4 unified config (preferred)
    unified_config = project_root / "phase4_tts" / "configs" / "voice_references.json"
    if unified_config.exists():
        logger.debug(f"Using unified voice config: {unified_config}")
        return unified_config

    # Priority 2: Legacy configs/voices.json
    legacy_config = project_root / "configs" / "voices.json"
    if legacy_config.exists():
        logger.warning(
            f"Using LEGACY voice config: {legacy_config}. "
            "Voices defined here may not have audio files for Phase 4 synthesis."
        )
        return legacy_config

    raise FileNotFoundError(
        "Voice config not found. Expected: phase4_tts/configs/voice_references.json"
    )


def load_voice_registry() -> Dict:
    """
    Load voice registry and normalize to unified format.

    Returns a dictionary with:
    - voice_references: Custom voices (may need audio files)
    - built_in_voices: Engine-provided voices (always available)
    - all_voices: Flat dict of all voices for quick lookup
    - default_voice: Default voice ID

    Returns:
        Normalized voice registry dictionary

    Raises:
        FileNotFoundError: If config not found
        json.JSONDecodeError: If config is invalid
    """
    voice_file = find_voice_registry()

    try:
        with open(voice_file, "r", encoding="utf-8") as f:
            raw_registry = json.load(f)

        # Detect format and normalize
        if "voice_references" in raw_registry or "built_in_voices" in raw_registry:
            # New unified format from phase4_tts/configs/voice_references.json
            registry = _normalize_unified_format(raw_registry, voice_file)
        elif "voices" in raw_registry:
            # Legacy format from configs/voices.json
            registry = _normalize_legacy_format(raw_registry, voice_file)
        else:
            logger.error(f"Unknown voice config format in {voice_file}")
            registry = {
                "voice_references": {},
                "built_in_voices": {},
                "all_voices": {},
                "default_voice": "am_adam",  # Safe Kokoro fallback
                "_source_file": str(voice_file),
            }

        voice_count = len(registry.get("all_voices", {}))
        builtin_count = sum(
            len(v) for v in registry.get("built_in_voices", {}).values()
        )
        custom_count = len(registry.get("voice_references", {}))

        logger.info(
            f"Loaded voice registry: {voice_count} total voices "
            f"({custom_count} custom, {builtin_count} built-in) from {voice_file}"
        )

        return registry

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in voice config: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load voice registry: {e}")
        raise


def _normalize_unified_format(raw: Dict, source_file: Path) -> Dict:
    """Normalize the unified phase4_tts format."""
    voice_refs = raw.get("voice_references", {})
    built_in = raw.get("built_in_voices", {})

    # Build flat all_voices dict
    all_voices: Dict[str, Dict] = {}

    # Add custom voice references
    for voice_id, voice_data in voice_refs.items():
        enriched = dict(voice_data)
        enriched["_type"] = "custom"
        enriched["_source"] = "voice_references"
        all_voices[voice_id] = enriched

    # Add built-in voices from each engine
    for engine_name, engine_voices in built_in.items():
        if not isinstance(engine_voices, dict):
            continue
        for voice_name, voice_data in engine_voices.items():
            enriched = dict(voice_data)
            enriched["_type"] = "built_in"
            enriched["_source"] = f"built_in_voices.{engine_name}"
            enriched["engine"] = engine_name
            enriched["built_in"] = True
            all_voices[voice_name] = enriched

    return {
        "voice_references": voice_refs,
        "built_in_voices": built_in,
        "all_voices": all_voices,
        "default_voice": raw.get("default_voice", "am_adam"),
        "_source_file": str(source_file),
    }


def _normalize_legacy_format(raw: Dict, source_file: Path) -> Dict:
    """Normalize the legacy configs/voices.json format."""
    legacy_voices = raw.get("voices", {})

    # Treat all legacy voices as custom (they need audio files)
    voice_refs: Dict[str, Dict] = {}
    all_voices: Dict[str, Dict] = {}

    for voice_id, voice_data in legacy_voices.items():
        enriched = dict(voice_data)
        enriched["_type"] = "custom"
        enriched["_source"] = "legacy_voices"
        # Map legacy field names
        if "narrator" in enriched and "narrator_name" not in enriched:
            enriched["narrator_name"] = enriched["narrator"]
        voice_refs[voice_id] = enriched
        all_voices[voice_id] = enriched

    return {
        "voice_references": voice_refs,
        "built_in_voices": {},  # Legacy format has no built-in voices
        "all_voices": all_voices,
        "default_voice": raw.get("default_voice", raw.get("fallback_voice", "neutral_narrator")),
        "_source_file": str(source_file),
        "_is_legacy": True,
    }


def validate_voice_id(voice_id: str) -> bool:
    """
    Check if a voice ID exists in the registry (regardless of availability).

    Args:
        voice_id: Voice identifier to validate

    Returns:
        True if voice exists in config, False otherwise
    """
    try:
        registry = load_voice_registry()
        all_voices = registry.get("all_voices", {})
        return voice_id in all_voices
    except Exception as e:
        logger.error(f"Failed to validate voice ID: {e}")
        return False


def get_voice_availability(voice_id: str) -> Tuple[bool, str, Optional[str]]:
    """
    Check if a voice is actually available for synthesis.

    Built-in voices (xtts, kokoro) are always available.
    Custom voices require audio reference files on disk.

    Args:
        voice_id: Voice identifier to check

    Returns:
        Tuple of (is_available, voice_type, reason_if_unavailable)
        - is_available: True if voice can be used for synthesis
        - voice_type: "built_in" or "custom"
        - reason_if_unavailable: Explanation if not available, None otherwise
    """
    try:
        registry = load_voice_registry()
        all_voices = registry.get("all_voices", {})

        if voice_id not in all_voices:
            return (False, "unknown", f"Voice '{voice_id}' not found in registry")

        voice_data = all_voices[voice_id]
        voice_type = voice_data.get("_type", "custom")

        # Built-in voices are always available
        if voice_type == "built_in" or voice_data.get("built_in", False):
            return (True, "built_in", None)

        # Custom voices need audio files
        local_path = voice_data.get("local_path")
        if not local_path:
            return (
                False,
                "custom",
                f"Custom voice '{voice_id}' has no local_path configured",
            )

        # Check if audio file exists
        project_root = find_project_root()
        # Try relative to phase4_tts first, then project root
        audio_paths = [
            project_root / "phase4_tts" / local_path,
            project_root / local_path,
        ]

        for audio_path in audio_paths:
            if audio_path.exists():
                return (True, "custom", None)

        return (
            False,
            "custom",
            f"Audio file not found for '{voice_id}': {local_path}",
        )

    except Exception as e:
        logger.error(f"Failed to check voice availability: {e}")
        return (False, "unknown", str(e))


def get_available_fallback_voice() -> str:
    """
    Get a reliable fallback voice that is always available.

    Returns a built-in Kokoro voice (am_adam preferred) since
    these don't require audio files.

    Returns:
        Voice ID of a built-in voice
    """
    # Preferred fallbacks in order (high-quality Kokoro voices)
    preferred = ["am_adam", "af_sarah", "bm_daniel", "bf_emma"]

    try:
        registry = load_voice_registry()
        all_voices = registry.get("all_voices", {})

        for voice_id in preferred:
            if voice_id in all_voices:
                voice_data = all_voices[voice_id]
                if voice_data.get("built_in", False) or voice_data.get("_type") == "built_in":
                    return voice_id

        # If preferred not found, find any built-in voice
        for voice_id, voice_data in all_voices.items():
            if voice_data.get("built_in", False) or voice_data.get("_type") == "built_in":
                return voice_id

    except Exception as e:
        logger.error(f"Failed to find fallback voice: {e}")

    # Ultimate fallback
    return "am_adam"


def select_voice(
    profile_name: str,
    file_id: Optional[str] = None,
    pipeline_data: Optional[Dict] = None,
    cli_override: Optional[str] = None,
    require_available: bool = True,
) -> str:
    """
    Select appropriate voice using priority cascade with availability checking.

    Selection priority (highest to lowest):
    1. CLI override (--voice flag)
    2. File-level override (pipeline_data['voice_overrides'][file_id])
    3. Global override (pipeline_data['tts_voice'])
    4. Genre profile match (prefers available built-in voices)
    5. Default voice from registry

    If require_available is True (default), custom voices without audio files
    will trigger a fallback to a built-in voice with a warning.

    Args:
        profile_name: Genre profile (e.g., 'philosophy', 'fiction')
        file_id: File identifier for file-level overrides (optional)
        pipeline_data: pipeline.json data with overrides (optional)
        cli_override: Voice ID from --voice CLI flag (optional)
        require_available: If True, verify voice can actually be used (default: True)

    Returns:
        Voice ID (e.g., 'am_adam', 'af_sarah', or custom voice if available)
    """
    selected_voice = None
    selection_reason = ""
    originally_requested = None

    # Priority 1: CLI override (--voice flag)
    if cli_override:
        if validate_voice_id(cli_override):
            selected_voice = cli_override
            originally_requested = cli_override
            selection_reason = f"CLI override (--voice {cli_override})"
        else:
            logger.warning(
                f"CLI voice '{cli_override}' not found in registry, ignoring"
            )

    # Priority 2: File-level override
    if not selected_voice and pipeline_data and file_id:
        voice_overrides = pipeline_data.get("voice_overrides", {})
        file_override = voice_overrides.get(file_id)

        if file_override:
            if validate_voice_id(file_override):
                selected_voice = file_override
                originally_requested = file_override
                selection_reason = f"File-level override for {file_id}"
            else:
                logger.warning(
                    f"File override '{file_override}' for {file_id} not in registry, ignoring"
                )

    # Priority 3: Global override
    if not selected_voice and pipeline_data:
        global_override = pipeline_data.get("tts_voice")

        if global_override:
            if validate_voice_id(global_override):
                selected_voice = global_override
                originally_requested = global_override
                selection_reason = "Global override (tts_voice)"
            else:
                logger.warning(
                    f"Global override '{global_override}' not in registry, ignoring"
                )

    # Priority 4: Genre profile match (prefer available built-in voices)
    if not selected_voice:
        try:
            registry = load_voice_registry()
            all_voices = registry.get("all_voices", {})

            # Find voices that prefer this profile, prioritizing built-in
            builtin_matches: List[str] = []
            custom_matches: List[str] = []

            for voice_id, voice_data in all_voices.items():
                preferred = voice_data.get("preferred_profiles", [])
                if profile_name in preferred:
                    if voice_data.get("built_in", False) or voice_data.get("_type") == "built_in":
                        builtin_matches.append(voice_id)
                    else:
                        custom_matches.append(voice_id)

            # Prefer built-in voices (always available) over custom
            if builtin_matches:
                selected_voice = builtin_matches[0]
                selection_reason = f"Profile match (built-in: {profile_name} → {selected_voice})"
            elif custom_matches:
                selected_voice = custom_matches[0]
                selection_reason = f"Profile match (custom: {profile_name} → {selected_voice})"

        except Exception as e:
            logger.error(f"Profile matching failed: {e}")

    # Priority 5: Default voice (fallback)
    if not selected_voice:
        try:
            registry = load_voice_registry()
            default_voice = registry.get("default_voice", "am_adam")
            selected_voice = default_voice
            selection_reason = f"Default fallback (no match for '{profile_name}')"
        except Exception as e:
            logger.error(f"Failed to get default voice: {e}")
            selected_voice = get_available_fallback_voice()
            selection_reason = "Built-in fallback (registry error)"

    # Availability check - ensure voice can actually be used
    if require_available and selected_voice:
        is_available, voice_type, unavailable_reason = get_voice_availability(selected_voice)

        if not is_available:
            fallback_voice = get_available_fallback_voice()
            logger.warning(
                f"VOICE FALLBACK: '{selected_voice}' is not available "
                f"({unavailable_reason}). Using built-in '{fallback_voice}' instead."
            )

            # Record what was originally requested
            if originally_requested:
                logger.info(
                    f"Original voice request: '{originally_requested}' → "
                    f"Fallback: '{fallback_voice}'"
                )

            selected_voice = fallback_voice
            selection_reason = f"Fallback from unavailable '{originally_requested or selected_voice}'"

    logger.info(f"Voice selection: {selected_voice} ({selection_reason})")
    return selected_voice


def get_voice_params(voice_id: str) -> Dict:
    """
    Get TTS engine parameters for a voice.

    Args:
        voice_id: Voice ID (e.g., 'am_adam', 'george_mckayland')

    Returns:
        Dictionary with TTS parameters (pitch, rate, etc.)
    """
    try:
        registry = load_voice_registry()
        all_voices = registry.get("all_voices", {})

        if voice_id not in all_voices:
            logger.warning(
                f"Voice '{voice_id}' not found, using default params"
            )
            return {}

        params = all_voices[voice_id].get("tts_engine_params", {})
        logger.debug(f"Voice '{voice_id}' params: {params}")
        return params

    except Exception as e:
        logger.error(f"Failed to get voice params: {e}")
        return {}


def list_available_voices(
    profile: Optional[str] = None,
    only_available: bool = False,
) -> Dict[str, Dict]:
    """
    Get list of voices with full details.

    Args:
        profile: Optional genre profile to filter by
        only_available: If True, only return voices that can actually be used

    Returns:
        Dictionary mapping voice IDs to voice data
    """
    try:
        registry = load_voice_registry()
        all_voices = registry.get("all_voices", {})

        result: Dict[str, Dict] = {}

        for voice_id, voice_data in all_voices.items():
            # Filter by profile if specified
            if profile:
                preferred = voice_data.get("preferred_profiles", [])
                if profile not in preferred:
                    continue

            # Filter by availability if requested
            if only_available:
                is_available, _, _ = get_voice_availability(voice_id)
                if not is_available:
                    continue

            result[voice_id] = voice_data

        return result

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
    Print voice information to console, grouped by type.

    Args:
        voice_id: Specific voice to show (None = show all)
    """
    try:
        registry = load_voice_registry()
        all_voices = registry.get("all_voices", {})

        if voice_id:
            # Show specific voice
            if voice_id not in all_voices:
                print(f"Voice '{voice_id}' not found")
                return

            voice_data = all_voices[voice_id]
            is_available, voice_type, reason = get_voice_availability(voice_id)
            status = "AVAILABLE" if is_available else f"UNAVAILABLE: {reason}"

            print(f"\n{voice_id}")
            print("=" * 60)
            print(f"Type: {voice_type}")
            print(f"Status: {status}")
            print(f"Description: {voice_data.get('description', 'N/A')}")
            print(f"Narrator: {voice_data.get('narrator_name', 'N/A')}")
            print(f"Engine: {voice_data.get('engine', 'N/A')}")
            print(
                f"Profiles: {', '.join(voice_data.get('preferred_profiles', []))}"
            )
            if voice_data.get("local_path"):
                print(f"Audio: {voice_data.get('local_path')}")

        else:
            # Show all voices grouped by type
            print("\n" + "=" * 60)
            print("Voice Registry")
            print("=" * 60)

            # Group by type
            builtin_voices = {}
            custom_voices = {}

            for vid, vdata in all_voices.items():
                if vdata.get("built_in", False) or vdata.get("_type") == "built_in":
                    engine = vdata.get("engine", "unknown")
                    if engine not in builtin_voices:
                        builtin_voices[engine] = []
                    builtin_voices[engine].append((vid, vdata))
                else:
                    custom_voices[vid] = vdata

            # Print built-in voices
            print(f"\nBUILT-IN VOICES (always available):")
            print("-" * 40)
            for engine, voices in sorted(builtin_voices.items()):
                print(f"\n  [{engine.upper()}] ({len(voices)} voices)")
                for vid, vdata in sorted(voices, key=lambda x: x[0])[:5]:
                    print(f"    {vid}: {vdata.get('description', '')[:40]}")
                if len(voices) > 5:
                    print(f"    ... and {len(voices) - 5} more")

            # Print custom voices
            print(f"\nCUSTOM VOICES (require audio files):")
            print("-" * 40)
            for vid, vdata in sorted(custom_voices.items()):
                is_available, _, reason = get_voice_availability(vid)
                status = "OK" if is_available else "MISSING"
                print(f"  [{status}] {vid}: {vdata.get('description', '')[:35]}")

            print(f"\nDefault voice: {registry.get('default_voice', 'N/A')}")
            print(f"Total: {len(all_voices)} voices\n")

    except Exception as e:
        print(f"Error loading voice registry: {e}")


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
    "get_voice_availability",
    "get_available_fallback_voice",
    "list_available_voices",
    "load_voice_registry",
    "validate_voice_id",
    "set_file_override",
    "set_global_override",
    "clear_override",
    "print_voice_info",
    "find_project_root",
]
