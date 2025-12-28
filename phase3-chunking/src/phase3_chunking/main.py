import argparse
import logging
from time import perf_counter
from pathlib import Path
import re
import yaml
import os
import sys
import warnings
import hashlib
from typing import List, Optional, Dict, Any, Tuple


def _load_pipeline_common():
    """Import pipeline_common after ensuring the repo root is on sys.path."""
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from pipeline_common import (
        PipelineState,
        StateError,
        ensure_phase_block,
        ensure_phase_and_file,
    )
    from pipeline_common.state_manager import StateTransaction
    from pipeline_common.astromech_notify import (
        play_success_beep,
        play_alert_beep,
    )

    return (
        PipelineState,
        StateError,
        ensure_phase_block,
        ensure_phase_and_file,
        StateTransaction,
        play_success_beep,
        play_alert_beep,
    )


(
    PipelineState,
    StateError,
    ensure_phase_block,
    ensure_phase_and_file,
    StateTransaction,
    play_success_beep,
    play_alert_beep,
) = _load_pipeline_common()

# Smart import: works both as script and as module
try:
    from .models import ChunkRecord, ValidationConfig, Phase3Config
    from .voice_selection import select_voice, validate_voice_id
    from .detect import detect_genre, get_genre_from_metadata, validate_genre
    from .profiles import get_profile
    from .utils import (
        clean_text,
        detect_sentences,
        form_semantic_chunks,
        assess_readability,
        save_chunks,
        calculate_chunk_metrics,
    )
    from .structure_chunking import (
        chunk_by_structure,
        should_use_structure_chunking,
    )
    from .io_utils import ensure_absolute_path
except ImportError:
    from models import ChunkRecord, ValidationConfig, Phase3Config
    from voice_selection import select_voice, validate_voice_id
    from detect import detect_genre, get_genre_from_metadata, validate_genre
    from profiles import get_profile
    from utils import (
        clean_text,
        detect_sentences,
        form_semantic_chunks,
        assess_readability,
        save_chunks,
        calculate_chunk_metrics,
    )
    from structure_chunking import (
        chunk_by_structure,
        should_use_structure_chunking,
    )
    from io_utils import ensure_absolute_path
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

warnings.filterwarnings(
    "ignore", category=UserWarning, module="textstat.textstat"
)

# Shared cadence assumption so downstream durations line up
DEFAULT_CHARS_PER_MINUTE = 1050


