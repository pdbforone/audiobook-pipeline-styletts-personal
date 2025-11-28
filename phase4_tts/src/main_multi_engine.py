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
except (
    ImportError
):  # psutil is optional; CPU guard will be disabled if missing
    psutil = None
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from pipeline_common import (
    PipelineState,
    ensure_phase_and_file,
    ensure_phase_block,
)
from pipeline_common.astromech_notify import play_alert_beep, play_success_beep
from pipeline_common.state_manager import StateTransaction
from io_helpers import validate_audio_file

# ASR validation (opt-in)
try:
    from asr_validator import ASRValidator
except ImportError:
    ASRValidator = None  # type: ignore

# Llama rewriter for ASR-driven fixes (opt-in)
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agents.llama_rewriter import LlamaRewriter
except ImportError:
    LlamaRewriter = None  # type: ignore

MODULE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_ROOT.parent.parent
DEFAULT_CHARS_PER_MINUTE = 1050  # Shared speaking cadence assumption


if not hasattr(StateTransaction, "update_phase"):

    def _phase4_update_phase(  # type: ignore[override]
        self,
        file_id: str,
        phase_name: str,
        status: str,
        timestamps: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Any]] = None,
        *,
        chunks: Optional[List[Dict[str, Any]]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        phase_block, file_entry = ensure_phase_and_file(
            self.data, phase_name, file_id
        )

        envelope = file_entry

        envelope["status"] = status

        envelope["timestamps"] = dict(timestamps or {})

        envelope["artifacts"] = dict(artifacts or {})

        envelope["metrics"] = dict(metrics or {})

        envelope["errors"] = list(errors or [])

        envelope["chunks"] = list(chunks or [])

        if extra_fields:

            envelope.update(extra_fields)

        return envelope

    setattr(StateTransaction, "update_phase", _phase4_update_phase)


# Add engines + shared utils to path
sys.path.insert(0, str(MODULE_ROOT.parent))

from engines.engine_manager import EngineManager  # noqa: E402

try:  # Import as package when executed via `python -m`
    from .utils import (
        get_selected_voice_from_phase3,
        prepare_voice_references,
        resolve_pipeline_file,
        sanitize_text_for_tts,
    )
    from .validation import (
        ValidationConfig,
        tier1_validate,
        tier2_validate,
        predict_expected_duration,
        should_run_tier2_validation,
    )
except (
    ImportError
):  # Fallback for CLI execution (`python src/main_multi_engine.py`)
    sys.path.insert(0, str(MODULE_ROOT))
    from utils import (  # type: ignore  # pylint: disable=import-error
        get_selected_voice_from_phase3,
        prepare_voice_references,
        resolve_pipeline_file,
        sanitize_text_for_tts,
    )
    from validation import (  # type: ignore  # pylint: disable=import-error
        ValidationConfig,
        tier1_validate,
        tier2_validate,
        predict_expected_duration,
        should_run_tier2_validation,
    )

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@dataclass(slots=True)
class ChunkPayload:
    chunk_id: str
    text: str
    source_path: Path
    voice_override: Optional[str] = None
    index: Optional[int] = None


@dataclass(slots=True)
class ChunkResult:
    chunk_id: str
    success: bool
    output_path: Optional[Path]
    engine_used: Optional[str]
    rt_factor: Optional[float] = None
    audio_duration: Optional[float] = None
    text_len: Optional[int] = None
    est_dur: Optional[float] = None
    latency_fallback_used: bool = False
    voice_used: Optional[str] = None
    error: Optional[str] = None
    validation_tier: Optional[int] = None
    validation_reason: Optional[str] = None
    validation_details: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class VoiceAsset:
    voice_id: str
    reference_audio: Optional[Path]
    engine_params: Dict[str, Any]
    preferred_engine: Optional[str] = None


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_voices_config(voices_config_path: Path) -> Dict[str, Any]:
    try:
        with open(voices_config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Voice config not found at %s", voices_config_path)
        return {}
    except json.JSONDecodeError as exc:
        logger.error(
            "Voice config at %s is invalid JSON: %s", voices_config_path, exc
        )
        return {}


def load_pipeline_json(json_path: Path) -> Dict[str, Any]:
    state = PipelineState(json_path, validate_on_read=False)
    try:
        return state.read(validate=False)
    except FileNotFoundError:
        logger.info(
            "Pipeline JSON not found at %s, starting fresh.", json_path
        )
        return {}


def estimate_audio_seconds(
    chunks: List[ChunkPayload], chars_per_min: int = DEFAULT_CHARS_PER_MINUTE
) -> float:
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


def normalize_pipeline_path(
    raw_path: str, pipeline_json: Optional[Path] = None
) -> Path:
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
    if (
        len(parts) >= 3
        and parts[0] == "/"
        and parts[1] == "mnt"
        and len(parts[2]) == 1
    ):
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
    resolved_key, phase3_entry = resolve_pipeline_file(
        pipeline_data, "phase3", file_id
    )

    chunk_paths = phase3_entry.get("chunk_paths", []) if phase3_entry else []
    voice_overrides_map: Dict[str, str] = {}
    if phase3_entry:
        voice_overrides_map = (
            phase3_entry.get("chunk_voice_overrides")
            or phase3_entry.get("voice_overrides")
            or {}
        )

    # Fallback: glob phase3b_chunks if pipeline lacks phase3 entry (or empty)
    if not chunk_paths:
        fallback_dir = PROJECT_ROOT / "phase3b_chunks" / file_id
        if fallback_dir.exists():
            chunk_paths = sorted(
                str(p) for p in fallback_dir.glob("chunk_*.txt")
            )
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
        chunk_path = normalize_pipeline_path(
            raw_path, pipeline_json=pipeline_json
        )
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
        voice_override = None
        if voice_overrides_map:
            # Allow matching by chunk_id or file name (with/without extension)
            voice_override = voice_overrides_map.get(chunk_id)
            if not voice_override:
                voice_override = voice_overrides_map.get(chunk_path.name)
                if not voice_override:
                    voice_override = voice_overrides_map.get(chunk_path.stem)
        chunk_payloads.append(
            ChunkPayload(
                chunk_id, sanitized, chunk_path, voice_override, index
            )
        )

    if chunk_index is not None:
        if chunk_index < 0 or chunk_index >= len(chunk_payloads):
            raise ValueError(
                f"Chunk index {chunk_index} out of range (0-{len(chunk_payloads) - 1})"
            )
        chunk_payloads = [chunk_payloads[chunk_index]]

    if not chunk_payloads:
        raise ValueError(
            f"All chunk files for '{file_id}' were empty or missing."
        )

    resolved = resolved_key or file_id
    if resolved != file_id:
        logger.info(
            "Resolved file_id '%s' to '%s' based on phase3 data",
            file_id,
            resolved,
        )

    return resolved, chunk_payloads


def select_voice(
    pipeline_json: Path,
    file_id: str,
    voice_override: Optional[str],
    prepared_refs: Dict[str, str],
    voices_config_path: Path,
    voices_config: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[Path], Dict[str, Any]]:
    """Determine voice to use and return (voice_id, reference_path, engine_params).

    Returns:
        Tuple of (voice_id, reference_path, engine_params)
        - For built-in voices: reference_path is None, voice name is in engine_params
        - For custom clones: reference_path points to audio file
    """
    voices_config = voices_config or load_voices_config(voices_config_path)

    voice_entries = voices_config.get("voice_references", {})
    built_in_voices = voices_config.get("built_in_voices", {})
    default_voice = voices_config.get("default_voice")

    # Determine which voice to use
    selected_voice = voice_override or get_selected_voice_from_phase3(
        str(pipeline_json), file_id
    )

    if not selected_voice:
        # Default to first built-in Kokoro voice or first prepared ref
        if built_in_voices.get("kokoro"):
            selected_voice = next(iter(built_in_voices["kokoro"].keys()))
            logger.info(
                "No voice selection. Using default built-in: '%s'",
                selected_voice,
            )
        elif prepared_refs:
            selected_voice = default_voice or next(iter(prepared_refs.keys()))
            logger.info(
                "No voice selection. Using default custom: '%s'",
                selected_voice,
            )
        else:
            raise RuntimeError(
                "No voices available (neither built-in nor custom)"
            )

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
        logger.info(
            "Using built-in voice '%s' from %s engine",
            selected_voice,
            built_in_engine,
        )
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
                selected_voice,
                fallback_voice,
            )
            return select_voice(
                pipeline_json,
                file_id,
                fallback_voice,
                prepared_refs,
                voices_config_path,
                voices_config=voices_config,
            )

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

    logger.info(
        "Using custom voice clone '%s' with reference audio", selected_voice
    )
    reference_path = Path(prepared_refs[selected_voice]).resolve()
    engine_params = voice_entries.get(selected_voice, {}).get(
        "tts_engine_params", {}
    )

    return selected_voice, reference_path, engine_params


def build_voice_assets(
    voices_config: Dict[str, Any],
    prepared_refs: Dict[str, str],
) -> Dict[str, VoiceAsset]:
    """Precompute per-voice assets for fast lookup (used for per-chunk overrides)."""
    assets: Dict[str, VoiceAsset] = {}
    voice_entries = voices_config.get("voice_references", {}) or {}
    built_in_voices = voices_config.get("built_in_voices", {}) or {}

    for engine_name, engine_voices in built_in_voices.items():
        for voice_name, voice_data in engine_voices.items():
            params = {}
            if engine_name == "xtts":
                params["speaker"] = voice_name
            elif engine_name == "kokoro":
                params["voice"] = voice_name
            params.update(voice_data.get("tts_engine_params", {}))
            assets[voice_name] = VoiceAsset(
                voice_id=voice_name,
                reference_audio=None,
                engine_params=params,
                preferred_engine=engine_name,
            )

    for voice_name, voice_data in voice_entries.items():
        ref_path = prepared_refs.get(voice_name)
        params = dict(voice_data.get("tts_engine_params", {}))
        if voice_name in assets:
            if ref_path:
                assets[voice_name].reference_audio = Path(ref_path)
            continue
        assets[voice_name] = VoiceAsset(
            voice_id=voice_name,
            reference_audio=Path(ref_path).resolve() if ref_path else None,
            engine_params=params,
            preferred_engine=None,
        )

    return assets


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
    voice_assets: Optional[Dict[str, VoiceAsset]] = None,
    default_voice_id: Optional[str] = None,
    validation_config: Optional[ValidationConfig] = None,
    validation_enabled: bool = True,
    chunk_index: Optional[int] = None,
    total_chunks: Optional[int] = None,
    chars_per_minute: Optional[int] = None,
) -> ChunkResult:
    """Synthesize text for a single chunk using requested engine with fallback."""
    chunk_kwargs = dict(engine_kwargs) if engine_kwargs else {}
    effective_engine = engine_name
    reference = reference_audio
    voice_used = default_voice_id
    validation_tier: Optional[int] = None
    validation_reason: Optional[str] = None
    validation_details: Optional[Dict[str, Any]] = None
    effective_cpm = chars_per_minute or DEFAULT_CHARS_PER_MINUTE
    text_len = len(chunk.text)

    if chunk.voice_override and voice_assets:
        voice_asset = voice_assets.get(chunk.voice_override)
        if voice_asset:
            if voice_asset.engine_params:
                chunk_kwargs.update(voice_asset.engine_params)
            if voice_asset.reference_audio:
                reference = voice_asset.reference_audio
            if (
                voice_asset.preferred_engine
                and voice_asset.preferred_engine in engine_manager.engines
            ):
                effective_engine = voice_asset.preferred_engine
            voice_used = voice_asset.voice_id
            logger.info(
                "Chunk %s overriding voice -> %s (engine=%s)",
                chunk.chunk_id,
                voice_asset.voice_id,
                effective_engine,
            )
        else:
            logger.warning(
                "Chunk %s requested voice '%s' but it is not defined; using default voice '%s'.",
                chunk.chunk_id,
                chunk.voice_override,
                voice_used,
            )
    existing_out = output_dir / f"{chunk.chunk_id}.wav"
    est_dur_sec = max(
        1.0,
        predict_expected_duration(chunk.text, chars_per_minute=effective_cpm),
    )

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
            text_len=text_len,
            est_dur=est_dur_sec,
            latency_fallback_used=False,
            voice_used=voice_used,
            validation_tier=None,
            validation_reason=None,
            validation_details=None,
        )

    kokoro_available = "kokoro" in engine_manager.engines

    def standardize_audio(
        raw_audio: np.ndarray, engine_key: str, elapsed: float
    ) -> Tuple[np.ndarray, Optional[int], float, float]:
        """Convert audio to mono float32 and compute duration/RT."""
        audio_arr = np.asarray(raw_audio, dtype=np.float32)
        if audio_arr.ndim > 1:
            audio_arr = audio_arr.mean(axis=0)
        audio_arr = np.clip(audio_arr, -1.0, 1.0)
        sample_rate = engine_manager.get_engine(engine_key).get_sample_rate()
        if not sample_rate:
            sample_rate = 24000
        audio_dur = len(audio_arr) / sample_rate if sample_rate else 0.0
        rt = elapsed / max(audio_dur, 1e-6) if audio_dur else float("inf")
        return audio_arr, sample_rate, audio_dur, rt

    def text_length_limit(target_engine: str) -> Optional[int]:
        """Return max text length for engine if enforced."""
        try:
            engine_obj = engine_manager.get_engine(target_engine)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Chunk %s failed to load engine '%s' for length check: %s",
                chunk.chunk_id,
                target_engine,
                exc,
            )
            raise
        if hasattr(engine_obj, "get_max_text_length"):
            try:
                max_len = engine_obj.get_max_text_length()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "Engine '%s' get_max_text_length failed: %s",
                    target_engine,
                    exc,
                )
                return None
            return max_len
        return None

    def split_into_sentences(text: str, limit: int) -> List[str]:
        """
        Lightweight sentence splitter that respects a hard character limit.

        Falls back to whitespace chunking if a single sentence still exceeds the limit.
        """
        sentences = re.split(r"(?<=[.!?])\\s+", text.strip())
        normalized: List[str] = []
        for sent in sentences:
            if not sent:
                continue
            if len(sent) <= limit:
                normalized.append(sent.strip())
                continue
            # If a sentence is still too long, break it by words into safe windows
            words = sent.split()
            current = []
            current_len = 0
            for word in words:
                wlen = len(word) + (1 if current else 0)
                if current_len + wlen <= limit:
                    current.append(word)
                    current_len += wlen
                else:
                    normalized.append(" ".join(current))
                    current = [word]
                    current_len = len(word)
            if current:
                normalized.append(" ".join(current))
        return [s for s in normalized if s]

    max_len = None
    try:
        max_len = text_length_limit(effective_engine)
    except Exception as exc:  # noqa: BLE001
        return ChunkResult(
            chunk_id=chunk.chunk_id,
            success=False,
            output_path=None,
            engine_used=effective_engine,
            rt_factor=None,
            audio_duration=None,
            text_len=text_len,
            est_dur=est_dur_sec,
            latency_fallback_used=False,
            voice_used=voice_used,
            error=str(exc),
            validation_tier=None,
            validation_reason="engine_load_failed",
            validation_details={"engine": effective_engine},
        )

    sentence_split_enabled = os.getenv("TTS_SENTENCE_SPLIT", "0") == "1"
    sentence_regen_enabled = os.getenv("TTS_SENTENCE_REGEN", "0") == "1"

    def attempt_synthesis(
        target_engine: str,
        allow_fb: bool,
        rtf_threshold: Optional[float],
        *,
        text_override: Optional[str] = None,
    ) -> Tuple[np.ndarray, str, int, float, float]:
        synth_start = time.time()
        audio_out, selected_engine = engine_manager.synthesize(
            text=text_override or chunk.text,
            reference_audio=reference,
            engine=target_engine,
            language=language,
            fallback=allow_fb,
            return_engine=True,
            est_dur_sec=est_dur_sec,
            rtf_fallback_threshold=rtf_threshold,
            **chunk_kwargs,
        )
        elapsed = time.time() - synth_start
        standardized, sample_rate, audio_duration, rt_factor = (
            standardize_audio(audio_out, selected_engine, elapsed)
        )
        return (
            standardized,
            selected_engine,
            sample_rate,
            audio_duration,
            rt_factor,
        )

    if max_len and len(chunk.text) > max_len:
        if sentence_split_enabled:
            sentences = split_into_sentences(chunk.text, max_len)
            if sentences and all(len(s) <= max_len for s in sentences) and len(sentences) > 1:
                try:
                    audio_parts: List[np.ndarray] = []
                    total_duration = 0.0
                    used_engine = effective_engine
                    rt_factor = None
                    sample_rate = None
                    for idx, sent in enumerate(sentences):
                        logger.info(
                            "Chunk %s sentence split %d/%d (len=%d) for engine '%s'",
                            chunk.chunk_id,
                            idx + 1,
                            len(sentences),
                            len(sent),
                            effective_engine,
                        )
                        (
                            sent_audio,
                            used_engine,
                            sample_rate,
                            sent_duration,
                            rt_factor,
                        ) = attempt_synthesis(effective_engine, allow_fallback, 1.1, text_override=sent)
                        audio_parts.append(sent_audio)
                        total_duration += sent_duration or 0.0
                    if audio_parts and sample_rate:
                        audio = np.concatenate(audio_parts)
                        output_path = output_dir / f"{chunk.chunk_id}.wav"
                        sf.write(output_path, audio, sample_rate)
                        return ChunkResult(
                            chunk_id=chunk.chunk_id,
                            success=True,
                            output_path=output_path,
                            engine_used=used_engine,
                            rt_factor=rt_factor,
                            audio_duration=total_duration,
                            text_len=text_len,
                            est_dur=est_dur_sec,
                            latency_fallback_used=False,
                            voice_used=voice_used,
                        )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error(
                        "Chunk %s sentence-split fallback failed: %s",
                        chunk.chunk_id,
                        exc,
                    )

        logger.error(
            "Chunk %s text length %d exceeds max %d for engine '%s'",
            chunk.chunk_id,
            len(chunk.text),
            max_len,
            effective_engine,
        )
        return ChunkResult(
            chunk_id=chunk.chunk_id,
            success=False,
            output_path=None,
            engine_used=effective_engine,
            rt_factor=None,
            audio_duration=None,
            text_len=text_len,
            est_dur=est_dur_sec,
            latency_fallback_used=False,
            voice_used=voice_used,
            error="text too long",
            validation_tier=1,
            validation_reason="text_too_long",
            validation_details={
                "max_length": max_len,
                "text_length": len(chunk.text),
            },
        )

    try:
        audio, used_engine, sample_rate, audio_duration, rt_factor = (
            attempt_synthesis(effective_engine, allow_fallback, 1.1)
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Chunk %s failed on engine '%s': %s",
            chunk.chunk_id,
            engine_name,
            exc,
        )
        if sentence_regen_enabled:
            sentences = split_into_sentences(chunk.text, max_len or len(chunk.text))
            if sentences and len(sentences) > 1:
                logger.info(
                    "Chunk %s attempting sentence-level regeneration after failure.",
                    chunk.chunk_id,
                )
                try:
                    audio_parts: List[np.ndarray] = []
                    total_duration = 0.0
                    used_engine = effective_engine
                    rt_factor = None
                    sample_rate = None
                    for idx, sent in enumerate(sentences):
                        (
                            sent_audio,
                            used_engine,
                            sample_rate,
                            sent_duration,
                            rt_factor,
                        ) = attempt_synthesis(effective_engine, allow_fallback, 1.1, text_override=sent)
                        audio_parts.append(sent_audio)
                        total_duration += sent_duration or 0.0
                    if audio_parts and sample_rate:
                        audio = np.concatenate(audio_parts)
                        audio_duration = total_duration
                        logger.info(
                            "Chunk %s regeneration succeeded with %d sentence segments.",
                            chunk.chunk_id,
                            len(audio_parts),
                        )
                except Exception as regen_exc:  # pylint: disable=broad-except
                    logger.error(
                        "Chunk %s sentence-level regeneration failed: %s",
                        chunk.chunk_id,
                        regen_exc,
                    )
                    return ChunkResult(
                        chunk_id=chunk.chunk_id,
                        success=False,
                        output_path=None,
                        engine_used=None,
                        rt_factor=None,
                        audio_duration=None,
                        text_len=text_len,
                        est_dur=est_dur_sec,
                        latency_fallback_used=False,
                        voice_used=voice_used,
                        error=str(exc),
                    )
            else:
                return ChunkResult(
                    chunk_id=chunk.chunk_id,
                    success=False,
                    output_path=None,
                    engine_used=None,
                    rt_factor=None,
                    audio_duration=None,
                    text_len=text_len,
                    est_dur=est_dur_sec,
                    latency_fallback_used=False,
                    voice_used=voice_used,
                    error=str(exc),
                )
        else:
            return ChunkResult(
                chunk_id=chunk.chunk_id,
                success=False,
                output_path=None,
                engine_used=None,
                rt_factor=None,
                audio_duration=None,
                text_len=text_len,
                est_dur=est_dur_sec,
                latency_fallback_used=False,
                voice_used=voice_used,
                error=str(exc),
            )

    latency_fallback_used = False
    synth_wall = audio_duration * rt_factor if audio_duration else 0.0
    logger.info(
        "Chunk %s via '%s': wall %.2fs, audio %.2fs, RT x%.2f",
        chunk.chunk_id,
        used_engine,
        synth_wall,
        audio_duration,
        rt_factor,
    )

    # Latency-driven fallback: if primary is very slow and Kokoro is available, try once.
    if (
        enable_latency_fallback
        and allow_fallback
        and used_engine != "kokoro"
        and rt_factor is not None
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
            kokoro_limit = text_length_limit("kokoro")
            if kokoro_limit and len(chunk.text) > kokoro_limit:
                logger.warning(
                    "Chunk %s skipping Kokoro latency fallback; text length %d exceeds max %d",
                    chunk.chunk_id,
                    len(chunk.text),
                    kokoro_limit,
                )
            else:
                (
                    fallback_audio,
                    fallback_engine,
                    kokoro_sr,
                    kokoro_dur,
                    kokoro_rt,
                ) = attempt_synthesis("kokoro", False, None)

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
                        kokoro_dur * kokoro_rt if kokoro_dur else 0.0,
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
                "Chunk %s Kokoro latency fallback failed: %s",
                chunk.chunk_id,
                fallback_exc,
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
    try:
        validate_audio_file(output_path)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Chunk %s output validation failed: %s", chunk.chunk_id, exc
        )
        return ChunkResult(
            chunk_id=chunk.chunk_id,
            success=False,
            output_path=output_path,
            engine_used=used_engine,
            rt_factor=rt_factor,
            audio_duration=audio_duration,
            text_len=text_len,
            est_dur=est_dur_sec,
            latency_fallback_used=latency_fallback_used,
            voice_used=voice_used,
            error="output_validation_failed",
            validation_tier=validation_tier,
            validation_reason="corrupt_output",
            validation_details={"error": str(exc)},
        )

    # Validation pipeline
    tier1_result = None
    tier2_result = None
    validation_success = True
    collected_validation_details: Dict[str, Any] = {}
    if validation_enabled and validation_config:
        if validation_config.enable_tier1:
            tier1_result = tier1_validate(
                chunk.text,
                str(output_path),
                validation_config,
                chars_per_minute=effective_cpm,
            )
            validation_tier = tier1_result.tier
            validation_reason = tier1_result.reason
            validation_details = tier1_result.details
            collected_validation_details["tier1"] = tier1_result.details
            validation_success = tier1_result.is_valid
            logger.info(
                "Chunk %s Tier1 validation %s (%s)",
                chunk.chunk_id,
                "PASS" if tier1_result.is_valid else "FAIL",
                tier1_result.reason,
            )

            if (
                not tier1_result.is_valid
                and allow_fallback
                and kokoro_available
                and used_engine != "kokoro"
            ):
                logger.warning(
                    "Chunk %s Tier1 failed (%s); retrying synthesis on Kokoro for validation recovery.",
                    chunk.chunk_id,
                    tier1_result.reason,
                )
                try:
                    kokoro_limit = text_length_limit("kokoro")
                    if kokoro_limit and len(chunk.text) > kokoro_limit:
                        logger.error(
                            "Chunk %s cannot retry on Kokoro because text length %d exceeds max %d",
                            chunk.chunk_id,
                            len(chunk.text),
                            kokoro_limit,
                        )
                    else:
                        (
                            audio,
                            used_engine,
                            sample_rate,
                            audio_duration,
                            rt_factor,
                        ) = attempt_synthesis("kokoro", False, None)
                        sf.write(output_path, audio, sample_rate)
                        tier1_result = tier1_validate(
                            chunk.text,
                            str(output_path),
                            validation_config,
                            chars_per_minute=effective_cpm,
                        )
                        validation_tier = tier1_result.tier
                        validation_reason = tier1_result.reason
                        validation_details = tier1_result.details
                        collected_validation_details["tier1"] = (
                            tier1_result.details
                        )
                        validation_success = tier1_result.is_valid
                        logger.info(
                            "Chunk %s Tier1 validation after Kokoro retry %s (%s)",
                            chunk.chunk_id,
                            "PASS" if tier1_result.is_valid else "FAIL",
                            tier1_result.reason,
                        )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error(
                        "Chunk %s validation retry failed: %s",
                        chunk.chunk_id,
                        exc,
                    )
                    validation_success = False
                    validation_reason = (
                        validation_reason or "validation_retry_failed"
                    )

        if validation_config.enable_tier2 and (
            tier1_result is None or tier1_result.is_valid
        ):
            if total_chunks is not None and chunk_index is not None:
                run_tier2 = should_run_tier2_validation(
                    chunk_index, total_chunks, validation_config
                )
            else:
                run_tier2 = True
            if run_tier2:
                tier2_result = tier2_validate(
                    chunk.text, str(output_path), validation_config
                )
                validation_tier = tier2_result.tier
                validation_reason = tier2_result.reason
                validation_details = tier2_result.details
                collected_validation_details["tier2"] = tier2_result.details
                validation_success = (
                    validation_success and tier2_result.is_valid
                )
                logger.info(
                    "Chunk %s Tier2 validation %s (%s)",
                    chunk.chunk_id,
                    "PASS" if tier2_result.is_valid else "FAIL",
                    tier2_result.reason,
                )

        # Tier 3: ASR Validation (opt-in)
        if (
            validation_config.enable_asr_validation
            if hasattr(validation_config, "enable_asr_validation")
            else False
        ) and ASRValidator is not None:
            logger.info("Chunk %s running ASR validation (Tier 3)", chunk.chunk_id)
            try:
                asr_validator = ASRValidator(model_size="base")
                asr_result = asr_validator.validate_audio(
                    output_path, chunk.text, chunk.chunk_id
                )

                collected_validation_details["asr"] = asr_result

                if not asr_result["valid"]:
                    validation_tier = 3
                    validation_reason = f"asr_{asr_result['recommendation']}"
                    validation_success = False

                    logger.warning(
                        "Chunk %s ASR validation FAILED: WER=%.1f%%, recommendation=%s",
                        chunk.chunk_id,
                        asr_result["wer"] * 100,
                        asr_result["recommendation"]
                    )

                    # Strategy 1: Try Llama rewrite first (if recommendation is "rewrite")
                    if (
                        asr_result["recommendation"] == "rewrite"
                        and LlamaRewriter is not None
                        and (
                            validation_config.enable_llama_asr_rewrite
                            if hasattr(validation_config, "enable_llama_asr_rewrite")
                            else False
                        )
                    ):
                        logger.info(
                            "Chunk %s attempting Llama rewrite based on ASR feedback",
                            chunk.chunk_id
                        )
                        try:
                            llama_rewriter = LlamaRewriter()
                            rewrite_result = llama_rewriter.rewrite_from_asr_feedback(
                                original_text=chunk.text,
                                asr_transcription=asr_result["transcription"],
                                asr_issues=asr_result["issues"],
                                wer=asr_result["wer"],
                                max_chars=max_len or len(chunk.text)
                            )

                            if rewrite_result["confidence"] > 0.7:
                                # High confidence rewrite, try synthesizing again
                                logger.info(
                                    "Chunk %s Llama rewrite (confidence=%.2f, strategy=%s): %s",
                                    chunk.chunk_id,
                                    rewrite_result["confidence"],
                                    rewrite_result["strategy"],
                                    rewrite_result["notes"]
                                )

                                # Retry synthesis with rewritten text
                                try:
                                    (
                                        rewrite_audio,
                                        rewrite_engine,
                                        rewrite_sr,
                                        rewrite_dur,
                                        rewrite_rt,
                                    ) = attempt_synthesis(
                                        effective_engine,
                                        False,
                                        None,
                                        text_override=rewrite_result["rewritten"]
                                    )

                                    # Validate the rewritten version with ASR
                                    temp_rewrite_path = output_dir / f"{chunk.chunk_id}_llama_retry.wav"
                                    sf.write(temp_rewrite_path, rewrite_audio, rewrite_sr)

                                    retry_asr_result = asr_validator.validate_audio(
                                        temp_rewrite_path,
                                        rewrite_result["rewritten"],
                                        chunk.chunk_id
                                    )

                                    if retry_asr_result["valid"] or retry_asr_result["wer"] < asr_result["wer"]:
                                        # Llama rewrite worked!
                                        audio = rewrite_audio
                                        sample_rate = rewrite_sr
                                        used_engine = rewrite_engine
                                        rt_factor = rewrite_rt
                                        audio_duration = rewrite_dur
                                        sf.write(output_path, audio, sample_rate)
                                        validation_success = True
                                        collected_validation_details["asr"] = retry_asr_result
                                        collected_validation_details["llama_rewrite"] = rewrite_result
                                        logger.info(
                                            "Chunk %s Llama+ASR SUCCESS: WER improved from %.1f%% to %.1f%%",
                                            chunk.chunk_id,
                                            asr_result["wer"] * 100,
                                            retry_asr_result["wer"] * 100
                                        )
                                    else:
                                        logger.warning(
                                            "Chunk %s Llama rewrite did not improve WER (%.1f%% → %.1f%%), trying engine switch",
                                            chunk.chunk_id,
                                            asr_result["wer"] * 100,
                                            retry_asr_result["wer"] * 100
                                        )

                                    temp_rewrite_path.unlink(missing_ok=True)

                                except Exception as llama_retry_exc:  # pylint: disable=broad-except
                                    logger.warning(
                                        "Chunk %s Llama rewrite retry synthesis failed: %s",
                                        chunk.chunk_id,
                                        llama_retry_exc
                                    )

                        except Exception as llama_exc:  # pylint: disable=broad-except
                            logger.warning(
                                "Chunk %s Llama rewrite failed: %s",
                                chunk.chunk_id,
                                llama_exc
                            )

                    # Strategy 2: Engine switch (if Llama didn't fix it, or recommendation is "switch_engine")
                    if (
                        not validation_success  # Llama didn't fix it
                        and allow_fallback
                        and kokoro_available
                        and used_engine != "kokoro"
                    ):
                        logger.warning(
                            "Chunk %s ASR recommends engine switch; retrying with Kokoro",
                            chunk.chunk_id
                        )
                        try:
                            (
                                fallback_audio,
                                fallback_engine,
                                fallback_sr,
                                fallback_dur,
                                fallback_rt,
                            ) = attempt_synthesis("kokoro", False, None)

                            # Re-validate with ASR
                            temp_path = output_dir / f"{chunk.chunk_id}_asr_retry.wav"
                            sf.write(temp_path, fallback_audio, fallback_sr)

                            retry_asr_result = asr_validator.validate_audio(
                                temp_path, chunk.text, chunk.chunk_id
                            )

                            if retry_asr_result["valid"] or retry_asr_result["wer"] < asr_result["wer"]:
                                # Kokoro version is better
                                audio = fallback_audio
                                sample_rate = fallback_sr
                                used_engine = fallback_engine
                                rt_factor = fallback_rt
                                audio_duration = fallback_dur
                                sf.write(output_path, audio, sample_rate)
                                validation_success = True
                                collected_validation_details["asr"] = retry_asr_result
                                logger.info(
                                    "Chunk %s ASR retry with Kokoro SUCCESS: WER improved from %.1f%% to %.1f%%",
                                    chunk.chunk_id,
                                    asr_result["wer"] * 100,
                                    retry_asr_result["wer"] * 100
                                )
                            temp_path.unlink(missing_ok=True)

                        except Exception as asr_retry_exc:  # pylint: disable=broad-except
                            logger.warning(
                                "Chunk %s ASR-driven Kokoro retry failed: %s",
                                chunk.chunk_id,
                                asr_retry_exc
                            )
                else:
                    logger.info(
                        "Chunk %s ASR validation PASSED: WER=%.1f%%",
                        chunk.chunk_id,
                        asr_result["wer"] * 100
                    )

            except Exception as asr_exc:  # pylint: disable=broad-except
                logger.warning(
                    "Chunk %s ASR validation error (continuing): %s",
                    chunk.chunk_id,
                    asr_exc
                )
                collected_validation_details["asr"] = {
                    "error": str(asr_exc),
                    "valid": True  # Fail open
                }

    if collected_validation_details and (
        validation_details is None
        or validation_details != collected_validation_details
    ):
        validation_details = collected_validation_details

    logger.info(
        "Chunk %s synthesized via '%s' → %s",
        chunk.chunk_id,
        used_engine,
        output_path,
    )
    return ChunkResult(
        chunk_id=chunk.chunk_id,
        success=validation_success,
        output_path=output_path,
        engine_used=used_engine,
        rt_factor=rt_factor,
        audio_duration=audio_duration,
        text_len=text_len,
        est_dur=est_dur_sec,
        latency_fallback_used=latency_fallback_used,
        voice_used=voice_used,
        validation_tier=validation_tier,
        validation_reason=validation_reason,
        validation_details=validation_details,
        error=None if validation_success else validation_reason,
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
    summary_path: Optional[Path] = None,
) -> None:
    """Write phase4 status back to pipeline.json following the documented schema."""
    state = PipelineState(pipeline_path, validate_on_read=False)
    total = len(results)
    completed = sum(1 for r in results if r.success)
    failed = total - completed
    engines_used = sorted({r.engine_used for r in results if r.engine_used})
    voices_used = sorted({r.voice_used for r in results if r.voice_used})
    rt_factors = [
        r.rt_factor
        for r in results
        if r.success and r.rt_factor is not None and np.isfinite(r.rt_factor)
    ]
    avg_rt_factor = float(np.mean(rt_factors)) if rt_factors else None
    latency_fallback_count = sum(1 for r in results if r.latency_fallback_used)
    fallback_rate = (
        float(latency_fallback_count) / max(1, completed)
        if completed
        else None
    )
    validated_chunks = sum(1 for r in results if r.validation_tier is not None)
    validation_failures = sum(
        1 for r in results if not r.success and r.validation_reason
    )
    tier1_failures = sum(
        1 for r in results if r.validation_tier == 1 and not r.success
    )
    tier2_failures = sum(
        1 for r in results if r.validation_tier == 2 and not r.success
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
        advisory = (
            (advisory + extra)
            if advisory
            else ("High latency fallback usage (>20%). " "Consider Kokoro.")
        )

    chunk_rows: List[Dict[str, Any]] = []
    for result in results:
        # Preserve the most specific error we can find; only fall back to
        # "unknown error" when nothing is available.
        error_message = None
        if not result.success:
            error_message = (
                result.error
                or (
                    result.validation_reason
                    if isinstance(result.validation_reason, str)
                    else None
                )
                or (
                    result.validation_details.get("error")
                    if isinstance(result.validation_details, dict)
                    else None
                )
            )
            # Some callers may stick an error string in rt_factor; capture it
            # when present to avoid losing detail in summaries.
            if not error_message and isinstance(result.rt_factor, str):
                error_message = result.rt_factor
        chunk_rows.append(
            {
                "chunk_id": result.chunk_id,
                "text_len": result.text_len,
                "est_dur": result.est_dur,
                "engine": result.engine_used,
                "rt_factor": result.rt_factor,
                "audio_path": (
                    serialize_path_for_pipeline(result.output_path)
                    if result.output_path
                    else None
                ),
                "status": "success" if result.success else "failed",
                "errors": (
                    [] if result.success else [error_message or "unknown error"]
                ),
                "latency_fallback_used": result.latency_fallback_used,
                "validation_tier": result.validation_tier,
                "validation_reason": result.validation_reason,
                "validation_details": result.validation_details,
            }
        )

    file_errors = [
        {
            "chunk_id": r.chunk_id,
            "message": (
                r.error
                or (
                    r.validation_reason if isinstance(r.validation_reason, str) else None
                )
                or (
                    r.validation_details.get("error")
                    if isinstance(r.validation_details, dict)
                    else None
                )
                or (r.rt_factor if isinstance(r.rt_factor, str) else None)
                or "unknown error"
            ),
        }
        for r in results
        if not r.success
    ]
    end_ts = time.time()
    start_ts = end_ts - duration_sec if duration_sec else None
    with state.transaction(operation="phase4_summary") as txn:
        # If there were chunks to synthesize but none succeeded, mark the file as
        # failed so downstream phases don't treat it as a successful run with
        # zero artifacts. Otherwise use success/partial semantics.
        if total > 0 and completed == 0:
            status = "failed"
        elif failed == 0:
            status = "success"
        else:
            status = "partial"
        timestamps = {
            "start": start_ts,
            "end": end_ts,
            "duration": duration_sec,
        }
        # Always include `chunk_audio_paths` (possibly empty) so downstream
        # phases can rely on the key existing in the pipeline envelope.
        artifacts = {
            "audio_dir": serialize_path_for_pipeline(output_dir),
            "chunk_audio_paths": [
                serialize_path_for_pipeline(r.output_path)
                for r in results
                if r.success and r.output_path
            ],
        }
        if summary_path:
            artifacts["run_summary"] = serialize_path_for_pipeline(
                summary_path
            )
        metrics = {
            "total_chunks": total,
            "chunks_completed": completed,
            "chunks_failed": failed,
            "duration_seconds": duration_sec,
            "avg_rt_factor": avg_rt_factor,
            "latency_fallback_chunks": latency_fallback_count,
            "fallback_rate": fallback_rate,
            "rt_p50": rt_p50,
            "rt_p90": rt_p90,
            "rt_p99": rt_p99,
            "validated_chunks": validated_chunks,
            "validation_failures": validation_failures,
            "tier1_failures": tier1_failures,
            "tier2_failures": tier2_failures,
        }
        extra_fields = {
            "voice_id": voice_id,
            "requested_engine": requested_engine,
            "selected_engine": selected_engine,
            "engines_used": engines_used,
            "voices_used": voices_used,
            "advisory": advisory,
        }
        file_entry = txn.update_phase(
            file_id,
            "phase4",
            status,
            timestamps,
            artifacts,
            metrics,
            file_errors,
            chunks=chunk_rows,
            extra_fields=extra_fields,
        )

        file_entry.setdefault(
            "chunk_audio_paths",
            file_entry.get("artifacts", {}).get("chunk_audio_paths", []),
        )

        # Ensure the phase block records this file entry (robust against
        # partial serializations or other anomalies).
        phase_block = ensure_phase_block(txn.data, "phase4")
        files_section = phase_block.setdefault("files", {})
        try:
            files_section[file_id] = file_entry
        except Exception:
            files_section[file_id] = dict(file_entry or {})
        phase_block.setdefault("chunks", [])
        all_files = files_section.values()
        block_success = all(
            entry.get("status") == "success" for entry in all_files
        )
        phase_block["status"] = "success" if block_success else "partial"
        phase_block.setdefault("errors", [])
        phase_metrics = phase_block.setdefault("metrics", {})
        phase_metrics.update(
            {
                "files_processed": len(files_section),
                "chunks_completed": sum(
                    entry.get("metrics", {}).get("chunks_completed", 0)
                    for entry in all_files
                ),
                "chunks_failed": sum(
                    entry.get("metrics", {}).get("chunks_failed", 0)
                    for entry in all_files
                ),
            }
        )
    logger.info("Updated phase4 summary for %s", file_id)


def write_run_summary(
    output_dir: Path,
    results: List[ChunkResult],
    duration_sec: float,
    requested_engine: str,
    selected_engine: str,
    voice_id: str,
) -> Path:
    """Persist a lightweight summary.json for quick inspection and return its path."""
    rt_values = [
        r.rt_factor
        for r in results
        if r.success and r.rt_factor is not None and np.isfinite(r.rt_factor)
    ]
    rt_p50 = float(np.percentile(rt_values, 50)) if rt_values else None
    rt_p90 = float(np.percentile(rt_values, 90)) if rt_values else None
    rt_p99 = float(np.percentile(rt_values, 99)) if rt_values else None
    fallback_rate = sum(
        1 for r in results if r.latency_fallback_used and r.success
    ) / max(1, sum(1 for r in results if r.success))
    validation_failures = sum(
        1 for r in results if not r.success and r.validation_reason
    )

    payload = {
        "requested_engine": requested_engine,
        "selected_engine": selected_engine,
        "voice_id": voice_id,
        "duration_seconds": duration_sec,
        "chunks_total": len(results),
        "chunks_success": sum(1 for r in results if r.success),
        "chunks_failed": sum(1 for r in results if not r.success),
        "rt_p50": rt_p50,
        "rt_p90": rt_p90,
        "rt_p99": rt_p99,
        "latency_fallback_rate": fallback_rate,
        "validation_failures": validation_failures,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return summary_path


ENGINE_IMPORT_MAP: Dict[str, Tuple[str, str]] = {
    "xtts": ("engines.xtts_engine", "XTTSEngine"),
    "kokoro": ("engines.kokoro_engine", "KokoroEngine"),
}


def build_engine_manager(
    device: str, engines: Optional[List[str]] = None
) -> EngineManager:
    """Build engine manager while skipping engines whose deps are unavailable."""
    manager = EngineManager(device=device)

    # Lazy import only requested engines to avoid dep conflicts
    if engines is None:
        engines = list(ENGINE_IMPORT_MAP.keys())

    for engine_name in engines:
        module_info = ENGINE_IMPORT_MAP.get(engine_name)
        if not module_info:
            logger.warning(
                "Unknown engine '%s' requested; skipping registration.",
                engine_name,
            )
            continue

        module_path, class_name = module_info
        try:
            module = importlib.import_module(module_path)
            engine_class = getattr(module, class_name)
        except ModuleNotFoundError as exc:
            logger.warning(
                "Skipping engine '%s' because dependencies are missing (%s).",
                engine_name,
                exc,
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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 4: Multi-Engine TTS Synthesis"
    )
    parser.add_argument(
        "--file_id",
        required=True,
        help="File identifier (matches phase3 entry)",
    )
    parser.add_argument(
        "--engine",
        default=None,
        choices=["auto", "xtts", "kokoro"],
        help="Preferred engine (auto defers to heuristic). Fallback order is managed automatically for XTTS/Kokoro.",
    )
    parser.add_argument(
        "--prefer_kokoro",
        action="store_true",
        help="Shortcut to default to Kokoro for throughput (overrides --engine if it is xtts).",
    )
    parser.add_argument(
        "--profile",
        choices=["safe", "balanced", "max_quality"],
        help="Preset: safe (workers=3, prefer Kokoro, guard on), balanced (workers=3, auto-engine), max_quality (workers=2, xtts focus).",
    )
    parser.add_argument(
        "--json_path", required=True, help="Path to pipeline.json"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Phase4 config file"
    )
    parser.add_argument(
        "--voice",
        help="Voice ID override (keys from configs/voice_references.json)",
    )
    parser.add_argument("--device", default="cpu", help="Device (cpu/cuda)")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Parallel workers for chunk synthesis",
    )
    parser.add_argument(
        "--max-workers",
        dest="workers",
        type=int,
        help="Alias for --workers (max parallel synth jobs).",
    )
    parser.add_argument(
        "--language", help="Override language (defaults to config value)"
    )
    parser.add_argument(
        "--chunk_id",
        type=int,
        help="Optional chunk index to synthesize (legacy compatibility)",
    )
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
        "--skip-existing",
        dest="resume",
        action="store_true",
        help="Alias for --resume; skip already-rendered chunks.",
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
    parser.add_argument(
        "--no-validation",
        action="store_true",
        help="Disable all validation tiers (Tier 1 and Tier 2).",
    )
    parser.add_argument(
        "--tier2-sample",
        type=float,
        help="Override Tier 2 random sample rate (0.0-1.0).",
    )
    parser.add_argument(
        "--tier2-first-n",
        type=int,
        help="Override Tier 2 always-validate first N chunks.",
    )
    parser.add_argument(
        "--tier2-last-n",
        type=int,
        help="Override Tier 2 always-validate last N chunks.",
    )

    args = parser.parse_args(argv)

    json_path = Path(args.json_path).resolve()
    config_path = MODULE_ROOT.parent / args.config
    voices_config_path = (
        MODULE_ROOT.parent / "configs" / "voice_references.json"
    )

    config = load_config(config_path)
    pipeline_data = load_pipeline_json(json_path)
    enable_g2p = bool(config.get("enable_g2p", False))
    normalize_numbers = bool(config.get("normalize_numbers", True))
    custom_overrides = config.get("custom_pronunciations", {}) or None
    chars_per_minute = int(
        config.get(
            "tts_chars_per_minute",
            config.get("chars_per_minute", DEFAULT_CHARS_PER_MINUTE),
        )
    )
    if chars_per_minute <= 0:
        chars_per_minute = DEFAULT_CHARS_PER_MINUTE
    workers = (
        args.workers if args.workers is not None else config.get("workers", 2)
    )
    workers = max(1, int(workers))
    cpu_safe = bool(args.cpu_safe)
    cpu_guard = bool(args.cpu_guard or cpu_safe)
    cpu_guard_high = float(
        args.cpu_guard_high if args.cpu_guard_high is not None else 85.0
    )
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
        slow_rt_threshold = min(
            slow_rt_threshold, 3.5
        )  # Prefer earlier fallback when protecting CPU thermals.
    validation_settings = config.get("validation", {}) or {}
    tier1_settings = validation_settings.get("tier1", validation_settings)
    tier2_settings = validation_settings.get("tier2", validation_settings)
    tier2_enabled_default = bool(
        tier2_settings.get(
            "enabled", tier2_settings.get("enable_tier2", False)
        )
    )
    tier2_enabled_override = any(
        val is not None
        for val in (args.tier2_sample, args.tier2_first_n, args.tier2_last_n)
    )
    validation_config = ValidationConfig(
        enable_tier1=bool(
            tier1_settings.get(
                "enabled", tier1_settings.get("enable_tier1", True)
            )
        ),
        duration_tolerance_sec=float(
            tier1_settings.get("duration_tolerance_sec", 120.0)
        ),
        silence_threshold_sec=float(
            tier1_settings.get("silence_threshold_sec", 2.0)
        ),
        min_amplitude_db=float(tier1_settings.get("min_amplitude_db", -40.0)),
        enable_tier2=tier2_enabled_default or tier2_enabled_override,
        whisper_model=tier2_settings.get("whisper_model", "tiny"),
        whisper_sample_rate=float(
            args.tier2_sample
            if args.tier2_sample is not None
            else tier2_settings.get("whisper_sample_rate", 0.02)
        ),
        whisper_first_n=int(
            args.tier2_first_n
            if args.tier2_first_n is not None
            else tier2_settings.get("whisper_first_n", 10)
        ),
        whisper_last_n=int(
            args.tier2_last_n
            if args.tier2_last_n is not None
            else tier2_settings.get("whisper_last_n", 10)
        ),
        max_wer=float(tier2_settings.get("max_wer", 0.10)),
        chars_per_minute=chars_per_minute,
        error_phrases=validation_settings.get("error_phrases"),
    )
    if args.no_validation:
        validation_config.enable_tier1 = False
        validation_config.enable_tier2 = False
    validation_enabled = (
        validation_config.enable_tier1 or validation_config.enable_tier2
    )

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
        if (
            args.play_notification is not False
            and not args.silence_notifications
        ):
            play_alert_beep(silence_mode=False)
        return 1

    engine_requested = args.engine or config.get("engine", "xtts")
    auto_engine_enabled = bool(args.auto_engine or cpu_safe)
    if engine_requested == "auto":
        auto_engine_enabled = True
        engine_requested = config.get("engine", "xtts")
    if args.profile:
        if args.profile == "safe":
            cpu_safe = True
            args.prefer_kokoro = True
            workers = min(workers, 3)
        elif args.profile == "balanced":
            cpu_safe = False
            workers = min(workers, 3)
        elif args.profile == "max_quality":
            engine_requested = "xtts"
            cpu_safe = False
            workers = min(workers, 2)
            enable_latency_fallback = False
            args.prefer_kokoro = False
    auto_engine_enabled = auto_engine_enabled or cpu_safe
    if args.prefer_kokoro and engine_requested == "xtts":
        engine_requested = "kokoro"
        logger.info(
            "Prefer Kokoro flag set: overriding requested engine to kokoro for throughput."
        )
    engine_selected = engine_requested
    est_audio_seconds = estimate_audio_seconds(
        chunks, chars_per_min=chars_per_minute
    )
    if auto_engine_enabled:
        engine_selected, reason = choose_engine_auto(
            chunks,
            preferred=engine_requested,
            rt_xtts=float(config.get("rt_xtts_factor", 3.2)),
            rt_kokoro=float(config.get("rt_kokoro_factor", 1.3)),
            chars_per_min=chars_per_minute,
        )
        logger.info(
            "Auto-engine decision: %s (requested=%s, selected=%s)",
            reason,
            engine_requested,
            engine_selected,
        )
    else:
        logger.info(
            "Auto-engine disabled. Using requested engine: %s",
            engine_requested,
        )
    if cpu_safe:
        logger.info(
            "CPU-safe mode: enforcing conservative throughput (workers capped, latency fallback always on)."
        )
    if rt_budget_hours:
        rt_factor_hint = float(
            config.get("rt_xtts_factor", 3.2)
            if engine_selected == "xtts"
            else config.get("rt_kokoro_factor", 1.3)
        )
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
                logger.info(
                    "CPU-safe + budget: biasing to Kokoro for throughput."
                )
                engine_selected = "kokoro"
            best_case_rt = float(
                min(
                    config.get("rt_xtts_factor", 3.2),
                    config.get("rt_kokoro_factor", 1.3),
                )
            )
            best_case_wall = est_audio_seconds * best_case_rt
            if best_case_wall > budget_seconds:
                logger.warning(
                    "Even best-case (fastest RT factor %.2f) estimated wall %.1fh exceeds budget %.1fh. Expect overrun.",
                    best_case_rt,
                    best_case_wall / 3600.0,
                    rt_budget_hours,
                )

    if args.play_notification is None:
        args.play_notification = (
            True  # Default ON unless explicitly disabled elsewhere
        )
    if args.play_notification and not args.silence_notifications:
        logger.info(
            "Astromech notifications: ON (use --silence_notifications to mute)."
        )
    if cpu_guard:
        logger.info(
            "CPU guard: enabled (CPU threshold %.1f%%; RAM guard 85%%; requires psutil).",
            cpu_guard_high,
        )

    voices_config = load_voices_config(voices_config_path)
    voice_references = prepare_voice_references(
        voice_config_path=str(voices_config_path),
        cache_dir=str(MODULE_ROOT.parent / "voice_references"),
    )
    voice_id, reference_audio, engine_params = select_voice(
        json_path,
        resolved_file_id,
        args.voice,
        voice_references,
        voices_config_path,
        voices_config=voices_config,
    )
    voice_assets = build_voice_assets(voices_config, voice_references)

    base_output = Path(
        config.get("audio_chunks_dir", "audio_chunks")
    ).resolve()
    output_dir = base_output / resolved_file_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Lazy-load only needed engines for isolation
    engines_to_load = [engine_selected] if args.disable_fallback else None
    manager = build_engine_manager(args.device, engines=engines_to_load)
    manager.set_default_engine(engine_selected)

    language = args.language or config.get("language", "en")
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
    total_chunks = len(chunks)
    pending = list(chunks)
    active_futures: Dict[Any, str] = {}
    progress = (
        tqdm(total=total_chunks, desc="Synth", unit="chunk") if tqdm else None
    )

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
                    voice_assets=voice_assets,
                    default_voice_id=voice_id,
                    validation_config=validation_config,
                    validation_enabled=validation_enabled,
                    chunk_index=chunk.index,
                    total_chunks=total_chunks,
                    chars_per_minute=chars_per_minute,
                )
                active_futures[future] = chunk.chunk_id

            if not active_futures:
                break

            done, _ = wait(active_futures, return_when=FIRST_COMPLETED)
            for future in done:
                active_futures.pop(future, None)
                result = future.result()
                results.append(result)
                if progress:
                    progress.update(1)
                if total_chunks:
                    completed_so_far = len(results)
                    if (
                        completed_so_far == total_chunks
                        or completed_so_far % max(1, total_chunks // 10) == 0
                    ):
                        logger.info(
                            "Progress: %d/%d (%.1f%%)",
                            completed_so_far,
                            total_chunks,
                            (completed_so_far / total_chunks) * 100.0,
                        )

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
                    ram_usage = psutil.virtual_memory().percent
                    hot = cpu_usage >= cpu_guard_high or ram_usage >= 85.0
                    if hot:
                        cpu_high_streak += 1
                    else:
                        cpu_high_streak = 0

                    if cpu_high_streak >= 2:
                        allowed_workers -= 1
                        cpu_high_streak = 0
                        logger.warning(
                            "CPU/RAM guard: reducing workers to %d (CPU %.1f%%, RAM %.1f%%; threshold CPU %.1f%%, RAM 85%%).",
                            allowed_workers,
                            cpu_usage,
                            ram_usage,
                            cpu_guard_high,
                        )
    if progress:
        progress.close()

    duration = time.time() - start_time
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    logger.info("-" * 80)
    logger.info(
        "Completed in %.1fs (%0.1fs/chunk)",
        duration,
        duration / max(1, len(results)),
    )
    logger.info("Success: %d | Failed: %d", success_count, failed_count)
    rt_values = [
        r.rt_factor
        for r in results
        if r.success and r.rt_factor is not None and np.isfinite(r.rt_factor)
    ]
    if rt_values:
        rt_p50 = float(np.percentile(rt_values, 50))
        rt_p90 = float(np.percentile(rt_values, 90))
        rt_p99 = float(np.percentile(rt_values, 99))
        fallback_rate = sum(
            1 for r in results if r.latency_fallback_used and r.success
        ) / max(1, success_count)
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

    summary_path = write_run_summary(
        output_dir=output_dir,
        results=results,
        duration_sec=duration,
        requested_engine=engine_requested,
        selected_engine=engine_selected,
        voice_id=voice_id,
    )
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
        summary_path=summary_path,
    )

    exit_code = 0 if failed_count == 0 else 1
    if args.play_notification is not False and not args.silence_notifications:
        if exit_code == 0:
            play_success_beep(silence_mode=False)
        else:
            play_alert_beep(silence_mode=False)
    return exit_code


def execute_phase4(
    file_id: str,
    json_path: str,
    engine: str = "auto",
    voice: Optional[str] = None,
    language: Optional[str] = None,
    workers: Optional[int] = None,
    resume: bool = False,
) -> int:
    """
    Standardized callable entry point so orchestrators can invoke Phase 4.
    """
    argv = [
        f"--file_id={file_id}",
        f"--json_path={json_path}",
        f"--engine={engine or 'auto'}",
    ]
    if voice:
        argv.append(f"--voice={voice}")
    if language:
        argv.append(f"--language={language}")
    if workers:
        argv.append(f"--workers={workers}")
    if resume:
        argv.append("--resume")
    return main(argv)


if __name__ == "__main__":
    sys.exit(main())
