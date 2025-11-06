import argparse
import logging
import json
from time import perf_counter
from pathlib import Path
import re
import yaml
import os
import sys
import warnings

try:
    from filelock import FileLock
except ImportError:
    FileLock = None

# Smart import: works both as script and as module
try:
    from .models import ChunkRecord, ValidationConfig
    from .voice_selection import select_voice, validate_voice_id
    from .utils import (
        clean_text,
        detect_sentences,
        form_semantic_chunks,
        assess_readability,
        save_chunks,
        log_chunk_times,
        calculate_chunk_metrics,
    )
    from .structure_chunking import chunk_by_structure, should_use_structure_chunking
except ImportError:
    from models import ChunkRecord, ValidationConfig
    from voice_selection import select_voice, validate_voice_id
    from utils import (
        clean_text,
        detect_sentences,
        form_semantic_chunks,
        assess_readability,
        save_chunks,
        log_chunk_times,
        calculate_chunk_metrics,
    )
    from structure_chunking import chunk_by_structure, should_use_structure_chunking

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning, module="textstat.textstat")


def find_monorepo_root(start_path: Path) -> Path:
    """Find the monorepo root by looking for phase directories or env variable."""
    root_env = os.environ.get("MONOREPO_ROOT")
    if root_env:
        root_path = Path(root_env)
        if root_path.exists():
            logger.info(f"Using MONOREPO_ROOT from env: {root_env}")
            return root_path
        else:
            logger.warning(f"MONOREPO_ROOT env var points to non-existent path: {root_env}")
    
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
                
            subdirs = [d for d in current.iterdir() if d.is_dir() and d.name.startswith("phase")]
            if len(subdirs) >= 2:
                logger.info(f"Monorepo root detected at: {current}")
                return current
        except (PermissionError, OSError) as e:
            logger.warning(f"Error accessing {current}: {e}")
        
        current = current.parent
        level += 1
    
    raise FileNotFoundError("Monorepo root not found. Set MONOREPO_ROOT environment variable or ensure phase directories exist in parent path.")


def derive_file_id_from_path(text_path: Path) -> str:
    """Derive a stable file_id from a text file path when none is provided."""
    stem = text_path.stem.lower()
    sanitized = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    sanitized = re.sub(r"_+", "_", sanitized)
    if not sanitized:
        sanitized = re.sub(r"\s+", "_", stem) or "file"
    logger.info(f"Derived file_id '{sanitized}' from text path '{text_path.name}'")
    return sanitized


def load_structure_from_json(json_path: str, file_id: str):
    """Load document structure from Phase 2 if available."""
    try:
        json_path_abs = Path(json_path).absolute()
        if not json_path_abs.exists():
            return None
        
        with open(json_path_abs, "r") as f:
            data = json.load(f)
        
        phase2_data = data.get("phase2", {}).get("files", {}).get(file_id, {})
        structure = phase2_data.get("structure")
        
        if structure:
            logger.info(f"Loaded structure metadata from Phase 2: {len(structure)} nodes")
            return structure
        else:
            logger.info("No structure metadata found in Phase 2")
            return None
            
    except Exception as e:
        logger.warning(f"Could not load structure from Phase 2: {e}")
        return None