def _install_update_phase_api() -> None:
    """Ensure StateTransaction exposes update_phase for schema-aligned writes."""

    if hasattr(StateTransaction, "update_phase"):
        return

    def update_phase(  # type: ignore[override]
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

    setattr(StateTransaction, "update_phase", update_phase)


_install_update_phase_api()


# -------------------------------------------------------------------
# LlamaChunker lazy loader (optional, requires Ollama + agents module)
# -------------------------------------------------------------------
_LLAMA_CHUNKER = None
_LLAMA_CHUNKER_CHECKED = False


def _get_llama_chunker(model: str = "llama3.1:8b-instruct-q4_K_M"):
    """
    Lazy-load LlamaChunker to avoid import errors when Ollama not available.

    Returns:
        LlamaChunker instance or None if unavailable
    """
    global _LLAMA_CHUNKER, _LLAMA_CHUNKER_CHECKED

    if _LLAMA_CHUNKER_CHECKED:
        return _LLAMA_CHUNKER

    _LLAMA_CHUNKER_CHECKED = True

    try:
        # Add monorepo root to path for agents import
        monorepo_root = Path(__file__).resolve().parents[3]
        if str(monorepo_root) not in sys.path:
            sys.path.insert(0, str(monorepo_root))

        from agents import LlamaChunker
        _LLAMA_CHUNKER = LlamaChunker(model=model)
        logger.info(f"✅ LlamaChunker initialized with model: {model}")
    except ImportError as e:
        # Likely missing 'ollama' package or agents module
        logger.warning(
            f"⚠️  LlamaChunker unavailable: {e}. "
            "To enable LLM-powered chunking: pip install ollama && ollama pull llama3.1:8b-instruct-q4_K_M"
        )
        _LLAMA_CHUNKER = None
    except Exception as e:
        # Could be Ollama server not running, model not pulled, etc.
        logger.warning(
            f"⚠️  LlamaChunker initialization failed: {e}. "
            "Ensure Ollama is running (ollama serve) and model is pulled."
        )
        _LLAMA_CHUNKER = None

    return _LLAMA_CHUNKER


def _llama_chunk_text(
    text: str,
    max_chars: int,
    min_chars: int,
    model: str = "llama3.1:8b-instruct-q4_K_M",
) -> tuple[list[str], list[float]]:
    """
    Use LlamaChunker to split text into semantic chunks.

    Returns:
        (chunks, coherence_scores) - coherence is 0.9 for LLM-based splits
    """
    chunker = _get_llama_chunker(model)
    if chunker is None:
        raise RuntimeError("LlamaChunker not available")

    # Use split_text which returns (chunk_text, boundary_info) tuples
    results = chunker.split_text(text, max_chars=max_chars, min_chars=min_chars)

    chunks = [chunk_text for chunk_text, _ in results]
    # LLM-based chunking has high semantic coherence by design
    coherence = [0.9] * len(chunks)

    return chunks, coherence


def _read_chunk_text_length(path: Path) -> Optional[int]:
    """Best-effort text length reader that tolerates missing/corrupt files."""
    try:
        return len(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Chunk file missing when computing metadata: %s", path)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to read chunk %s for length calculation: %s", path, exc
        )
    return None


def build_chunk_metadata(
    chunks: List[str], chunk_paths: List[str]
) -> List[Dict[str, Any]]:
    """Standardize chunk metadata for downstream phases."""
    metadata: List[Dict[str, Any]] = []
    for idx, path_str in enumerate(chunk_paths):
        path_obj = ensure_absolute_path(path_str)
        chunk_id = derive_chunk_id_from_path(path_obj, idx)
        text_len: Optional[int] = None
        if chunks and idx < len(chunks):
            text_len = len(chunks[idx])
        if text_len is None:
            text_len = _read_chunk_text_length(path_obj)
        est_dur = (
            (text_len / DEFAULT_CHARS_PER_MINUTE) * 60.0 if text_len else None
        )
        metadata.append(
            {
                "chunk_id": chunk_id,
                "text_len": text_len,
                "est_dur": est_dur,
                "engine": None,
                "rt_factor": None,
                "path": str(path_obj),
            }
        )
    return metadata


def ensure_chunk_metadata(
    record: ChunkRecord,
    chunk_paths: List[str],
    chunks: Optional[List[str]] = None,
) -> None:
    """Populate chunk_metadata if missing to keep schema stable."""
    if getattr(record, "chunk_metadata", None):
        return
    record.chunk_metadata = build_chunk_metadata(chunks or [], chunk_paths)


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA256 for change detection and reuse checks."""
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            sha.update(block)
    return sha.hexdigest()


def find_monorepo_root(start_path: Path) -> Path:
    """Find the monorepo root by looking for phase directories or env variable."""
    root_env = os.environ.get("MONOREPO_ROOT")
    if root_env:
        root_path = Path(root_env)
        if root_path.exists():
            logger.info(f"Using MONOREPO_ROOT from env: {root_env}")
            return root_path
        else:
            logger.warning(
                f"MONOREPO_ROOT env var points to non-existent path: {root_env}"
            )

    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    max_levels = 10
    level = 0

    while current != current.parent and level < max_levels:
        try:
            if not current.exists() or not current.is_dir():
                current = current.parent
                level += 1
                continue

            subdirs = [
                d
                for d in current.iterdir()
                if d.is_dir() and d.name.startswith("phase")
            ]
            if len(subdirs) >= 2:
                logger.info(f"Monorepo root detected at: {current}")
                return current
        except (PermissionError, OSError) as e:
            logger.warning(f"Error accessing {current}: {e}")

        current = current.parent
        level += 1

    raise FileNotFoundError(
        "Monorepo root not found. Set MONOREPO_ROOT environment variable or ensure phase directories exist in parent path."
    )


def derive_file_id_from_path(text_path: Path) -> str:
    """Derive a stable file_id from a text file path when none is provided."""
    stem = text_path.stem.lower()
    sanitized = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    sanitized = re.sub(r"_+", "_", sanitized)
    if not sanitized:
        sanitized = re.sub(r"\s+", "_", stem) or "file"
    logger.info(
        f"Derived file_id '{sanitized}' from text path '{text_path.name}'"
    )
    return sanitized


def derive_chunk_id_from_path(path: Path, index: int) -> str:
    """Normalize chunk IDs (chunk_0001) for downstream phases."""
    stem = path.stem
    match = re.search(r"chunk[_-]?(\d+)", stem, flags=re.IGNORECASE)
    if match:
        return f"chunk_{int(match.group(1)):04d}"
    return f"chunk_{index:04d}"


def hash_text_content(text: str) -> str:
    """Hash cleaned text for reuse detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_pipeline_state(json_path: str) -> dict:
    """Load pipeline.json contents via PipelineState."""
    state = PipelineState(Path(json_path), validate_on_read=False)
    try:
        return state.read(validate=False)
    except FileNotFoundError:
        logger.info(
            "Pipeline JSON not found at %s, starting fresh.", state.path
        )
        return {}
    except StateError as exc:
        logger.error(
            "Failed to read pipeline state (%s); starting empty.", exc
        )
        return {}


def persist_phase3_result(
    json_path: str,
    pipeline_data: dict,
    file_id: str,
    record: ChunkRecord,
    chunk_ids: List[str],
    detected_genre: str,
    applied_profile: str,
    sentence_model: str,
    embeddings_enabled: bool,
    text_hash: str,
    structure_mode_used: bool,
    fallback_used: bool = False,
    fallback_message: str = "",
) -> dict:
    """Persist phase3 results using PipelineState transactions."""
    state = PipelineState(Path(json_path), validate_on_read=False)
    with state.transaction(
        operation="phase3_commit",
        seed_data=pipeline_data if pipeline_data else None,
    ) as txn:
        # Safe model serialization to handle Pydantic v1/v2 differences or unexpected errors.
        try:
            entry_payload = record.model_dump()
        except Exception:
            try:
                entry_payload = (
                    record.dict() if hasattr(record, "dict") else {}
                )
            except Exception:
                # Best-effort minimal payload so we still write a pipeline entry.
                entry_payload = {
                    "text_path": getattr(record, "text_path", None),
                    "chunk_paths": list(
                        getattr(record, "chunk_paths", []) or []
                    ),
                    "status": getattr(record, "status", "failed"),
                    "timestamps": getattr(record, "timestamps", {}),
                    "errors": list(getattr(record, "errors", []) or []),
                }
        chunk_metrics = dict(record.chunk_metrics or {})
        avg_coherence = (
            sum(record.coherence_scores) / len(record.coherence_scores)
            if record.coherence_scores
            else None
        )
        avg_readability = (
            sum(record.readability_scores) / len(record.readability_scores)
            if record.readability_scores
            else 0.0
        )

        artifacts = {
            "text_path": record.text_path,
            "chunk_paths": list(record.chunk_paths),
        }
        metrics = {
            **chunk_metrics,
            "chunk_count": len(record.chunk_paths),
            "avg_chunk_chars": int(
                chunk_metrics.get("avg_char_length", 0) or 0
            ),
            "avg_chunk_words": int(
                chunk_metrics.get("avg_word_count", 0) or 0
            ),
            "avg_chunk_duration_sec": float(
                chunk_metrics.get("avg_duration", 0.0) or 0.0
            ),
            "avg_coherence": (
                None if avg_coherence is None else float(avg_coherence)
            ),
            "avg_readability": float(avg_readability),
        }
        extra_fields = {
            key: value
            for key, value in entry_payload.items()
            if key
            not in {
                "status",
                "timestamps",
                "artifacts",
                "metrics",
                "errors",
                "chunks",
            }
        }
        extra_fields.update(
            {
                "chunk_ids": chunk_ids,
                "genre": detected_genre,
                "profile": applied_profile,
                "sentence_model": sentence_model,
                "embeddings_enabled": embeddings_enabled,
                "structure_mode_used": bool(structure_mode_used),
                "text_hash": text_hash,
                "source_hash": entry_payload.get("source_hash") or text_hash,
                "avg_coherence": metrics["avg_coherence"],
                "avg_readability": metrics["avg_readability"],
                "chunk_metadata": record.chunk_metadata or [],
            }
        )
        envelope = txn.update_phase(
            file_id,
            "phase3",
            record.status or "pending",
            record.timestamps or {},
            artifacts,
            metrics,
            record.errors or [],
            chunks=record.chunk_metadata or [],
            extra_fields=extra_fields,
        )

        # Ensure the phase3.files mapping contains an entry for this file_id even
        # if serialization partially failed earlier. This avoids missing pipeline
        # entries that cause downstream phases to abort.
        phase_block = ensure_phase_block(txn.data, "phase3")
        phase_block.setdefault("files", {})
        try:
            phase_block["files"][file_id] = envelope
        except Exception:
            # As a last resort, write the safe entry_payload we constructed above.
            phase_block["files"][file_id] = dict(entry_payload or {})

        phase_block = ensure_phase_block(txn.data, "phase3")
        if fallback_used:
            error_entry = {
                "file_id": file_id,
                "type": "Phase2Desync",
                "message": fallback_message
                or "Fallback used due to missing/invalid Phase 2 data",
                "timestamp": record.timestamps.get("start", 0),
            }
            phase_block.setdefault("errors", []).append(error_entry)

        files = phase_block.get("files", {})
        successful = sum(
            1 for f in files.values() if f.get("status") == "success"
        )
        failed = sum(1 for f in files.values() if f.get("status") == "failed")
        total = len(files)
        if failed:
            phase_block["status"] = "partial"
        elif successful == total and total > 0:
            phase_block["status"] = "success"
        else:
            phase_block.setdefault("status", "running")

        phase_block.setdefault("metrics", {})
        phase_block["metrics"].update(
            {
                "total_files": total,
                "successful": successful,
                "failed": failed,
                "partial": total - successful - failed,
                "total_chunks": sum(
                    len(f.get("chunk_paths", [])) for f in files.values()
                ),
            }
        )

        phase_block.setdefault("timestamps", {})
        if record.timestamps:
            if "start" not in phase_block["timestamps"]:
                phase_block["timestamps"]["start"] = record.timestamps.get(
                    "start"
                )
            phase_block["timestamps"]["last_completed"] = (
                record.timestamps.get("end")
            )
            phase_block["timestamps"]["duration"] = max(
                phase_block["timestamps"].get("duration", 0.0) or 0.0,
                record.timestamps.get("duration", 0.0) or 0.0,
            )

        phase_block.setdefault("artifacts", {})
        phase_block.setdefault("chunks", [])

        logger.info("Updated pipeline JSON for phase3 -> %s", file_id)
        return txn.data


def load_structure_from_json(json_path: str, file_id: str):
    """Load document structure from Phase 2 if available."""
    try:
        state = PipelineState(Path(json_path), validate_on_read=False)
        data = state.read(validate=False)
    except FileNotFoundError:
        logger.info(
            "Pipeline JSON not found when loading structure: %s", json_path
        )
        return None
    except StateError as exc:
        logger.warning("Could not load structure: %s", exc)
        return None

    structure = (
        data.get("phase2", {})
        .get("files", {})
        .get(file_id, {})
        .get("structure")
    )
    if structure:
        logger.info(
            "Loaded structure metadata from Phase 2: %s nodes", len(structure)
        )
    else:
        logger.info("No structure metadata found in Phase 2 for %s", file_id)
    return structure


def load_production_bible(file_id: str) -> Optional[Dict[str, Any]]:
    """Loads the Production Bible for a given file ID."""
    try:
        project_root = find_monorepo_root(Path(__file__).parent)
        bible_path = project_root / ".pipeline" / "books" / file_id / "production_bible.json"
        if bible_path.exists():
            with bible_path.open("r", encoding="utf-8") as f:
                bible = json.load(f)
            logger.info(f"Production Bible loaded for {file_id}")
            return bible
    except Exception as e:
        logger.warning(f"Could not load Production Bible for {file_id}: {e}")
    return None


def adjust_chunk_limits_for_pace(
    pace: str,
    soft_limit: int,
    hard_limit: int,
    emergency_limit: int,
    target_duration: float,
    emergency_duration: float,
) -> Tuple[int, int, int, float, float]:
    """Adjusts chunking limits based on the recommended pace from the Production Bible."""
    pace = pace.lower()
    adjustment_factor = 1.0

    if "fast-paced" in pace or "energetic" in pace:
        adjustment_factor = 0.80  # 20% shorter chunks
        logger.info(f"Pacing guide '{pace}': Adjusting chunk sizes shorter by 20%.")
    elif "slow" in pace or "deliberate" in pace or "measured" in pace:
        adjustment_factor = 1.15  # 15% longer chunks
        logger.info(f"Pacing guide '{pace}': Adjusting chunk sizes longer by 15%.")
    else:
        return soft_limit, hard_limit, emergency_limit, target_duration, emergency_duration

    new_soft = int(soft_limit * adjustment_factor)
    new_hard = int(hard_limit * adjustment_factor)
    new_emergency = int(emergency_limit * adjustment_factor)
    new_target_dur = target_duration * adjustment_factor
    new_emergency_dur = emergency_duration * adjustment_factor

    logger.info(f"Pace-adjusted limits: soft={new_soft}, hard={new_hard}, target_dur={new_target_dur:.1f}s")
    return new_soft, new_hard, new_emergency, new_target_dur, new_emergency_dur


def run_phase3(
    file_id: str, pipeline: dict, config: Phase3Config
) -> ChunkRecord:
    """Canonical Phase 3 execution entry point."""
    start_time = perf_counter()
    json_path = getattr(config, "json_path", "pipeline.json")
    chunks_dir = getattr(config, "chunks_dir", "chunks")
    pipeline_data = pipeline or {}
    fallback_used = False
    fallback_message = ""

    phase2_entry = (
        pipeline_data.get("phase2", {}).get("files", {}).get(file_id, {})
    )
    metadata = phase2_entry.get("metadata", {})
    text_path = getattr(
        config, "text_path_override", None
    ) or phase2_entry.get("extracted_text_path")
    structure_nodes = phase2_entry.get("structure") or []

    if not text_path:
        try:
            text_path = _fallback_find_text(file_id)
            fallback_used = True
            fallback_message = "Used fallback text discovery (phase2 missing)"
        except Exception as exc:
            raise FileNotFoundError(f"No text path found for {file_id}: {exc}")

    text_path_abs = ensure_absolute_path(text_path)
    if not text_path_abs.exists():
        raise FileNotFoundError(f"Text file not found: {text_path_abs}")

    logger.info(
        f"Processing Phase 3 for {file_id} with profile={config.phase3_profile}"
    )

    # Load the Production Bible to make chunking smarter
    production_bible = load_production_bible(file_id)
    pace_guide = None
    if production_bible:
        narrative_profile = production_bible.get("narrative_profile", {})
        if narrative_profile:
            pace_guide = narrative_profile.get("pace")

    with open(text_path_abs, "r", encoding="utf-8") as handle:
        raw_text = handle.read()
    if not raw_text.strip():
        raise ValueError(f"Text file is empty: {text_path_abs}")

    cleaned = clean_text(raw_text)
    text_hash = hash_text_content(cleaned)

    # Reuse check
    existing_phase3 = (
        pipeline_data.get("phase3", {}).get("files", {}).get(file_id, {})
    )
    existing_hash = existing_phase3.get("text_hash") or existing_phase3.get(
        "source_hash"
    )
    existing_paths = [
        str(ensure_absolute_path(p))
        for p in existing_phase3.get("chunk_paths") or []
    ]
    if (
        existing_phase3
        and existing_hash
        and existing_hash == text_hash
        and existing_paths
        and all(Path(p).exists() for p in existing_paths)
    ):
        logger.info("Phase 3 reuse: text hash matched, reusing chunks.")
        try:
            record = ChunkRecord(**existing_phase3)
        except Exception:
            record = ChunkRecord(
                text_path=str(text_path_abs),
                chunk_paths=existing_paths,
                coherence_scores=existing_phase3.get("coherence_scores", []),
                readability_scores=existing_phase3.get(
                    "readability_scores", []
                ),
                embeddings=existing_phase3.get("embeddings", []),
                status=existing_phase3.get("status", "success"),
                errors=existing_phase3.get("errors", []),
                timestamps=existing_phase3.get("timestamps", {}),
                chunk_metrics=existing_phase3.get("chunk_metrics", {}),
                suggested_voice=existing_phase3.get("suggested_voice"),
                applied_profile=existing_phase3.get("applied_profile"),
                genre_confidence=existing_phase3.get("genre_confidence"),
                coherence_threshold=getattr(
                    config, "coherence_threshold", None
                ),
                flesch_threshold=getattr(config, "flesch_threshold", None),
                source_hash=existing_hash,
                text_hash=existing_hash,
                structure_mode_used=existing_phase3.get(
                    "structure_mode_used", False
                ),
                chunk_voice_overrides=existing_phase3.get(
                    "chunk_voice_overrides", {}
                ),
                chunk_metadata=existing_phase3.get("chunk_metadata", []),
            )
        record.text_hash = text_hash
        ensure_chunk_metadata(record, existing_paths)

        # BUGFIX: Regenerate voice overrides if CLI voice provided (even in resume mode)
        cli_voice = getattr(config, "voice_override", None)
        if cli_voice or pipeline_data.get("tts_voice") or (
            file_id and pipeline_data.get("voice_overrides", {}).get(file_id)
        ):
            selected_voice = select_voice(
                profile_name=record.applied_profile or "general",
                file_id=file_id,
                pipeline_data=pipeline_data,
                cli_override=cli_voice,
            )
            if selected_voice:
                chunk_voice_overrides = {}
                for idx, chunk_path_str in enumerate(record.chunk_paths):
                    try:
                        cid = derive_chunk_id_from_path(Path(chunk_path_str), idx)
                        chunk_voice_overrides[cid] = selected_voice
                    except Exception as exc:
                        logger.warning(
                            "Failed to derive chunk_id for %s: %s", chunk_path_str, exc
                        )
                record.chunk_voice_overrides = chunk_voice_overrides
                logger.info(f"Resume mode: Updated voice overrides to '{selected_voice}' for {len(chunk_voice_overrides)} chunks")

        chunk_ids = [
            derive_chunk_id_from_path(Path(p), idx)
            for idx, p in enumerate(existing_paths)
        ]
        persist_phase3_result(
            json_path,
            pipeline_data,
            file_id,
            record,
            chunk_ids,
            existing_phase3.get("genre") or config.genre_profile,
            existing_phase3.get("profile") or config.genre_profile,
            existing_phase3.get("sentence_model", "spacy_lg"),
            bool(existing_phase3.get("embeddings_enabled", True)),
            text_hash,
            existing_phase3.get("structure_mode_used", False),
            fallback_used=False,
        )
        return record

    # Genre detection
    detected_genre = get_genre_from_metadata(metadata)
    genre_confidence = 1.0 if detected_genre else 0.0
    if (
        not detected_genre
        and config.genre_profile
        and config.genre_profile != "auto"
    ):
        detected_genre = config.genre_profile
        genre_confidence = 1.0

    if not detected_genre or detected_genre == "auto":
        detected_genre, genre_confidence, _ = detect_genre(cleaned, metadata)
        if genre_confidence < 0.55:
            logger.warning(
                f"Low genre detection confidence ({genre_confidence:.2f}) for {file_id}"
            )

    if not validate_genre(detected_genre):
        logger.warning(
            f"Invalid genre '{detected_genre}', defaulting to auto profile"
        )
        detected_genre = "auto"

    chunk_profile = get_profile(detected_genre)
    profile_overrides = chunk_profile.genre_duration_overrides.get(
        detected_genre, {}
    ) or chunk_profile.genre_duration_overrides.get(chunk_profile.name, {})

    phase3_profile = (config.phase3_profile or "full").lower()
    embeddings_enabled = phase3_profile == "full"
    lightweight = phase3_profile == "fast_cpu"
    sentence_preference = (
        "lg" if phase3_profile in {"full", "no_embeddings"} else "sm"
    )
    sentence_model_label = (
        f"spacy_{sentence_preference}"
        if sentence_preference in {"lg", "sm"}
        else "pysbd"
    )

    # Apply duration overrides and profile-specific caps
    target_duration = float(
        profile_overrides.get(
            "target_duration",
            getattr(config, "max_chunk_duration", 20.0),
        )
    )
    emergency_duration = float(
        profile_overrides.get(
            "max_duration",
            getattr(
                config,
                "emergency_chunk_duration",
                max(target_duration + 5.0, 24.0),
            ),
        )
    )
    min_duration = profile_overrides.get("min_duration")
    if phase3_profile == "fast_cpu":
        target_duration = min(
            target_duration,
            getattr(config, "max_chunk_duration", target_duration),
            16.0,
        )
        emergency_duration = min(
            emergency_duration, max(target_duration + 4.0, target_duration)
        )

    min_chars = max(
        getattr(config, "min_chunk_chars", 420), chunk_profile.min_chars
    )
    hard_limit = min(
        getattr(config, "hard_chunk_chars", chunk_profile.max_chars),
        chunk_profile.max_chars,
    )
    soft_limit = max(
        min_chars,
        min(getattr(config, "soft_chunk_chars", hard_limit), hard_limit),
    )
    emergency_limit = max(
        getattr(config, "emergency_chunk_chars", hard_limit + 200),
        hard_limit + 1,
    )

    # Adjust limits based on Production Bible pace guide
    if pace_guide:
        soft_limit, hard_limit, emergency_limit, target_duration, emergency_duration = adjust_chunk_limits_for_pace(
            pace_guide, soft_limit, hard_limit, emergency_limit, target_duration, emergency_duration
        )

    logger.info(
        f"Profile '{detected_genre}' with execution '{phase3_profile}': "
        f"soft={soft_limit}, hard={hard_limit}, emergency={emergency_limit}, "
        f"target_dur={target_duration}s, emergency_dur={emergency_duration}s, "
        f"embeddings={'on' if embeddings_enabled else 'off'}"
    )

    timers = {
        "sentence_detection": 0.0,
        "chunking": 0.0,
        "embeddings": 0.0,
        "structure": 0.0,
    }
    sentence_engine_used = sentence_model_label
    structure_mode_used = False

    # Chunking strategy selection (priority: LlamaChunker > Structure > Sentence)
    chunks: List[str] = []
    coherence: List[float] = []
    embeddings: List[List[float]] = []
    llama_mode_used = False
    timers["llama"] = 0.0

    # Option 1: LlamaChunker (LLM-powered semantic chunking)
    # Check env var override (UI can disable via DISABLE_LLAMA_CHUNKER=1)
    use_llama = config.use_llama_chunker and not os.environ.get("DISABLE_LLAMA_CHUNKER", "").lower() in ("1", "true", "yes")
    if use_llama:
        llama_start = perf_counter()
        try:
            chunks, coherence = _llama_chunk_text(
                cleaned,
                max_chars=hard_limit,
                min_chars=min_chars,
                model=config.llama_model,
            )
            llama_mode_used = True
            timers["llama"] = perf_counter() - llama_start
            logger.info(
                f"LlamaChunker created {len(chunks)} chunks in {timers['llama']:.2f}s"
            )
        except Exception as e:
            logger.warning(f"LlamaChunker failed, falling back to standard chunking: {e}")
            # Reset for fallback
            chunks = []
            coherence = []

    # Option 2: Structure-aware chunking (if LlamaChunker not used/failed)
    if (
        not chunks
        and config.use_structure_chunking
        and structure_nodes
        and should_use_structure_chunking(
            structure_nodes, config.min_structure_nodes
        )
    ):
        structure_mode_used = True
        structure_start = perf_counter()
        chunks, coherence, embeddings = chunk_by_structure(
            cleaned,
            structure_nodes,
            chunk_profile,
            max_chunk_words=chunk_profile.max_words,
            target_sec=target_duration,
            soft_merge_sec=max(4.0, target_duration / 2),
            words_per_minute=150.0,
            use_embeddings=embeddings_enabled,
        )
        timers["structure"] = perf_counter() - structure_start
        if embeddings_enabled:
            timers["embeddings"] = timers["structure"]

    # Option 3: Sentence-based chunking (default fallback)
    if not chunks:
        sentence_start = perf_counter()
        sentences, detected_engine = detect_sentences(
            cleaned,
            model_preference=sentence_preference,
            allow_pysbd=True,
            return_model=True,
        )
        timers["sentence_detection"] = perf_counter() - sentence_start
        sentence_engine_used = detected_engine

        if not sentences:
            raise ValueError("No sentences detected in text")

        chunk_start = perf_counter()
        chunks, coherence, embeddings = form_semantic_chunks(
            sentences,
            min_chars=min_chars,
            soft_limit=soft_limit,
            hard_limit=hard_limit,
            emergency_limit=emergency_limit,
            max_duration=target_duration,
            emergency_duration=emergency_duration,
            enable_embeddings=embeddings_enabled,
            lightweight=lightweight,
            min_duration=min_duration,
        )
        timers["chunking"] = perf_counter() - chunk_start
        if embeddings_enabled:
            timers["embeddings"] = timers["chunking"]

    if not chunks:
        raise ValueError("No chunks created from text")

    chunk_paths = [
        str(ensure_absolute_path(p))
        for p in save_chunks(str(text_path_abs), chunks, chunks_dir)
    ]
    chunk_ids = [
        derive_chunk_id_from_path(Path(p), idx)
        for idx, p in enumerate(chunk_paths)
    ]
    chunk_metadata = build_chunk_metadata(chunks, chunk_paths)

    readability = assess_readability(chunks)
    chunk_metrics = calculate_chunk_metrics(chunks, config)

    avg_coherence = sum(coherence) / len(coherence) if coherence else None
    avg_flesch = sum(readability) / len(readability) if readability else 0.0

    if avg_coherence is not None and avg_coherence < getattr(
        config, "coherence_threshold", 0.0
    ):
        logger.warning(
            f"Average coherence {avg_coherence:.3f} below threshold {config.coherence_threshold}"
        )
    if avg_flesch < getattr(config, "flesch_threshold", 0.0):
        logger.warning(
            f"Average readability {avg_flesch:.2f} below threshold {config.flesch_threshold}"
        )

    errors = []
    max_duration_cap = min(
        target_duration, getattr(config, "max_chunk_duration", target_duration)
    )
    if chunk_metrics.get("max_duration", 0) > max_duration_cap:
        errors.append(
            f"Some chunks exceed {max_duration_cap}s duration "
            f"(max: {chunk_metrics.get('max_duration', 0):.1f}s)"
        )

    status = "success" if not errors else "partial"

    selected_voice = select_voice(
        profile_name=detected_genre,
        file_id=file_id,
        pipeline_data=pipeline_data,
        cli_override=getattr(config, "voice_override", None),
    )
    chunk_voice_overrides = {}
    if selected_voice:
        for idx, chunk_path_str in enumerate(chunk_paths):
            try:
                cid = derive_chunk_id_from_path(Path(chunk_path_str), idx)
                chunk_voice_overrides[cid] = selected_voice
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to derive chunk_id for %s: %s", chunk_path_str, exc
                )

    end_time = perf_counter()
    duration = end_time - start_time

    record = ChunkRecord(
        text_path=str(text_path_abs),
        chunk_paths=chunk_paths,
        coherence_scores=coherence,
        readability_scores=readability,
        embeddings=embeddings,
        status=status,
        errors=errors,
        timestamps={
            "start": start_time,
            "end": end_time,
            "duration": duration,
        },
        chunk_metrics=chunk_metrics,
        chunk_metadata=chunk_metadata,
        suggested_voice=selected_voice,
        applied_profile=None if detected_genre == "auto" else detected_genre,
        genre_confidence=genre_confidence,
        coherence_threshold=getattr(config, "coherence_threshold", None),
        flesch_threshold=getattr(config, "flesch_threshold", None),
        source_hash=text_hash,
        text_hash=text_hash,
        chunk_voice_overrides=chunk_voice_overrides,
        structure_mode_used=structure_mode_used,
    )

    persist_phase3_result(
        json_path,
        pipeline_data,
        file_id,
        record,
        chunk_ids,
        detected_genre,
        record.applied_profile or detected_genre,
        sentence_engine_used,
        embeddings_enabled,
        text_hash,
        structure_mode_used,
        fallback_used=fallback_used,
        fallback_message=fallback_message,
    )

    logger.info(
        f"Timers - llama: {timers['llama']:.2f}s, sentence: {timers['sentence_detection']:.2f}s, "
        f"chunking: {timers['chunking']:.2f}s, embeddings: {timers['embeddings']:.2f}s, "
        f"structure: {timers['structure']:.2f}s (llama_mode={llama_mode_used})"
    )

    return record


