"""Multi-engine Phase 4 entry point with schema-aware pipeline writes.

Why:
- Honors the current pipeline.json layout (phase-scoped, slugged lookups)
- Shares reference preparation and text sanitation logic with main.py
- Records which engine actually produced audio when fallbacks kick in
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor
from concurrent.futures import wait
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf
import yaml
try:
    import psutil
except ImportError:  # psutil is optional; CPU guard will be disabled if missing
    psutil = None

MODULE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_ROOT.parent.parent
DEFAULT_CHARS_PER_MINUTE = 2700  # CPU XTTS cadence heuristic
from pipeline_common.astromech_notify import play_success_beep, play_alert_beep

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
    rt_factor: Optional[float] = None
    audio_duration: Optional[float] = None
    latency_fallback_used: bool = False
    error: Optional[str] = None


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_pipeline_json(json_path: Path) -> Dict[str, Any]:
    if not json_path.exists():
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def estimate_audio_seconds(chunks: List[ChunkPayload], chars_per_min: int = DEFAULT_CHARS_PER_MINUTE) -> float:
    """Estimate total audio length (seconds) from chunk text sizes."""
    if chars_per_min <= 0:
        chars_per_min = DEFAULT_CHARS_PER_MINUTE
    total_chars = sum(len(c.text) for c in chunks)
    return (total_chars / chars_per_min) * 60.0


def choose_engine_auto(
    chunks: List[ChunkPayload],
    preferred: str,
    rt_xtts: float = 3.2,
    rt_kokoro: float = 1.3,
    chars_per_min: int = DEFAULT_CHARS_PER_MINUTE,
) -> Tuple[str, str]:
    """
    Heuristic engine selector: pick Kokoro when estimated XTTS wall time greatly exceeds Kokoro.
    Returns (engine_name, reason).
    """
    est_audio = estimate_audio_seconds(chunks, chars_per_min=chars_per_min)
    xtts_time = est_audio * rt_xtts
    kokoro_time = est_audio * rt_kokoro

    if xtts_time > kokoro_time * 1.3:
        reason = (
            f"Estimated XTTS wall {xtts_time/3600:.2f}h vs Kokoro {kokoro_time/3600:.2f}h; "
            "selecting Kokoro for throughput."
        )
        return "kokoro", reason

    return preferred, "Using preferred engine (throughput acceptable)."


def normalize_pipeline_path(raw_path: str, pipeline_json: Optional[Path] = None) -> Path:
    """Resolve chunk paths saved in pipeline.json to an existing absolute path."""
    if not raw_path:
        raise FileNotFoundError("Empty chunk path")

    normalized = raw_path.strip().strip('"')
    expanded = Path(normalized).expanduser()

    candidates: List[Path] = []
    candidates.append(expanded)

    if not expanded.is_absolute():
        candidates.append((PROJECT_ROOT / normalized).resolve())

    if pipeline_json:
        candidates.append((pipeline_json.parent / normalized).resolve())

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
    pipeline_json: Optional[Path] = None,
    enable_g2p: bool = False,
    normalize_numbers: bool = True,
    custom_overrides: Optional[Dict[str, str]] = None,
) -> Tuple[str, List[ChunkPayload]]:
    """Load chunk paths from phase3 section and sanitize text for synthesis."""
    resolved_key, phase3_entry = resolve_pipeline_file(pipeline_data, "phase3", file_id)

    chunk_paths = phase3_entry.get("chunk_paths", []) if phase3_entry else []

    # Fallback: glob phase3b_chunks if pipeline lacks phase3 entry (or empty)
    if not chunk_paths:
        fallback_dir = PROJECT_ROOT / "phase3b_chunks" / file_id
        if fallback_dir.exists():
            chunk_paths = sorted(str(p) for p in fallback_dir.glob("chunk_*.txt"))
            if chunk_paths:
                logger.warning(
                    "Phase 3 entry missing for '%s'; using filesystem chunks at %s",
                    file_id,
                    fallback_dir,
                )
                resolved_key = file_id

    if not chunk_paths:
        raise ValueError(f"No chunk paths recorded for '{file_id}'.")

    chunk_payloads: List[ChunkPayload] = []
    for index, raw_path in enumerate(chunk_paths):
        chunk_path = normalize_pipeline_path(raw_path, pipeline_json=pipeline_json)
        if not chunk_path.exists():
            raise FileNotFoundError(f"Chunk file not found: {raw_path}")

        text = chunk_path.read_text(encoding="utf-8").strip()
        if not text:
            logger.warning("Chunk %s is empty: %s", index, chunk_path)
            continue

        chunk_id = derive_chunk_id(chunk_path, index)
        sanitized = sanitize_text_for_tts(
            text,
            enable_g2p=enable_g2p,
            normalize_numbers=normalize_numbers,
            custom_overrides=custom_overrides,
        )
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
    enable_latency_fallback: bool = True,
    slow_rt_threshold: float = 4.0,
    engine_kwargs: Optional[Dict[str, Any]] = None,
    skip_existing: bool = False,
) -> ChunkResult:
    """Synthesize text for a single chunk using requested engine with fallback."""
    chunk_kwargs = dict(engine_kwargs) if engine_kwargs else {}
    existing_out = output_dir / f"{chunk.chunk_id}.wav"

    # Resume support: skip already-rendered chunks
    if skip_existing and existing_out.exists():
        logger.info("Skipping %s (already exists)", chunk.chunk_id)
        return ChunkResult(
            chunk_id=chunk.chunk_id,
            success=True,
            output_path=existing_out,
            engine_used=None,
            rt_factor=None,
            audio_duration=None,
            latency_fallback_used=False,
        )

    synth_start = time.time()
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
        return ChunkResult(
            chunk_id=chunk.chunk_id,
            success=False,
            output_path=None,
            engine_used=None,
            rt_factor=None,
            audio_duration=None,
            latency_fallback_used=False,
            error=str(exc),
        )

    synth_elapsed = time.time() - synth_start

    audio = np.asarray(audio_out, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=0)
    audio = np.clip(audio, -1.0, 1.0)

    sample_rate = engine_manager.get_engine(used_engine).get_sample_rate()
    audio_duration = len(audio) / sample_rate if sample_rate else 0.0
    rt_factor = synth_elapsed / max(audio_duration, 1e-6) if audio_duration else float("inf")
    latency_fallback_used = False
    logger.info(
        "Chunk %s via '%s': wall %.2fs, audio %.2fs, RT x%.2f",
        chunk.chunk_id,
        used_engine,
        synth_elapsed,
        audio_duration,
        rt_factor,
    )

    # Latency-driven fallback: if primary is very slow and Kokoro is available, try once.
    kokoro_available = "kokoro" in engine_manager.engines
    if (
        enable_latency_fallback
        and allow_fallback
        and used_engine != "kokoro"
        and rt_factor > slow_rt_threshold
        and kokoro_available
    ):
        logger.warning(
            "Chunk %s RT x%.2f exceeds %.1f; attempting Kokoro fallback for speed",
            chunk.chunk_id,
            rt_factor,
            slow_rt_threshold,
        )
        try:
            fallback_start = time.time()
            fallback_audio, fallback_engine = engine_manager.synthesize(
                text=chunk.text,
                reference_audio=reference_audio,
                engine="kokoro",
                language=language,
                fallback=False,
                return_engine=True,
                **chunk_kwargs,
            )
            fallback_elapsed = time.time() - fallback_start
            fallback_audio = np.asarray(fallback_audio, dtype=np.float32)
            if fallback_audio.ndim > 1:
                fallback_audio = fallback_audio.mean(axis=0)
            fallback_audio = np.clip(fallback_audio, -1.0, 1.0)
            kokoro_sr = engine_manager.get_engine(fallback_engine).get_sample_rate()
            kokoro_dur = len(fallback_audio) / kokoro_sr if kokoro_sr else 0.0
            kokoro_rt = fallback_elapsed / max(kokoro_dur, 1e-6) if kokoro_dur else float("inf")

            # Replace audio if Kokoro is materially faster or XTTS was effectively stalled.
            if kokoro_rt < rt_factor or rt_factor == float("inf"):
                audio = fallback_audio
                sample_rate = kokoro_sr
                used_engine = fallback_engine
                rt_factor = kokoro_rt
                audio_duration = kokoro_dur
                latency_fallback_used = True
                logger.info(
                    "Chunk %s switched to Kokoro: wall %.2fs, audio %.2fs, RT x%.2f",
                    chunk.chunk_id,
                    fallback_elapsed,
                    kokoro_dur,
                    kokoro_rt,
                )
            else:
                logger.info(
                    "Chunk %s kept primary '%s' (fallback RT x%.2f not better)",
                    chunk.chunk_id,
                    used_engine,
                    kokoro_rt,
                )
        except Exception as fallback_exc:  # pylint: disable=broad-except
            logger.warning(
                "Chunk %s Kokoro latency fallback failed: %s", chunk.chunk_id, fallback_exc
            )

    if rt_factor > slow_rt_threshold:
        logger.warning(
            "Chunk %s final RT x%.2f remains above threshold %.1f; consider Kokoro or shorter chunks.",
            chunk.chunk_id,
            rt_factor,
            slow_rt_threshold,
        )

    output_path = output_dir / f"{chunk.chunk_id}.wav"
    sf.write(output_path, audio, sample_rate)

    logger.info("Chunk %s synthesized via '%s' → %s", chunk.chunk_id, used_engine, output_path)
    return ChunkResult(
        chunk_id=chunk.chunk_id,
        success=True,
        output_path=output_path,
        engine_used=used_engine,
        rt_factor=rt_factor,
        audio_duration=audio_duration,
        latency_fallback_used=latency_fallback_used,
    )


def update_phase4_summary(
    pipeline_path: Path,
    file_id: str,
    voice_id: str,
    requested_engine: str,
    selected_engine: str,
    slow_rt_threshold: float,
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
    rt_factors = [
        r.rt_factor for r in results if r.success and r.rt_factor is not None and np.isfinite(r.rt_factor)
    ]
    avg_rt_factor = float(np.mean(rt_factors)) if rt_factors else None
    latency_fallback_count = sum(1 for r in results if r.latency_fallback_used)
    fallback_rate = (
        float(latency_fallback_count) / max(1, completed) if completed else None
    )
    rt_p50 = float(np.percentile(rt_factors, 50)) if rt_factors else None
    rt_p90 = float(np.percentile(rt_factors, 90)) if rt_factors else None
    rt_p99 = float(np.percentile(rt_factors, 99)) if rt_factors else None
    advisory: Optional[str] = None
    if completed and rt_p90 and rt_p90 > slow_rt_threshold:
        advisory = (
            f"High RT: p90={rt_p90:.2f}x > threshold {slow_rt_threshold:.1f}. "
            "Consider --cpu_safe, --workers 2, --auto_engine, or lowering slow-rt-threshold."
        )
    if completed and fallback_rate is not None and fallback_rate > 0.2:
        extra = " High latency fallback usage (>20%)."
        advisory = (advisory + extra) if advisory else ("High latency fallback usage (>20%). " "Consider Kokoro.")

    file_entry: Dict[str, Any] = {
        "status": "success" if failed == 0 else "partial",
        "voice_id": voice_id,
        "requested_engine": requested_engine,
        "selected_engine": selected_engine,
        "engines_used": engines_used,
        "total_chunks": total,
        "chunks_completed": completed,
        "chunks_failed": failed,
        "audio_dir": serialize_path_for_pipeline(output_dir),
        "chunk_audio_paths": [
            serialize_path_for_pipeline(r.output_path) for r in results if r.success and r.output_path
        ],
        "duration_seconds": duration_sec,
        "avg_rt_factor": avg_rt_factor,
        "latency_fallback_chunks": latency_fallback_count,
        "fallback_rate": fallback_rate,
        "rt_p50": rt_p50,
        "rt_p90": rt_p90,
        "rt_p99": rt_p99,
        "advisory": advisory,
    }

    for result in results:
        file_entry[result.chunk_id] = {
            "chunk_id": result.chunk_id,
            "audio_path": serialize_path_for_pipeline(result.output_path) if result.output_path else None,
            "status": "success" if result.success else "failed",
            "engine_used": result.engine_used,
            "rt_factor": result.rt_factor,
            "audio_seconds": result.audio_duration,
            "latency_fallback_used": result.latency_fallback_used,
            "errors": [] if result.success else [result.error or "unknown error"],
        }

    files_section[file_id] = file_entry

    if files_section and all(entry.get("status") == "success" for entry in files_section.values()):
        phase4["status"] = "success"
    else:
        phase4["status"] = "partial"

    with open(pipeline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


ENGINE_IMPORT_MAP: Dict[str, Tuple[str, str]] = {
    "xtts": ("engines.xtts_engine", "XTTSEngine"),
    "kokoro": ("engines.kokoro_engine", "KokoroEngine"),
}


def build_engine_manager(device: str, engines: Optional[List[str]] = None) -> EngineManager:
    """Build engine manager while skipping engines whose deps are unavailable."""
    manager = EngineManager(device=device)

    # Lazy import only requested engines to avoid dep conflicts
    if engines is None:
        engines = list(ENGINE_IMPORT_MAP.keys())

    for engine_name in engines:
        module_info = ENGINE_IMPORT_MAP.get(engine_name)
        if not module_info:
            logger.warning("Unknown engine '%s' requested; skipping registration.", engine_name)
            continue

        module_path, class_name = module_info
        try:
            module = importlib.import_module(module_path)
            engine_class = getattr(module, class_name)
        except ModuleNotFoundError as exc:
            logger.warning(
                "Skipping engine '%s' because dependencies are missing (%s).", engine_name, exc
            )
            continue
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to import engine '%s': %s", engine_name, exc)
            continue

        manager.register_engine(engine_name, engine_class)

    if not manager.engines:
        raise RuntimeError(
            f"No TTS engines could be registered for device '{device}'. "
            "Check per-engine environments or dependency installs."
        )

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
    parser.add_argument(
        "--slow-rt-threshold",
        type=float,
        help="Real-time factor threshold to trigger Kokoro latency fallback (default from config or 4.0).",
    )
    parser.add_argument(
        "--disable_latency_fallback",
        action="store_true",
        help="Disable latency-based Kokoro fallback even if enabled in config.",
    )
    parser.add_argument(
        "--play_notification",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Play astromech beep on completion/failure (default: ON)",
    )
    parser.add_argument(
        "--silence_notifications",
        action="store_true",
        help="Silence astromech notifications (beeps are ON by default)",
    )
    parser.add_argument(
        "--auto_engine",
        action="store_true",
        help="Enable heuristic engine selection (Kokoro when XTTS throughput would be much slower).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip chunks whose output WAV already exists (resume support).",
    )
    parser.add_argument(
        "--cpu_safe",
        action="store_true",
        help="CPU-friendly preset: clamp workers to Ryzen-safe values, force latency fallbacks on, and enable auto-engine selection.",
    )
    parser.add_argument(
        "--cpu_guard",
        action="store_true",
        help="Dynamically reduce workers when system CPU usage is high (requires psutil; enabled automatically with --cpu_safe).",
    )
    parser.add_argument(
        "--cpu_guard_high",
        type=float,
        help="CPU usage percent threshold to start downscaling workers (default 85%%; only used when cpu_guard is on).",
    )
    parser.add_argument(
        "--rt_budget_hours",
        type=float,
        help="Optional wall-clock budget (hours). If estimated time exceeds budget, suggest safer settings and prefer Kokoro.",
    )

    args = parser.parse_args()

    json_path = Path(args.json_path).resolve()
    config_path = MODULE_ROOT.parent / args.config
    voices_config_path = MODULE_ROOT.parent / "configs" / "voice_references.json"

    config = load_config(config_path)
    pipeline_data = load_pipeline_json(json_path)
    enable_g2p = bool(config.get("enable_g2p", False))
    normalize_numbers = bool(config.get("normalize_numbers", True))
    custom_overrides = config.get("custom_pronunciations", {}) or None
    cpu_safe = bool(args.cpu_safe)
    cpu_guard = bool(args.cpu_guard or cpu_safe)
    cpu_guard_high = float(args.cpu_guard_high if args.cpu_guard_high is not None else 85.0)
    enable_latency_fallback = not args.disable_latency_fallback and bool(
        config.get("enable_latency_fallback", True)
    )
    if cpu_safe:
        enable_latency_fallback = True  # Always allow faster fallback when CPU-safe mode is requested.
    rt_budget_hours = args.rt_budget_hours
    slow_rt_threshold = float(
        args.slow_rt_threshold
        if args.slow_rt_threshold is not None
        else config.get("slow_rt_threshold", 4.0)
    )
    if cpu_safe:
        slow_rt_threshold = min(slow_rt_threshold, 3.5)  # Prefer earlier fallback when protecting CPU thermals.

    resolved_file_id, chunks = collect_chunks(
        pipeline_data,
        args.file_id,
        chunk_index=args.chunk_id,
        pipeline_json=json_path,
        enable_g2p=enable_g2p,
        normalize_numbers=normalize_numbers,
        custom_overrides=custom_overrides,
    )
    if not chunks:
        logger.error("No chunks discovered for %s", args.file_id)
        if args.play_notification is not False and not args.silence_notifications:
            play_alert_beep(silence_mode=False)
        return 1

    engine_requested = args.engine
    engine_selected = engine_requested
    auto_engine_enabled = args.auto_engine or cpu_safe
    est_audio_seconds = estimate_audio_seconds(
        chunks, chars_per_min=int(config.get("chars_per_minute", DEFAULT_CHARS_PER_MINUTE))
    )
    if auto_engine_enabled:
        engine_selected, reason = choose_engine_auto(
            chunks,
            preferred=engine_requested,
            rt_xtts=float(config.get("rt_xtts_factor", 3.2)),
            rt_kokoro=float(config.get("rt_kokoro_factor", 1.3)),
            chars_per_min=int(config.get("chars_per_minute", DEFAULT_CHARS_PER_MINUTE)),
        )
        logger.info("Auto-engine decision: %s (requested=%s, selected=%s)", reason, engine_requested, engine_selected)
    else:
        logger.info("Auto-engine disabled. Using requested engine: %s", engine_requested)
    if cpu_safe:
        logger.info("CPU-safe mode: enforcing conservative throughput (workers capped, latency fallback always on).")
    if rt_budget_hours:
        rt_factor_hint = float(config.get("rt_xtts_factor", 3.2) if engine_selected == "xtts" else config.get("rt_kokoro_factor", 1.3))
        est_wall = est_audio_seconds * rt_factor_hint
        budget_seconds = rt_budget_hours * 3600.0
        if est_wall > budget_seconds:
            logger.warning(
                "Estimated wall-clock %.1fh exceeds RT budget %.1fh (engine=%s). Consider Kokoro, cpu_safe, or fewer workers.",
                est_wall / 3600.0,
                rt_budget_hours,
                engine_selected,
            )
            if cpu_safe and engine_selected == "xtts":
                logger.info("CPU-safe + budget: biasing to Kokoro for throughput.")
                engine_selected = "kokoro"
            best_case_rt = float(min(config.get("rt_xtts_factor", 3.2), config.get("rt_kokoro_factor", 1.3)))
            best_case_wall = est_audio_seconds * best_case_rt
            if best_case_wall > budget_seconds:
                logger.warning(
                    "Even best-case (fastest RT factor %.2f) estimated wall %.1fh exceeds budget %.1fh. Expect overrun.",
                    best_case_rt,
                    best_case_wall / 3600.0,
                    rt_budget_hours,
                )

    if args.play_notification is None:
        args.play_notification = True  # Default ON unless explicitly disabled elsewhere
    if args.play_notification and not args.silence_notifications:
        logger.info("Astromech notifications: ON (use --silence_notifications to mute).")
    if cpu_guard:
        logger.info("CPU guard: enabled (threshold %.1f%%; requires psutil).", cpu_guard_high)

    voice_references = prepare_voice_references(
        voice_config_path=str(voices_config_path),
        cache_dir=str(MODULE_ROOT.parent / "voice_references"),
    )
    voice_id, reference_audio, engine_params = select_voice(
        json_path, resolved_file_id, args.voice, voice_references, voices_config_path
    )

    base_output = Path(config.get("audio_chunks_dir", "audio_chunks")).resolve()
    output_dir = base_output / resolved_file_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Lazy-load only needed engines for isolation
    engines_to_load = [engine_selected] if args.disable_fallback else None
    manager = build_engine_manager(args.device, engines=engines_to_load)
    manager.set_default_engine(engine_selected)

    language = args.language or config.get("language", "en")
    workers = max(1, args.workers)
    cpu_worker_cap = 3
    if cpu_safe and workers > cpu_worker_cap:
        logger.info(
            "CPU-safe mode: clamping workers to %d for Ryzen stability (requested %d)",
            cpu_worker_cap,
            workers,
        )
        workers = cpu_worker_cap
    elif workers > cpu_worker_cap:
        logger.info(
            "Capping workers to %d for CPU stability on Ryzen 5 (requested %d)",
            cpu_worker_cap,
            workers,
        )
        workers = cpu_worker_cap
    skip_existing = bool(args.resume)

    if cpu_guard and psutil is None:
        logger.warning(
            "CPU guard requested but psutil is not installed; skipping CPU usage-based scaling."
        )
        cpu_guard = False

    logger.info("=" * 80)
    logger.info("Phase 4 Multi-Engine TTS")
    logger.info("File ID      : %s", resolved_file_id)
    logger.info("Voice        : %s", voice_id)
    logger.info("Engine (req) : %s", engine_requested)
    logger.info("Engine (use) : %s", engine_selected)
    logger.info("Language     : %s", language)
    logger.info("Chunks       : %d", len(chunks))
    logger.info("Workers      : %d", workers)
    logger.info("Reference    : %s", reference_audio)
    logger.info("=" * 80)

    start_time = time.time()
    results: List[ChunkResult] = []
    allowed_workers = workers
    slow_streak = 0
    cpu_high_streak = 0
    pending = list(chunks)
    active_futures: Dict[Any, str] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        while pending or active_futures:
            # Fill the queue up to the current allowed concurrency
            while pending and len(active_futures) < allowed_workers:
                chunk = pending.pop(0)
                future = executor.submit(
                    synthesize_chunk_with_engine,
                    chunk,
                    reference_audio,
                    manager,
                    engine_selected,
                    output_dir,
                    language,
                    allow_fallback=not args.disable_fallback,
                    enable_latency_fallback=enable_latency_fallback,
                    slow_rt_threshold=slow_rt_threshold,
                    engine_kwargs=engine_params,
                    skip_existing=skip_existing,
                )
                active_futures[future] = chunk.chunk_id

            if not active_futures:
                break

            done, _ = wait(active_futures, return_when=FIRST_COMPLETED)
            for future in done:
                active_futures.pop(future, None)
                result = future.result()
                results.append(result)

                if (
                    cpu_safe
                    and result.success
                    and result.rt_factor is not None
                    and np.isfinite(result.rt_factor)
                    and result.rt_factor > slow_rt_threshold
                ):
                    slow_streak += 1
                else:
                    slow_streak = 0

                if cpu_safe and allowed_workers > 1 and slow_streak >= 2:
                    allowed_workers -= 1
                    slow_streak = 0
                    logger.warning(
                        "Adaptive worker scaling: reducing workers to %d after consecutive slow chunks (threshold %.1f).",
                        allowed_workers,
                        slow_rt_threshold,
                    )

                if cpu_guard and allowed_workers > 1 and psutil is not None:
                    cpu_usage = psutil.cpu_percent(interval=None)
                    if cpu_usage >= cpu_guard_high:
                        cpu_high_streak += 1
                    else:
                        cpu_high_streak = 0

                    if cpu_high_streak >= 2:
                        allowed_workers -= 1
                        cpu_high_streak = 0
                        logger.warning(
                            "CPU guard: reducing workers to %d due to high CPU usage (%.1f%% over threshold %.1f).",
                            allowed_workers,
                            cpu_usage,
                            cpu_guard_high,
                        )

    duration = time.time() - start_time
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    logger.info("-" * 80)
    logger.info("Completed in %.1fs (%0.1fs/chunk)", duration, duration / max(1, len(results)))
    logger.info("Success: %d | Failed: %d", success_count, failed_count)
    rt_values = [
        r.rt_factor for r in results if r.success and r.rt_factor is not None and np.isfinite(r.rt_factor)
    ]
    if rt_values:
        rt_p50 = float(np.percentile(rt_values, 50))
        rt_p90 = float(np.percentile(rt_values, 90))
        rt_p99 = float(np.percentile(rt_values, 99))
        fallback_rate = sum(1 for r in results if r.latency_fallback_used and r.success) / max(
            1, success_count
        )
        logger.info(
            "RT factors p50=%.2fx p90=%.2fx p99=%.2fx | latency fallback rate=%.1f%%",
            rt_p50,
            rt_p90,
            rt_p99,
            fallback_rate * 100.0,
        )
        if rt_p90 > slow_rt_threshold:
            logger.warning(
                "High RT p90=%.2fx above threshold %.1f; consider --cpu_safe, --workers 2, or --auto_engine.",
                rt_p90,
                slow_rt_threshold,
            )
        if fallback_rate > 0.2:
            logger.warning(
                "Latency fallback used on %.1f%% of chunks; Kokoro may be preferable for this run.",
                fallback_rate * 100.0,
            )
    logger.info("-" * 80)

    update_phase4_summary(
        pipeline_path=json_path,
        file_id=resolved_file_id,
        voice_id=voice_id,
        requested_engine=engine_requested,
        selected_engine=engine_selected,
        slow_rt_threshold=slow_rt_threshold,
        results=results,
        output_dir=output_dir,
        duration_sec=duration,
    )

    exit_code = 0 if failed_count == 0 else 1
    if args.play_notification is not False and not args.silence_notifications:
        if exit_code == 0:
            play_success_beep(silence_mode=False)
        else:
            play_alert_beep(silence_mode=False)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