def process_chunking(
    text_path: str,
    chunks_dir: str,
    config: ValidationConfig,
    json_path: str = "pipeline.json",
    file_id: str = None,
    cli_voice_override: str = None,
) -> ChunkRecord:
    """Process a text file into semantic chunks with character-based optimization."""
    start_time = perf_counter()
    text_path_abs = Path(text_path).resolve()
    
    if not text_path_abs.exists():
        logger.error(f"Text file not found: {text_path_abs}")
        raise FileNotFoundError(f"Text file not found: {text_path_abs}")
    
    logger.info(f"Reading text from: {text_path_abs}")
    try:
        with open(text_path_abs, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        logger.error(f"Failed to read text file: {e}")
        raise
    
    if not text or not text.strip():
        raise ValueError(f"Text file is empty: {text_path_abs}")
    
    logger.info(f"Text length: {len(text)} characters")
    
    cleaned = clean_text(text)
    if not cleaned:
        raise ValueError("Text became empty after cleaning")
    
    structure = None
    if file_id:
        structure = load_structure_from_json(json_path, file_id)
    
    sentences = detect_sentences(cleaned)
    if not sentences:
        raise ValueError("No sentences detected in text")
    
    logger.info(f"Detected {len(sentences)} sentences")
    
    # Form chunks with character optimization
    # ALWAYS use semantic chunking (structure chunking creates huge chunks)
    logger.info("Using semantic chunking with character optimization")
    chunk_kwargs = {
        "min_chars": getattr(config, "min_chunk_chars", 1000),
        "max_duration": getattr(config, "max_chunk_duration", 25.0),
    }
    if hasattr(config, "soft_chunk_chars"):
        chunk_kwargs["soft_limit"] = config.soft_chunk_chars
    if hasattr(config, "hard_chunk_chars"):
        chunk_kwargs["hard_limit"] = config.hard_chunk_chars
    if hasattr(config, "emergency_chunk_chars"):
        chunk_kwargs["emergency_limit"] = config.emergency_chunk_chars
    if hasattr(config, "emergency_chunk_duration"):
        chunk_kwargs["emergency_duration"] = config.emergency_chunk_duration
    
    chunks, coherence, embeddings = form_semantic_chunks(
        sentences,
        **chunk_kwargs
    )
    
    if not chunks:
        raise ValueError("No chunks created from text")
    
    # Select voice for TTS synthesis
    pipeline_data = None
    try:
        json_path_abs = Path(json_path).absolute()
        if json_path_abs.exists():
            with open(json_path_abs, 'r') as f:
                pipeline_data = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load pipeline.json for voice selection: {e}")
    
    # Determine genre profile (from config or detect from structure)
    profile = config.genre_profile if hasattr(config, 'genre_profile') else 'auto'
    
    # Select voice using priority cascade
    selected_voice = select_voice(
        profile_name=profile,
        file_id=file_id,
        pipeline_data=pipeline_data,
        cli_override=cli_voice_override
    )
    logger.info(f"Selected voice for TTS: {selected_voice}")
    
    # Calculate chunk metrics
    chunk_metrics = calculate_chunk_metrics(chunks, config)
    chunk_metrics['selected_voice'] = selected_voice
    logger.info(f"Average chunk: {chunk_metrics['avg_char_length']:.0f} chars, "
                f"{chunk_metrics['avg_word_count']:.0f} words, "
                f"{chunk_metrics['avg_duration']:.1f}s duration")
    
    readability = assess_readability(chunks)
    
    avg_coherence = sum(coherence) / len(coherence) if coherence else 0.0
    avg_flesch = sum(readability) / len(readability) if readability else 0.0
    
    logger.info(f"Chunking complete: {len(chunks)} chunks created")
    logger.info(f"Average coherence: {avg_coherence:.4f}")
    logger.info(f"Average Flesch score: {avg_flesch:.2f}")
    
    errors = []
    if chunk_metrics['max_duration'] > config.max_chunk_duration:
        errors.append(f"Some chunks exceed {config.max_chunk_duration}s duration (max: {chunk_metrics['max_duration']:.1f}s)")
    
    status = "success" if not errors else "partial"
    
    try:
        chunk_paths = save_chunks(str(text_path_abs), chunks, chunks_dir)
    except Exception as e:
        logger.error(f"Failed to save chunks: {e}")
        errors.append(f"Save error: {str(e)}")
        status = "failed"
        chunk_paths = []
    
    log_chunk_times(chunks, config)
    
    end_time = perf_counter()
    duration = end_time - start_time
    
    logger.info(f"Total processing time: {duration:.2f}s")
    
    record = ChunkRecord(
        text_path=str(text_path_abs),
        chunk_paths=chunk_paths,
        coherence_scores=coherence,
        readability_scores=readability,
        embeddings=embeddings,
        status=status,
        errors=errors,
        timestamps={"start": start_time, "end": end_time, "duration": duration},
        chunk_metrics=chunk_metrics,
        suggested_voice=selected_voice,
        applied_profile=None if profile == "auto" else profile,
        coherence_threshold=getattr(config, "coherence_threshold", None),
        flesch_threshold=getattr(config, "flesch_threshold", None),
    )
    
    return record


def load_from_json(json_path: str, file_id: str, strict: bool = False) -> str:
    """Load text path from Phase 2 JSON or fallback to file search."""
    json_path_abs = Path(json_path).absolute()
    lock_file = str(json_path_abs) + ".lock"
    
    if FileLock:
        with FileLock(lock_file, timeout=10):
            return _load_from_json_impl(json_path_abs, file_id, strict)
    else:
        logger.warning("filelock not installed; proceeding without file lock")
        return _load_from_json_impl(json_path_abs, file_id, strict)


def _load_from_json_impl(json_path_abs: Path, file_id: str, strict: bool = False) -> str:
    """Implementation of load_from_json with actual logic."""
    try:
        if not json_path_abs.exists():
            raise FileNotFoundError(f"Pipeline JSON not found: {json_path_abs}")
        
        with open(json_path_abs, "r") as f:
            data = json.load(f)
        
        phase2_data = data.get("phase2", {}).get("files", {}).get(file_id, {})
        
        if not phase2_data:
            raise KeyError(f"No Phase 2 data found for file_id: {file_id}")
        
        if phase2_data.get("status") != "success":
            raise ValueError(f"Phase 2 status is not 'success': {phase2_data.get('status')}")
        
        text_path = phase2_data.get("extracted_text_path", "")
        
        if not text_path:
            raise ValueError("Phase 2 data missing 'extracted_text_path' field")
        
        text_path_obj = Path(text_path)
        if not text_path_obj.exists():
            raise FileNotFoundError(f"Text file from Phase 2 not found: {text_path}")
        
        logger.info(f"Loaded text path from JSON: {text_path}")
        return text_path
        
    except Exception as e:
        logger.error(f"Failed to load from Phase 2 JSON: {e}")
        
        if strict:
            logger.error("Strict mode enabled, not attempting fallback")
            raise
        
        logger.info("Attempting fallback to file search...")
        return _fallback_find_text(file_id)


def _fallback_find_text(file_id: str) -> str:
    """Fallback: search for text file in phase2 extracted_text directory."""
    try:
        monorepo_root = find_monorepo_root(Path(__file__).parent)
    except FileNotFoundError as e:
        logger.error(f"Cannot find monorepo root for fallback: {e}")
        raise FileNotFoundError(f"Could not locate text file for {file_id}: monorepo root not found")
    
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
            f"Phase 2 extracted_text directory not found. Tried:\n" +
            "\n".join(f"  - {d}" for d in possible_dirs) +
            f"\n\nPlease run Phase 2 first or check directory structure."
        )
    
    logger.info(f"Searching for text file matching '{file_id}' in: {fallback_dir}")
    
    matching_files = []
    search_patterns = [file_id, file_id.replace("_", " "), file_id.replace(" ", "_")]
    
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
            dir_contents = [f.name for f in fallback_dir.iterdir() if f.is_file()]
        except Exception:
            dir_contents = ["<unable to list>"]
            
        raise FileNotFoundError(
            f"No matching text file for '{file_id}' in {fallback_dir}\n"
            f"Searched for patterns: {search_patterns}\n"
            f"Directory contains {len(dir_contents)} files:\n" +
            "\n".join(f"  - {name}" for name in dir_contents[:10]) +
            (f"\n  ... and {len(dir_contents) - 10} more" if len(dir_contents) > 10 else "")
        )
    
    primary_match = fallback_dir / f"{file_id}.txt"
    if primary_match.exists():
        text_path = str(primary_match)
        logger.info(f"Found exact match: {text_path}")
    else:
        matching_files.sort(key=lambda x: len(x.name))
        text_path = str(matching_files[0])
        logger.warning(f"No exact match for '{file_id}.txt', using: {matching_files[0].name}")
        if len(matching_files) > 1:
            logger.info(f"Other matches found: {[f.name for f in matching_files[1:]]}")
    
    return text_path