def process_chunking(
    text_path: str,
    chunks_dir: str,
    config: ValidationConfig,
    json_path: str = "pipeline.json",
    file_id: str = None,
    cli_voice_override: str = None,
) -> ChunkRecord:
    """Backward-compatible wrapper that delegates to run_phase3."""
    if isinstance(config, Phase3Config):
        cfg = config
    else:
        cfg_payload = (
            config.model_dump()
            if hasattr(config, "model_dump")
            else config.dict()
        )
        cfg = Phase3Config(**cfg_payload)
    cfg.json_path = json_path
    cfg.chunks_dir = chunks_dir
    cfg.voice_override = cli_voice_override
    cfg.text_path_override = text_path
    if not file_id:
        file_id = derive_file_id_from_path(Path(text_path))

    pipeline = load_pipeline_state(json_path)
    return run_phase3(file_id=file_id, pipeline=pipeline, config=cfg)


def execute_phase3(
    file_id: str,
    json_path: str,
    config: Optional[Phase3Config] = None,
    resume: bool = False,
) -> ChunkRecord:
    """
    Standardized entry point for Phase 3 to align with downstream phases.

    Args:
        file_id: File identifier (matches phase2/phase4 entries)
        json_path: Path to pipeline.json
        config: Optional Phase3Config overrides
        resume: When true, reuse existing config.resume flag if present
    """
    cfg = config or Phase3Config()
    cfg.json_path = json_path
    if resume and hasattr(cfg, "resume"):
        cfg.resume = True
    pipeline = load_pipeline_state(json_path)
    return run_phase3(file_id=file_id, pipeline=pipeline, config=cfg)


