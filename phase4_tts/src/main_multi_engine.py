"""Multi-engine Phase 4 entry point with schema-aware pipeline writes.

Why:
- Honors the current pipeline.json layout (phase-scoped, slugged lookups)
- Shares reference preparation and text sanitation logic with main.py
- Records which engine actually produced audio when fallbacks kick in
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf
import yaml

MODULE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_ROOT.parent.parent

# Add engines + shared utils to path
sys.path.insert(0, str(MODULE_ROOT.parent))

from engines.engine_manager import EngineManager

try:  # Import as package when executed via `python -m`
    from .utils import (
        get_selected_voice_from_phase3,
        prepare_voice_references,
        resolve_pipeline_file,
        sanitize_text_for_tts,
    )
except ImportError:  # Fallback for CLI execution (`python src/main_multi_engine.py`)
    sys.path.insert(0, str(MODULE_ROOT))
    from utils import (  # type: ignore  # pylint: disable=import-error
        get_selected_voice_from_phase3,
        prepare_voice_references,
        resolve_pipeline_file,
        sanitize_text_for_tts,
    )

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@dataclass(slots=True)
class ChunkPayload:
    chunk_id: str
    text: str
    source_path: Path


@dataclass(slots=True)
class ChunkResult:
    chunk_id: str
    success: bool
    output_path: Optional[Path]
    engine_used: Optional[str]
    error: Optional[str] = None


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_pipeline_json(json_path: Path) -> Dict[str, Any]:
    if not json_path.exists():
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_pipeline_path(raw_path: str) -> Path:
    """Resolve paths saved in pipeline.json (often Windows absolute paths)."""
    if not raw_path:
        raise FileNotFoundError("Empty chunk path")

    normalized = raw_path.strip().strip('"')
    candidates: List[Path] = []

    expanded = Path(normalized).expanduser()
    candidates.append(expanded)

    if not expanded.is_absolute():
        candidates.append((PROJECT_ROOT / normalized).resolve())

    if re.match(r"^[A-Za-z]:\\", normalized):
        win_path = PureWindowsPath(normalized)
        drive = win_path.drive.rstrip(":").lower()
        relative_parts = win_path.parts[1:]
        if drive and relative_parts:
            wsl_path = Path("/mnt") / drive / Path(*relative_parts)
        elif drive:
            wsl_path = Path("/mnt") / drive
        else:
            wsl_path = Path(normalized)
        candidates.append(wsl_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Chunk path not found: {raw_path}")


def serialize_path_for_pipeline(path: Path) -> str:
    """Convert POSIX paths back to Windows-style when running inside WSL."""
    resolved = path.resolve()
    if os.name == "nt":
        return str(resolved)

    parts = resolved.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "mnt" and len(parts[2]) == 1:
        drive = parts[2].upper()
        win_path = PureWindowsPath(f"{drive}:/", *parts[3:])
        return str(win_path)

    return str(resolved)


def derive_chunk_id(path: Path, index: int) -> str:
    """Normalize chunk IDs to chunk_0000 format using filename hints when present."""
    stem = path.stem
    match = re.search(r"chunk[_-]?(\d+)", stem, flags=re.IGNORECASE)
    if match:
        return f"chunk_{int(match.group(1)):04d}"
    return f"chunk_{index:04d}"


def collect_chunks(
    pipeline_data: Dict[str, Any],
    file_id: str,
    chunk_index: Optional[int] = None,
) -> Tuple[str, List[ChunkPayload]]:
    """Load chunk paths from phase3 section and sanitize text for synthesis."""
    resolved_key, phase3_entry = resolve_pipeline_file(pipeline_data, "phase3", file_id)
    if not phase3_entry:
        raise ValueError(f"No phase3 entry found for '{file_id}'. Run phase3 first.")

    chunk_paths = phase3_entry.get("chunk_paths", [])
    if not chunk_paths:
        raise ValueError(f"No chunk paths recorded for '{file_id}'.")

    chunk_payloads: List[ChunkPayload] = []
    for index, raw_path in enumerate(chunk_paths):
        chunk_path = normalize_pipeline_path(raw_path)
        if not chunk_path.exists():
            raise FileNotFoundError(f"Chunk file not found: {raw_path}")

        text = chunk_path.read_text(encoding="utf-8").strip()
        if not text:
            logger.warning("Chunk %s is empty: %s", index, chunk_path)
            continue

        chunk_id = derive_chunk_id(chunk_path, index)
        sanitized = sanitize_text_for_tts(text)
        chunk_payloads.append(ChunkPayload(chunk_id, sanitized, chunk_path))

    if chunk_index is not None:
        if chunk_index < 0 or chunk_index >= len(chunk_payloads):
            raise ValueError(
                f"Chunk index {chunk_index} out of range (0-{len(chunk_payloads) - 1})"
            )
        chunk_payloads = [chunk_payloads[chunk_index]]

    if not chunk_payloads:
        raise ValueError(f"All chunk files for '{file_id}' were empty or missing.")

    resolved = resolved_key or file_id
    if resolved != file_id:
        logger.info("Resolved file_id '%s' to '%s' based on phase3 data", file_id, resolved)

    return resolved, chunk_payloads


def select_voice(
    pipeline_json: Path,
    file_id: str,
    voice_override: Optional[str],
    prepared_refs: Dict[str, str],
    voices_config_path: Path
) -> Tuple[str, Optional[Path], Dict[str, Any]]:
    """Determine voice to use and return (voice_id, reference_path, engine_params).

    Returns:
        Tuple of (voice_id, reference_path, engine_params)
        - For built-in voices: reference_path is None, voice name is in engine_params
        - For custom clones: reference_path points to audio file
    """
    with open(voices_config_path, "r", encoding="utf-8") as f:
        voices_config = json.load(f)

    voice_entries = voices_config.get("voice_references", {})
    built_in_voices = voices_config.get("built_in_voices", {})
    default_voice = voices_config.get("default_voice")

    # Determine which voice to use
    selected_voice = voice_override or get_selected_voice_from_phase3(str(pipeline_json), file_id)

    if not selected_voice:
        # Default to first built-in Kokoro voice or first prepared ref
        if built_in_voices.get("kokoro"):
            selected_voice = next(iter(built_in_voices["kokoro"].keys()))
            logger.info("No voice selection. Using default built-in: '%s'", selected_voice)
        elif prepared_refs:
            selected_voice = default_voice or next(iter(prepared_refs.keys()))
            logger.info("No voice selection. Using default custom: '%s'", selected_voice)
        else:
            raise RuntimeError("No voices available (neither built-in nor custom)")

    # Check if this is a built-in voice (across all engines)
    is_built_in = False
    built_in_engine = None
    built_in_data = None

    for engine_name, engine_voices in built_in_voices.items():
        if selected_voice in engine_voices:
            is_built_in = True
            built_in_engine = engine_name
            built_in_data = engine_voices[selected_voice]
            break

    if is_built_in:
        # Built-in voice - no reference audio needed
        logger.info("Using built-in voice '%s' from %s engine", selected_voice, built_in_engine)
        engine_params = {}

        # Set appropriate voice parameter based on engine
        if built_in_engine == "xtts":
            engine_params["speaker"] = selected_voice
        elif built_in_engine == "kokoro":
            engine_params["voice"] = selected_voice

        # Add any additional params from voice config
        if built_in_data:
            tts_params = built_in_data.get("tts_engine_params", {})
            engine_params.update(tts_params)

        return selected_voice, None, engine_params

    # Custom voice clone - needs reference audio
    if not prepared_refs:
        raise RuntimeError(
            f"Voice '{selected_voice}' is not a built-in voice and no custom references are prepared."
        )

    if selected_voice not in prepared_refs:
        # Try to fall back to a built-in voice first
        if built_in_voices.get("kokoro"):
            fallback_voice = next(iter(built_in_voices["kokoro"].keys()))
            logger.warning(
                "Custom voice '%s' not found. Falling back to built-in: '%s'",
                selected_voice, fallback_voice
            )
            return select_voice(pipeline_json, file_id, fallback_voice, prepared_refs, voices_config_path)

        # Otherwise fall back to custom voice
        fallback_voice = None
        if "neutral_narrator" in prepared_refs:
            fallback_voice = "neutral_narrator"
        elif default_voice and default_voice in prepared_refs:
            fallback_voice = default_voice
        else:
            fallback_voice = next(iter(prepared_refs.keys()))
        logger.warning(
            "Voice '%s' missing from prepared references. Falling back to '%s'.",
            selected_voice,
            fallback_voice,
        )
        selected_voice = fallback_voice

    logger.info("Using custom voice clone '%s' with reference audio", selected_voice)
    reference_path = Path(prepared_refs[selected_voice]).resolve()
    engine_params = voice_entries.get(selected_voice, {}).get("tts_engine_params", {})

    return selected_voice, reference_path, engine_params


def synthesize_chunk_with_engine(
    chunk: ChunkPayload,
    reference_audio: Path,
    engine_manager: EngineManager,
    engine_name: str,
    output_dir: Path,
    language: str,
    allow_fallback: bool,
    engine_kwargs: Optional[Dict[str, Any]] = None,
) -> ChunkResult:
    """Synthesize text for a single chunk using requested engine with fallback."""
    chunk_kwargs = dict(engine_kwargs) if engine_kwargs else {}

    try:
        audio_out, used_engine = engine_manager.synthesize(
            text=chunk.text,
            reference_audio=reference_audio,
            engine=engine_name,
            language=language,
            fallback=allow_fallback,
            return_engine=True,
            **chunk_kwargs,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Chunk %s failed on engine '%s': %s", chunk.chunk_id, engine_name, exc)
        return ChunkResult(chunk.chunk_id, False, None, None, str(exc))

    audio = np.asarray(audio_out, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=0)
    audio = np.clip(audio, -1.0, 1.0)

    sample_rate = engine_manager.get_engine(used_engine).get_sample_rate()
    output_path = output_dir / f"{chunk.chunk_id}.wav"
    sf.write(output_path, audio, sample_rate)

    logger.info("Chunk %s synthesized via '%s' → %s", chunk.chunk_id, used_engine, output_path)
    return ChunkResult(chunk.chunk_id, True, output_path, used_engine)


def update_phase4_summary(
    pipeline_path: Path,
    file_id: str,
    voice_id: str,
    requested_engine: str,
    results: List[ChunkResult],
    output_dir: Path,
    duration_sec: float,
) -> None:
    """Write phase4 status back to pipeline.json following the documented schema."""
    data = load_pipeline_json(pipeline_path)
    phase4 = data.setdefault("phase4", {"status": "partial", "files": {}})
    files_section = phase4.setdefault("files", {})

    total = len(results)
    completed = sum(1 for r in results if r.success)
    failed = total - completed
    engines_used = sorted({r.engine_used for r in results if r.engine_used})

    file_entry: Dict[str, Any] = {
        "status": "success" if failed == 0 else "partial",
        "voice_id": voice_id,
        "requested_engine": requested_engine,
        "engines_used": engines_used,
        "total_chunks": total,
        "chunks_completed": completed,
        "chunks_failed": failed,
        "audio_dir": serialize_path_for_pipeline(output_dir),
        "chunk_audio_paths": [
            serialize_path_for_pipeline(r.output_path) for r in results if r.success and r.output_path
        ],
        "duration_seconds": duration_sec,
    }

    for result in results:
        file_entry[result.chunk_id] = {
            "chunk_id": result.chunk_id,
            "audio_path": serialize_path_for_pipeline(result.output_path) if result.output_path else None,
            "status": "success" if result.success else "failed",
            "engine_used": result.engine_used,
            "errors": [] if result.success else [result.error or "unknown error"],
        }

    files_section[file_id] = file_entry

    if files_section and all(entry.get("status") == "success" for entry in files_section.values()):
        phase4["status"] = "success"
    else:
        phase4["status"] = "partial"

    with open(pipeline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def build_engine_manager(device: str, engines: Optional[List[str]] = None) -> EngineManager:
    """Build engine manager with lazy imports for isolation."""
    manager = EngineManager(device=device)

    # Lazy import only requested engines to avoid dep conflicts
    if engines is None:
        engines = ["xtts", "kokoro"]

    for engine_name in engines:
        if engine_name == "xtts":
            from engines.xtts_engine import XTTSEngine
            manager.register_engine("xtts", XTTSEngine)
        elif engine_name == "kokoro":
            from engines.kokoro_engine import KokoroEngine
            manager.register_engine("kokoro", KokoroEngine)

    return manager


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4: Multi-Engine TTS Synthesis")
    parser.add_argument("--file_id", required=True, help="File identifier (matches phase3 entry)")
    parser.add_argument(
        "--engine",
        default="xtts",
        choices=["xtts", "kokoro"],
        help="Preferred engine. Fallback order is managed automatically.",
    )
    parser.add_argument("--json_path", required=True, help="Path to pipeline.json")
    parser.add_argument("--config", default="config.yaml", help="Phase4 config file")
    parser.add_argument("--voice", help="Voice ID override (keys from configs/voice_references.json)")
    parser.add_argument("--device", default="cpu", help="Device (cpu/cuda)")
    parser.add_argument("--workers", type=int, default=2, help="Parallel workers for chunk synthesis")
    parser.add_argument("--language", help="Override language (defaults to config value)")
    parser.add_argument("--chunk_id", type=int, help="Optional chunk index to synthesize (legacy compatibility)")
    parser.add_argument(
        "--disable_fallback",
        action="store_true",
        help="Disables cascading to other engines on failure (per-process fallback).",
    )

    args = parser.parse_args()

    json_path = Path(args.json_path).resolve()
    config_path = MODULE_ROOT.parent / args.config
    voices_config_path = MODULE_ROOT.parent / "configs" / "voice_references.json"

    config = load_config(config_path)
    pipeline_data = load_pipeline_json(json_path)

    resolved_file_id, chunks = collect_chunks(
        pipeline_data,
        args.file_id,
        chunk_index=args.chunk_id,
    )
    if not chunks:
        logger.error("No chunks discovered for %s", args.file_id)
        return 1

    voice_references = prepare_voice_references(
        voice_config_path=str(voices_config_path),
        cache_dir=str(MODULE_ROOT.parent / "voice_references"),
    )
    voice_id, reference_audio, engine_params = select_voice(
        json_path, resolved_file_id, args.voice, voice_references, voices_config_path
    )

    output_dir = Path(config.get("audio_chunks_dir", "audio_chunks")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Lazy-load only needed engines for isolation
    engines_to_load = [args.engine] if args.disable_fallback else None
    manager = build_engine_manager(args.device, engines=engines_to_load)
    manager.set_default_engine(args.engine)

    language = args.language or config.get("language", "en")
    workers = max(1, args.workers)

    logger.info("=" * 80)
    logger.info("Phase 4 Multi-Engine TTS")
    logger.info("File ID      : %s", resolved_file_id)
    logger.info("Voice        : %s", voice_id)
    logger.info("Engine (req) : %s", args.engine)
    logger.info("Language     : %s", language)
    logger.info("Chunks       : %d", len(chunks))
    logger.info("Workers      : %d", workers)
    logger.info("Reference    : %s", reference_audio)
    logger.info("=" * 80)

    start_time = time.time()
    results: List[ChunkResult] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(
                synthesize_chunk_with_engine,
                chunk,
                reference_audio,
                manager,
                args.engine,
                output_dir,
                language,
                allow_fallback=not args.disable_fallback,
                engine_kwargs=engine_params,
            ): chunk.chunk_id
            for chunk in chunks
        }

        for future in as_completed(future_map):
            result = future.result()
            results.append(result)

    duration = time.time() - start_time
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    logger.info("-" * 80)
    logger.info("Completed in %.1fs (%0.1fs/chunk)", duration, duration / max(1, len(results)))
    logger.info("Success: %d | Failed: %d", success_count, failed_count)
    logger.info("-" * 80)

    update_phase4_summary(
        pipeline_path=json_path,
        file_id=resolved_file_id,
        voice_id=voice_id,
        requested_engine=args.engine,
        results=results,
        output_dir=output_dir,
        duration_sec=duration,
    )

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