def merge_to_json(record: ChunkRecord, json_path: str, file_id: str, fallback_used: bool = False, fallback_message: str = ""):
    """Merge chunking results into pipeline JSON file."""
    json_path_abs = Path(json_path).absolute()
    lock_file = str(json_path_abs) + ".lock"
    
    if FileLock:
        with FileLock(lock_file, timeout=10):
            _merge_to_json_impl(record, json_path_abs, file_id, fallback_used, fallback_message)
    else:
        _merge_to_json_impl(record, json_path_abs, file_id, fallback_used, fallback_message)


def _merge_to_json_impl(record: ChunkRecord, json_path_abs: Path, file_id: str, fallback_used: bool = False, fallback_message: str = ""):
    """Implementation of merge_to_json with actual logic."""
    try:
        with open(json_path_abs, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.info(f"Creating new pipeline JSON: {json_path_abs}")
        data = {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error, creating new structure: {e}")
        data = {}
    
    if "phase3" not in data:
        data["phase3"] = {"files": {}, "errors": [], "metrics": {}}
    
    data["phase3"]["files"][file_id] = record.model_dump()
    
    metrics = record.get_metrics()
    data["phase3"]["files"][file_id]["metrics"] = metrics
    
    if fallback_used:
        error_entry = {
            "file_id": file_id,
            "type": "Phase2Desync",
            "message": fallback_message or "Fallback used due to missing/invalid Phase 2 data",
            "timestamp": record.timestamps.get("start", 0),
        }
        data["phase3"]["errors"].append(error_entry)
        logger.warning(f"Recorded Phase 2 desync error for {file_id}")
    
    all_files = data["phase3"]["files"]
    if all_files:
        data["phase3"]["metrics"] = {
            "total_files": len(all_files),
            "successful": sum(1 for f in all_files.values() if f.get("status") == "success"),
            "partial": sum(1 for f in all_files.values() if f.get("status") == "partial"),
            "failed": sum(1 for f in all_files.values() if f.get("status") == "failed"),
            "total_chunks": sum(len(f.get("chunk_paths", [])) for f in all_files.values()),
        }
    
    try:
        with open(json_path_abs, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Updated pipeline JSON: {json_path_abs}")
    except Exception as e:
        logger.error(f"Failed to write JSON: {e}")
        raise


def load_config(config_path: str) -> ValidationConfig:
    """Load configuration from YAML file."""
    config_path_abs = Path(config_path).resolve()
    
    try:
        with open(config_path_abs, "r") as f:
            config_data = yaml.safe_load(f) or {}
        logger.info(f"Loaded config from: {config_path_abs}")
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path_abs}, using defaults")
        config_data = {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}, using defaults")
        config_data = {}
    
    def _as_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)
    
    min_chars = _as_int(config_data.get("chunk_min_chars", config_data.get("min_chunk_chars")), 1000)
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
    soft_candidate_raw = config_data.get("soft_chunk_chars", config_data.get("chunk_soft_chars"))
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
        None if emergency_candidate_raw is None else _as_int(emergency_candidate_raw, hard_chars + 500)
    )
    if emergency_candidate is None:
        emergency_chars = max(hard_chars + 500, 3000, hard_chars + 1)
    else:
        emergency_chars = max(hard_chars + 1, int(emergency_candidate))
    
    try:
        max_duration = float(config_data.get("max_chunk_duration", config_data.get("chunk_max_duration", 25.0)))
    except (TypeError, ValueError):
        max_duration = 25.0
    try:
        emergency_duration = float(
            config_data.get(
                "emergency_chunk_duration",
                config_data.get("chunk_emergency_duration", max(38.0, max_duration + 5)),
            )
        )
    except (TypeError, ValueError):
        emergency_duration = max(38.0, max_duration + 5)
    if emergency_duration <= max_duration:
        emergency_duration = max(max_duration + 1.0, 38.0)
    
    return ValidationConfig(
        chunk_min_words=config_data.get("chunk_min_words", config_data.get("min_chunk_words", 200)),
        max_chunk_words=config_data.get("chunk_max_words", config_data.get("max_chunk_words", 400)),
        coherence_threshold=config_data.get("coherence_threshold", 0.87),
        flesch_threshold=config_data.get("flesch_threshold", 60.0),
        min_chunk_chars=min_chars,
        max_chunk_chars=hard_chars,
        max_chunk_duration=max_duration,
        soft_chunk_chars=soft_chars,
        hard_chunk_chars=hard_chars,
        emergency_chunk_chars=emergency_chars,
        emergency_chunk_duration=emergency_duration,
        genre_profile=config_data.get("genre_profile", config_data.get("profile", "auto")),
    )