def load_text_path_from_pipeline(
    json_path: str, file_id: str, strict: bool = False
) -> str:
    """Load text path from Phase 2 via PipelineState or fallback."""
    try:
        state = PipelineState(Path(json_path), validate_on_read=False)
        data = state.read(validate=False)
    except FileNotFoundError:
        logger.error("Pipeline JSON not found: %s", json_path)
        if strict:
            raise
        logger.info("Attempting fallback to file search...")
        return _fallback_find_text(file_id)
    except StateError as exc:
        logger.error("Failed to read pipeline state: %s", exc)
        if strict:
            raise
        logger.info("Attempting fallback to file search...")
        return _fallback_find_text(file_id)

    phase2_data = (
        data.get("phase2", {}).get("files", {}).get(file_id, {}) or {}
    )
    if not phase2_data:
        message = f"No Phase 2 data found for file_id: {file_id}"
        logger.error(message)
        if strict:
            raise KeyError(message)
        logger.info("Attempting fallback to file search...")
        return _fallback_find_text(file_id)

    if phase2_data.get("status") != "success":
        message = (
            f"Phase 2 status is not 'success': {phase2_data.get('status')}"
        )
        logger.error(message)
        if strict:
            raise ValueError(message)
        logger.info("Attempting fallback to file search...")
        return _fallback_find_text(file_id)

    text_path = phase2_data.get("extracted_text_path")
    if not text_path:
        message = "Phase 2 data missing 'extracted_text_path' field"
        logger.error(message)
        if strict:
            raise ValueError(message)
        logger.info("Attempting fallback to file search...")
        return _fallback_find_text(file_id)

    text_path_obj = ensure_absolute_path(text_path)
    if not text_path_obj.exists():
        message = f"Text file from Phase 2 not found: {text_path_obj}"
        logger.error(message)
        if strict:
            raise FileNotFoundError(message)
        logger.info("Attempting fallback to file search...")
        return _fallback_find_text(file_id)

    logger.info("Loaded text path from pipeline.json: %s", text_path_obj)
    return str(text_path_obj)


def _fallback_find_text(file_id: str) -> str:
    """Fallback: search for text file in phase2 extracted_text directory."""
    try:
        monorepo_root = find_monorepo_root(Path(__file__).parent)
    except FileNotFoundError as e:
        logger.error(f"Cannot find monorepo root for fallback: {e}")
        raise FileNotFoundError(
            f"Could not locate text file for {file_id}: monorepo root not found"
        )

    possible_dirs = [
        monorepo_root / "phase2-extraction" / "extracted_text",
        monorepo_root / "phase2_extraction" / "extracted_text",
        monorepo_root / "phase2" / "extracted_text",
    ]

    fallback_dir = None
    for dir_path in possible_dirs:
        if dir_path.exists() and dir_path.is_dir():
            fallback_dir = dir_path
            logger.info(f"Found phase2 directory: {fallback_dir}")
            break

    if not fallback_dir:
        raise FileNotFoundError(
            "Phase 2 extracted_text directory not found. Tried:\n"
            + "\n".join(f"  - {d}" for d in possible_dirs)
            + "\n\nPlease run Phase 2 first or check directory structure."
        )

    logger.info(
        f"Searching for text file matching '{file_id}' in: {fallback_dir}"
    )

    matching_files = []
    search_patterns = [
        file_id,
        file_id.replace("_", " "),
        file_id.replace(" ", "_"),
    ]

    try:
        for f in fallback_dir.iterdir():
            if not f.is_file() or f.suffix != ".txt":
                continue

            for pattern in search_patterns:
                if pattern.lower() in f.name.lower():
                    matching_files.append(f)
                    break
    except (PermissionError, OSError) as e:
        logger.error(f"Error reading directory {fallback_dir}: {e}")
        raise FileNotFoundError(f"Cannot access fallback directory: {e}")

    if not matching_files:
        try:
            dir_contents = [
                f.name for f in fallback_dir.iterdir() if f.is_file()
            ]
        except Exception:
            dir_contents = ["<unable to list>"]

        raise FileNotFoundError(
            f"No matching text file for '{file_id}' in {fallback_dir}\n"
            f"Searched for patterns: {search_patterns}\n"
            f"Directory contains {len(dir_contents)} files:\n"
            + "\n".join(f"  - {name}" for name in dir_contents[:10])
            + (
                f"\n  ... and {len(dir_contents) - 10} more"
                if len(dir_contents) > 10
                else ""
            )
        )

    primary_match = fallback_dir / f"{file_id}.txt"
    if primary_match.exists():
        text_path = str(primary_match)
        logger.info(f"Found exact match: {text_path}")
    else:
        matching_files.sort(key=lambda x: len(x.name))
        text_path = str(matching_files[0])
        logger.warning(
            f"No exact match for '{file_id}.txt', using: {matching_files[0].name}"
        )
        if len(matching_files) > 1:
            logger.info(
                f"Other matches found: {[f.name for f in matching_files[1:]]}"
            )

    return text_path