def main():
    """Main entry point for Phase 3 chunking."""
    logger.info(f"Starting Phase 3 from cwd: {os.getcwd()}")
    
    parser = argparse.ArgumentParser(
        description="Phase 3: Semantic Chunking for TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--file-id", "--file_id", dest="file_id", help="File ID from Phase 2")
    parser.add_argument("--text-path", "--text_path", "--text-file", dest="text_path",
                        help="Direct path to text file (bypasses Phase 2 lookup)")
    parser.add_argument("--json-path", "--json_path", dest="json_path", default="pipeline.json",
                        help="Path to pipeline JSON file")
    parser.add_argument("--chunks-dir", "--chunks_dir", "--output-dir", dest="chunks_dir",
                        default="chunks", help="Output directory for chunk files")
    parser.add_argument("--config", help="Path to YAML config file with thresholds")
    parser.add_argument("--profile", help="Genre profile override (e.g., philosophy, fiction)")
    parser.add_argument("--strict", action="store_true", help="Fail immediately if Phase 2 data missing")
    parser.add_argument("--voice", help="Override voice selection (e.g., landon_elkind, tom_weiss)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Validate voice override if provided
    if args.voice:
        if not validate_voice_id(args.voice):
            logger.error(f"Invalid voice ID: {args.voice}")
            logger.info("Run 'python -m phase3_chunking.voice_selection --list' to see available voices")
            sys.exit(1)
        logger.info(f"Using CLI voice override: {args.voice}")
    
    if args.config:
        config = load_config(args.config)
    else:
        default_config_path = Path("config.yaml")
        if default_config_path.exists():
            logger.info(f"No config supplied; using default {default_config_path}")
            config = load_config(str(default_config_path))
        else:
            config = ValidationConfig()
    
    if args.profile:
        try:
            config = config.model_copy(update={"genre_profile": args.profile})
        except AttributeError:
            setattr(config, "genre_profile", args.profile)  # Fallback for older pydantic versions
        logger.info(f"Using CLI profile override: {args.profile}")
    elif getattr(config, "genre_profile", None):
        logger.info(f"Using configured profile: {config.genre_profile}")
    
    logger.info(f"Configuration: {config.model_dump()}")
    
    fallback_used = False
    fallback_message = ""
    text_path = None
    file_id = args.file_id
    
    if args.text_path:
        text_path_obj = Path(args.text_path).expanduser()
        if not text_path_obj.exists():
            logger.error(f"Specified text file not found: {args.text_path}")
            sys.exit(1)
        text_path_obj = text_path_obj.resolve()
        text_path = str(text_path_obj)
        logger.info(f"Using directly specified text file: {text_path}")
        
        if not file_id:
            file_id = derive_file_id_from_path(text_path_obj)
        else:
            logger.info(f"Using explicit file_id: {file_id}")
    else:
        if not file_id:
            logger.error("Missing --file-id. Provide one or supply --text-file for automatic detection.")
            sys.exit(2)
        try:
            text_path = load_from_json(args.json_path, file_id, args.strict)
        except Exception as e:
            fallback_used = True
            fallback_message = f"Failed to load from Phase 2: {str(e)}"
            logger.error(fallback_message)
            
            if args.strict:
                logger.error("Strict mode enabled, exiting")
                sys.exit(1)
            
            logger.error("Both primary and fallback methods failed")
            sys.exit(1)
    
    if not file_id:
        logger.error("Unable to determine file_id after processing inputs")
        sys.exit(2)
    
    try:
        logger.info(f"Processing file: {file_id}")
        record = process_chunking(
            text_path, args.chunks_dir, config, 
            json_path=args.json_path, file_id=file_id,
            cli_voice_override=args.voice
        )
        
        logger.info(f"Chunking completed with status: {record.status}")
        
        merge_to_json(record, args.json_path, file_id, fallback_used, fallback_message)
        
        metrics = record.get_metrics()
        print("\n" + "="*60)
        print("PHASE 3 CHUNKING SUMMARY")
        print("="*60)
        print(f"File ID: {file_id}")
        print(f"Status: {record.status}")
        print(f"Chunks created: {metrics['num_chunks']}")
        print(f"Average coherence: {metrics['avg_coherence']:.4f}")
        print(f"Average Flesch score: {metrics['avg_flesch']:.2f}")
        print(f"Average chunk size: {metrics.get('avg_char_length', 0):.0f} chars, {metrics.get('avg_word_count', 0):.0f} words")
        print(f"Average duration: {metrics.get('avg_chunk_duration', 0):.1f}s (max: {metrics.get('max_chunk_duration', 0):.1f}s)")
        print(f"Processing time: {metrics['duration']:.2f}s")
        
        if record.errors:
            print(f"\nWarnings/Errors:")
            for error in record.errors:
                print(f"  - {error}")
        
        print("="*60 + "\n")
        
        if record.status == "failed":
            sys.exit(1)
        elif record.status == "partial":
            logger.warning("Chunking completed with warnings")
            sys.exit(0)
        else:
            logger.info("Chunking completed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Fatal error during chunking: {e}", exc_info=True)
        
        try:
            failed_record = ChunkRecord(
                text_path=text_path or "unknown",
                chunk_paths=[],
                coherence_scores=[],
                readability_scores=[],
                embeddings=[],
                status="failed",
                errors=[f"Fatal error: {str(e)}"],
                timestamps={"start": perf_counter(), "end": perf_counter(), "duration": 0},
            )
            merge_to_json(failed_record, args.json_path, file_id, fallback_used, fallback_message)
        except Exception as merge_error:
            logger.error(f"Could not record failure in JSON: {merge_error}")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