def load_config(config_path: str) -> Phase3Config:
    """Load configuration from YAML file."""
    config_path_abs = Path(config_path).resolve()

    try:
        with open(config_path_abs, "r") as f:
            config_data = yaml.safe_load(f) or {}
        logger.info(f"Loaded config from: {config_path_abs}")
    except FileNotFoundError:
        logger.warning(
            f"Config file not found: {config_path_abs}, using defaults"
        )
        config_data = {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}, using defaults")
        config_data = {}

    def _as_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    min_chars = _as_int(
        config_data.get("chunk_min_chars", config_data.get("min_chunk_chars")),
        1000,
    )
    hard_chars_value = config_data.get(
        "hard_chunk_chars",
        config_data.get("chunk_max_chars", config_data.get("max_chunk_chars")),
    )
    hard_chars = _as_int(hard_chars_value, 2000)
    if hard_chars < min_chars:
        logger.warning(
            "Configured hard_chunk_chars (%s) less than min_chunk_chars (%s); aligning to min",
            hard_chars,
            min_chars,
        )
        hard_chars = min_chars
    soft_candidate_raw = config_data.get(
        "soft_chunk_chars", config_data.get("chunk_soft_chars")
    )
    if soft_candidate_raw is None:
        soft_candidate = 1800
    else:
        soft_candidate = _as_int(soft_candidate_raw, 1800)
    if soft_candidate is not None:
        soft_chars = int(
            max(
                min_chars,
                min(soft_candidate, hard_chars),
            )
        )
    else:
        soft_chars = min(hard_chars, max(min_chars, 1800))

    emergency_candidate_raw = config_data.get(
        "emergency_chunk_chars",
        config_data.get("chunk_emergency_chars"),
    )
    emergency_candidate = (
        None
        if emergency_candidate_raw is None
        else _as_int(emergency_candidate_raw, hard_chars + 500)
    )
    if emergency_candidate is None:
        emergency_chars = max(hard_chars + 500, 3000, hard_chars + 1)
    else:
        emergency_chars = max(hard_chars + 1, int(emergency_candidate))

    try:
        max_duration = float(
            config_data.get(
                "max_chunk_duration",
                config_data.get("chunk_max_duration", 25.0),
            )
        )
    except (TypeError, ValueError):
        max_duration = 25.0
    try:
        emergency_duration = float(
            config_data.get(
                "emergency_chunk_duration",
                config_data.get(
                    "chunk_emergency_duration", max(38.0, max_duration + 5)
                ),
            )
        )
    except (TypeError, ValueError):
        emergency_duration = max(38.0, max_duration + 5)
    if emergency_duration <= max_duration:
        emergency_duration = max(max_duration + 1.0, 38.0)

    return Phase3Config(
        chunk_min_words=config_data.get(
            "chunk_min_words", config_data.get("min_chunk_words", 200)
        ),
        max_chunk_words=config_data.get(
            "chunk_max_words", config_data.get("max_chunk_words", 400)
        ),
        coherence_threshold=config_data.get("coherence_threshold", 0.87),
        flesch_threshold=config_data.get("flesch_threshold", 60.0),
        min_chunk_chars=min_chars,
        max_chunk_chars=hard_chars,
        max_chunk_duration=max_duration,
        soft_chunk_chars=soft_chars,
        hard_chunk_chars=hard_chars,
        emergency_chunk_chars=emergency_chars,
        emergency_chunk_duration=emergency_duration,
        genre_profile=config_data.get(
            "genre_profile", config_data.get("profile", "auto")
        ),
        json_path=config_data.get("json_path", "pipeline.json"),
        chunks_dir=config_data.get("chunks_dir", "chunks"),
        phase3_profile=config_data.get("phase3_profile", "full"),
        use_structure_chunking=config_data.get("use_structure_chunking", True),
        min_structure_nodes=int(
            config_data.get("min_structure_nodes", 10) or 10
        ),
    )


def main():
    """Main entry point for Phase 3 chunking."""
    logger.info(f"Starting Phase 3 from cwd: {os.getcwd()}")

    parser = argparse.ArgumentParser(
        description="Phase 3: Semantic Chunking for TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--file-id", "--file_id", dest="file_id", help="File ID from Phase 2"
    )
    parser.add_argument(
        "--text-path",
        "--text_path",
        "--text-file",
        dest="text_path",
        help="Direct path to text file (bypasses Phase 2 lookup)",
    )
    parser.add_argument(
        "--json-path",
        "--json_path",
        dest="json_path",
        default="pipeline.json",
        help="Path to pipeline JSON file",
    )
    parser.add_argument(
        "--chunks-dir",
        "--chunks_dir",
        "--output-dir",
        dest="chunks_dir",
        default="chunks",
        help="Output directory for chunk files",
    )
    parser.add_argument(
        "--config", help="Path to YAML config file with thresholds"
    )
    parser.add_argument(
        "--profile", help="Genre profile override (e.g., philosophy, fiction)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately if Phase 2 data missing",
    )
    parser.add_argument(
        "--voice",
        help="Override voice selection (e.g., landon_elkind, tom_weiss)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--silence_notifications",
        action="store_true",
        help="Silence astromech notifications (beeps are ON by default)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    if not args.silence_notifications:
        logger.info(
            "Astromech notifications: ON (use --silence_notifications to mute)."
        )

    if args.voice:
        if not validate_voice_id(args.voice):
            logger.error(f"Invalid voice ID: {args.voice}")
            logger.info(
                "Run 'python -m phase3_chunking.voice_selection --list' to see available voices"
            )
            if not args.silence_notifications:
                play_alert_beep(silence_mode=False)
            sys.exit(1)
        logger.info(f"Using CLI voice override: {args.voice}")

    if args.config:
        config = load_config(args.config)
    else:
        default_config_path = Path("config.yaml")
        if default_config_path.exists():
            logger.info(
                f"No config supplied; using default {default_config_path}"
            )
            config = load_config(str(default_config_path))
        else:
            config = Phase3Config()

    if args.profile:
        try:
            config = config.model_copy(update={"genre_profile": args.profile})
        except AttributeError:
            setattr(config, "genre_profile", args.profile)
        logger.info(f"Using CLI profile override: {args.profile}")
    elif getattr(config, "genre_profile", None):
        logger.info(f"Using configured profile: {config.genre_profile}")

    config.json_path = args.json_path
    config.chunks_dir = args.chunks_dir
    config.voice_override = args.voice

    try:
        config_dump = config.model_dump()
    except AttributeError:
        config_dump = config.dict() if hasattr(config, "dict") else {}
    logger.info(f"Configuration: {config_dump}")

    file_id = args.file_id
    pipeline_data = load_pipeline_state(args.json_path)

    if args.text_path:
        text_path_obj = Path(args.text_path).expanduser()
        if not text_path_obj.exists():
            logger.error(f"Specified text file not found: {args.text_path}")
            if not args.silence_notifications:
                play_alert_beep(silence_mode=False)
            sys.exit(1)
        text_path_obj = text_path_obj.resolve()
        config.text_path_override = str(text_path_obj)
        logger.info(
            f"Using directly specified text file: {config.text_path_override}"
        )
        if not file_id:
            file_id = derive_file_id_from_path(text_path_obj)
        else:
            logger.info(f"Using explicit file_id: {file_id}")
    else:
        if not file_id:
            logger.error(
                "Missing --file-id. Provide one or supply --text-file for automatic detection."
            )
            if not args.silence_notifications:
                play_alert_beep(silence_mode=False)
            sys.exit(2)
        if not pipeline_data.get("phase2", {}).get("files", {}).get(file_id):
            try:
                config.text_path_override = load_text_path_from_pipeline(
                    args.json_path, file_id, args.strict
                )
            except Exception as exc:
                if args.strict:
                    logger.error(
                        f"Strict mode: could not locate text for {file_id}: {exc}"
                    )
                    if not args.silence_notifications:
                        play_alert_beep(silence_mode=False)
                    sys.exit(1)
                logger.warning(
                    f"Phase2 lookup failed; runner will attempt fallback: {exc}"
                )

    if not file_id:
        logger.error("Unable to determine file_id after processing inputs")
        if not args.silence_notifications:
            play_alert_beep(silence_mode=False)
        sys.exit(2)

    try:
        logger.info(f"Processing file: {file_id}")
        record = run_phase3(
            file_id=file_id,
            pipeline=pipeline_data,
            config=config,
        )

        logger.info(f"Chunking completed with status: {record.status}")

        metrics = record.get_metrics()
        avg_coh = metrics.get("avg_coherence")
        coherence_display = f"{avg_coh:.4f}" if avg_coh is not None else "n/a"

        print("\n" + "=" * 60)
        print("PHASE 3 CHUNKING SUMMARY")
        print("=" * 60)
        print(f"File ID: {file_id}")
        print(f"Profile: {record.applied_profile or config.genre_profile}")
        print(
            f"Structure chunking: {getattr(record, 'structure_mode_used', False)}"
        )
        print(f"Status: {record.status}")
        print(f"Chunks created: {metrics['num_chunks']}")
        print(f"Average coherence: {coherence_display}")
        print(f"Average Flesch score: {metrics['avg_flesch']:.2f}")
        print(
            f"Average chunk size: {metrics.get('avg_char_length', 0):.0f} chars, {metrics.get('avg_word_count', 0):.0f} words"
        )
        print(
            f"Average duration: {metrics.get('avg_chunk_duration', 0):.1f}s (max: {metrics.get('max_chunk_duration', 0):.1f}s)"
        )
        print(f"Processing time: {metrics['duration']:.2f}s")

        if record.errors:
            print("\nWarnings/Errors:")
            for error in record.errors:
                print(f"  - {error}")

        print("=" * 60 + "\n")

        if record.status == "failed":
            exit_code = 1
        elif record.status == "partial":
            logger.warning("Chunking completed with warnings")
            exit_code = 0
        else:
            logger.info("Chunking completed successfully")
            exit_code = 0
        if not args.silence_notifications:
            if exit_code == 0:
                play_success_beep(silence_mode=False)
            else:
                play_alert_beep(silence_mode=False)
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Fatal error during chunking: {e}", exc_info=True)
        try:
            failure_hash = ""
            if getattr(config, "text_path_override", None):
                try:
                    raw_text = Path(config.text_path_override).read_text(
                        encoding="utf-8"
                    )
                    failure_hash = hash_text_content(clean_text(raw_text))
                except Exception:
                    failure_hash = ""
            failed_record = ChunkRecord(
                text_path=config.text_path_override or "unknown",
                chunk_paths=[],
                coherence_scores=[],
                readability_scores=[],
                embeddings=[],
                status="failed",
                errors=[f"Fatal error: {str(e)}"],
                timestamps={
                    "start": perf_counter(),
                    "end": perf_counter(),
                    "duration": 0,
                },
                text_hash=failure_hash or None,
            )
            persist_phase3_result(
                args.json_path,
                pipeline_data,
                file_id or "unknown",
                failed_record,
                [],
                getattr(config, "genre_profile", "auto"),
                getattr(config, "genre_profile", "auto"),
                "unknown",
                embeddings_enabled=False,
                text_hash=failure_hash or "",
                structure_mode_used=False,
            )
        except Exception as persist_exc:
            logger.error(
                f"Could not record failure in pipeline.json: {persist_exc}"
            )
        if not args.silence_notifications:
            play_alert_beep(silence_mode=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
