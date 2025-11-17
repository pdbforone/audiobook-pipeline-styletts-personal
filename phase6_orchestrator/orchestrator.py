#!/usr/bin/env python3
"""
Phase 6: Single-File Orchestrator (Enhanced)
Production-ready orchestrator - runs phases 1-5 sequentially with:
- Rich progress reporting
- Robust Conda environment handling
- Resume from checkpoints
- Error handling with retries
- Actionable error messages
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import yaml
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for pipeline_common
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline_common import PipelineState, StateError

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich not available. Install with: pip install rich")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console() if RICH_AVAILABLE else None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_ROOT = PROJECT_ROOT / "audiobooks"
PHASE4_AUDIO_DIR: Optional[Path] = None
_ORCHESTRATOR_CONFIG: Optional[Dict] = None


def get_orchestrator_config() -> Dict:
    """Load phase6 config.yaml once."""
    global _ORCHESTRATOR_CONFIG
    if _ORCHESTRATOR_CONFIG is not None:
        return _ORCHESTRATOR_CONFIG

    config_path = Path(__file__).with_name("config.yaml")
    data: Dict = {}
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except Exception as exc:
            logger.warning("Failed to read orchestrator config (%s); using defaults.", exc)
    _ORCHESTRATOR_CONFIG = data
    return data


def get_pipeline_mode() -> str:
    return get_orchestrator_config().get("pipeline_mode", "commercial").lower()


def get_tts_engine() -> str:
    return get_orchestrator_config().get("tts_engine", "chatterbox").lower()


def set_phase4_audio_dir(audio_dir: Path) -> None:
    global PHASE4_AUDIO_DIR
    PHASE4_AUDIO_DIR = audio_dir.resolve()


def print_status(message: str, style: str = "bold"):
    """Print status message with Rich or fallback to print"""
    if console:
        console.print(message, style=style)
    else:
        print(message)


def print_panel(content: str, title: str = "", style: str = ""):
    """Print panel with Rich or fallback"""
    if console:
        console.print(Panel(content, title=title, style=style))
    else:
        print(f"\n{'='*60}")
        if title:
            print(f"{title}")
            print("="*60)
        print(content)
        print("="*60 + "\n")


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA256 for reuse decisions."""
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            sha.update(block)
    return sha.hexdigest()


def play_sound(success: bool = True) -> None:
    """Play a short audible cue on Windows; no-op elsewhere."""
    try:
        if sys.platform != "win32":
            return
        import winsound

        if success:
            # Two quick beeps: success
            winsound.Beep(1000, 200)
            winsound.Beep(1300, 200)
        else:
            # Lower, longer tone: failure
            winsound.Beep(400, 600)
    except Exception as exc:  # If sound is unavailable, ignore
        logger.debug("Sound playback skipped: %s", exc)


def humanize_title(file_id: str) -> str:
    """Convert file_id or filename into a readable title."""
    name = Path(file_id).stem
    name = re.sub(r"[_\-]+", " ", name).strip()
    return name.title() if name else "Audiobook"


def resolve_phase5_audiobook_path(file_id: str, pipeline_json: Path, phase5_dir: Path) -> Path:
    """Locate the final audiobook path recorded in pipeline.json (with fallbacks)."""
    audiobook_path: Optional[Path] = None
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        pipeline_data = state.read()
    except Exception as exc:
        logger.warning(f"Failed to read pipeline.json for archive lookup: {exc}")
        pipeline_data = {}

    phase5_data = pipeline_data.get("phase5", {}) or {}
    raw_path = phase5_data.get("output_file")

    if not raw_path:
        phase5_files = phase5_data.get("files", {}) or {}
        if phase5_files:
            candidate_key = file_id if file_id in phase5_files else next(iter(phase5_files))
            entry = phase5_files.get(candidate_key, {})
            raw_path = entry.get("path") or entry.get("output_file")

    if raw_path:
        audiobook_path = Path(raw_path)
        if not audiobook_path.is_absolute():
            audiobook_path = (phase5_dir / audiobook_path).resolve()
    else:
        audiobook_path = (phase5_dir / "processed" / "audiobook.mp3").resolve()

    return audiobook_path


def concat_phase5_from_existing(phase_dir: Path, file_id: str, pipeline_json: Path) -> bool:
    """
    Build final MP3 from existing enhanced WAVs without re-running enhancement.
    """
    processed_dir = phase_dir / "processed"
    wavs = sorted(processed_dir.glob("enhanced_*.wav"))
    if not wavs:
        logger.error("Concat-only mode: no enhanced_*.wav files found.")
        return False

    list_file = phase_dir / "temp_concat_list.txt"
    try:
        list_file.write_text("\n".join([f"file '{p.resolve().as_posix()}'" for p in wavs]), encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to write concat list: %s", exc)
        return False

    mp3_path = processed_dir / "audiobook.mp3"
    if mp3_path.exists():
        mp3_path.unlink()

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "warning",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-ac",
        "1",
        "-ar",
        "24000",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        "-id3v2_version",
        "3",
        "-metadata",
        f"title={humanize_title(file_id)}",
        "-metadata",
        f"artist={file_id}",
        str(mp3_path),
    ]

    result = subprocess.run(cmd, cwd=str(phase_dir), capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Concat-only ffmpeg failed (exit %s): %s", result.returncode, result.stderr[-1000:])
        return False

    logger.info("Concat-only MP3 created at %s", mp3_path)

    # Update pipeline.json
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        with state.transaction() as txn:
            phase5 = txn.data.setdefault("phase5", {"status": "partial", "files": {}})
            files = phase5.setdefault("files", {})
            entry = files.get(file_id, {})
            entry.update(
                {
                    "status": "success",
                    "output_file": serialize_path_for_pipeline(mp3_path),
                    "chunks_completed": len(wavs),
                    "total_chunks": len(wavs),
                    "audio_dir": serialize_path_for_pipeline(processed_dir),
                }
            )
            files[file_id] = entry
            phase5["status"] = "success"
        logger.info("pipeline.json updated for concat-only run")
    except Exception as exc:
        logger.warning("Failed to update pipeline.json after concat-only: %s", exc)

    try:
        list_file.unlink()
    except Exception:
        pass

    return True


def archive_final_audiobook(file_id: str, pipeline_json: Path) -> None:
    """Save a copy of the final audiobook that survives Phase 5 cleanup."""
    phase5_dir = find_phase_dir(5)
    if not phase5_dir:
        logger.warning("Cannot archive audiobook: Phase 5 directory not found")
        return

    source_path = resolve_phase5_audiobook_path(file_id, pipeline_json, phase5_dir)

    if not source_path.exists():
        logger.warning(f"Archive skipped: audiobook not found at {source_path}")
        return

    title = humanize_title(file_id)
    archive_dir = ARCHIVE_ROOT / title
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = archive_dir / f"{title}_{timestamp}.mp3"

    try:
        shutil.copy2(source_path, dest_path)
        # Also copy canonical name (audiobook.mp3) in the title folder
        canonical_path = archive_dir / "audiobook.mp3"
        shutil.copy2(source_path, canonical_path)
        logger.info(f"Archived final audiobook to {dest_path} and {canonical_path}")
    except Exception as exc:
        logger.warning(f"Failed to archive audiobook copy: {exc}")


def get_clean_env_for_poetry() -> Dict[str, str]:
    """
    Create a clean environment for Poetry subprocess calls.

    When the orchestrator runs in its own Poetry virtualenv, os.environ contains
    Poetry/virtualenv variables that interfere with Poetry's ability to detect
    and activate the correct virtualenv for phase subdirectories.

    This function creates a clean environment by removing Poetry-specific variables
    while preserving necessary system variables.

    Returns:
        Clean environment dict suitable for subprocess.run(env=...)
    """
    env = os.environ.copy()

    # Remove Poetry and virtualenv variables that interfere with Poetry's detection
    vars_to_remove = [
        'VIRTUAL_ENV',           # Points to current virtualenv
        'POETRY_ACTIVE',         # Indicates Poetry is active
        'PYTHONHOME',            # Can override Python location
        '_OLD_VIRTUAL_PATH',     # Backup of PATH before virtualenv activation
        '_OLD_VIRTUAL_PYTHONHOME',  # Backup of PYTHONHOME
    ]

    for var in vars_to_remove:
        env.pop(var, None)

    # Clean PATH to remove current virtualenv's Scripts/bin directory
    # This allows Poetry to add the correct virtualenv's Scripts/bin
    if 'PATH' in env:
        path_parts = env['PATH'].split(os.pathsep)
        # Filter out paths containing current virtualenv indicators
        clean_path_parts = [
            p for p in path_parts
            if not any(indicator in p.lower() for indicator in ['virtualenvs', '.venv', 'poetry'])
        ]
        env['PATH'] = os.pathsep.join(clean_path_parts)

    return env


def check_conda_environment(env_name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if Conda environment exists and is accessible.

    Returns:
        (exists: bool, error_message: Optional[str])
    """
    try:
        # Check if conda is available
        result = subprocess.run(
            ["conda", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "Conda not found. Install Miniconda or Anaconda first."
        
        # Check if environment exists
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if env_name not in result.stdout:
            error_msg = (
                f"Conda environment '{env_name}' not found.\n\n"
                f"Create it with:\n"
                f"  cd phase4_tts\n"
                f"  conda env create -f environment.yml\n"
                f"  conda activate {env_name}\n"
                f"  pip install git+https://github.com/resemble-ai/chatterbox.git\n"
                f"  pip install piper-tts librosa requests torchaudio"
            )
            return False, error_msg
        
        # Verify environment can be activated
        test_cmd = ["conda", "run", "-n", env_name, "python", "--version"]
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, f"Cannot activate '{env_name}': {result.stderr}"
        
        logger.info(f"OK Conda environment '{env_name}' is ready")
        return True, None
        
    except FileNotFoundError:
        error_msg = (
            "Conda not found in PATH.\n\n"
            "Install Miniconda from: https://docs.conda.io/en/latest/miniconda.html\n"
            "Or add Conda to PATH if already installed."
        )
        return False, error_msg
    except subprocess.TimeoutExpired:
        return False, "Conda command timed out. Check your Conda installation."
    except Exception as e:
        return False, f"Conda check failed: {str(e)}"


def load_pipeline_json(json_path: Path) -> Dict:
    """
    Load pipeline.json with atomic state manager.

    Returns:
        Dictionary with pipeline data, or empty dict on error
    """
    try:
        state = PipelineState(json_path, validate_on_read=False)
        data = state.read()

        if data:
            logger.info(f"Loaded pipeline.json: {len(data)} phase(s) recorded")
        else:
            logger.info(f"Pipeline JSON not found: {json_path} (will create on first run)")

        return data

    except StateError as e:
        logger.error(f"Corrupt pipeline.json: {e}")

        # Try to restore from backup
        try:
            state = PipelineState(json_path)
            backups = state.list_backups()
            if backups:
                logger.info(f"Found {len(backups)} backup(s), restoring most recent...")
                if state.restore_backup(backups[0]):
                    logger.info("✓ Restored from backup")
                    return state.read()
        except Exception as restore_error:
            logger.warning(f"Backup restore failed: {restore_error}")

        # Last resort: start fresh
        logger.warning("Starting with empty pipeline state")
        return {}

    except Exception as e:
        logger.error(f"Failed to load pipeline.json: {e}")
        return {}


def should_skip_phase2(file_path: Path, file_id: str, pipeline_json: Path) -> bool:
    """
    Decide whether to skip Phase 2 based on existing successful extraction and matching hash.
    Uses the source_hash from Phase 2 (preferred) or Phase 1 hash as fallback.
    """
    if not pipeline_json.exists():
        return False

    try:
        pipeline_data = load_pipeline_json(pipeline_json)
    except Exception as exc:
        logger.warning("Phase 2 reuse: could not load pipeline.json (%s); will run Phase 2.", exc)
        return False

    phase2_entry = pipeline_data.get("phase2", {}).get("files", {}).get(file_id, {})
    if phase2_entry.get("status") != "success":
        return False

    extracted_path = (
        phase2_entry.get("extracted_text_path")
        or phase2_entry.get("path")
        or phase2_entry.get("output_file")
    )
    if not extracted_path or not Path(extracted_path).exists():
        return False

    recorded_hash = phase2_entry.get("source_hash")
    phase1_hash = (
        pipeline_data.get("phase1", {})
        .get("files", {})
        .get(file_id, {})
        .get("hash")
    )

    # If no hash recorded, still allow skip to honor prior success (legacy runs)
    if not recorded_hash and not phase1_hash:
        logger.info("Phase 2 reuse: found existing success (no hash recorded); skipping.")
        return True

    try:
        current_hash = compute_sha256(file_path)
    except Exception as exc:
        logger.warning("Phase 2 reuse: failed to hash source (%s); will run Phase 2.", exc)
        return False

    expected_hash = recorded_hash or phase1_hash
    if expected_hash and current_hash == expected_hash:
        logger.info("Phase 2 reuse: hash match (%s); skipping.", file_id)
        return True

    logger.info("Phase 2 reuse: source hash changed; re-running Phase 2.")
    return False


def check_phase_status(pipeline_data: Dict, phase_num: int, file_id: str) -> str:
    """
    Check status of a phase for a specific file.
    
    Returns:
        "success", "failed", "partial", or "pending"
    """
    phase_key = f"phase{phase_num}"
    phase_data = pipeline_data.get(phase_key, {})
    files = phase_data.get("files", {})
    
    # Try exact match first
    if file_id in files:
        return files[file_id].get("status", "pending")
    
    # Try fuzzy match
    for key in files.keys():
        if file_id in key or key in file_id:
            logger.info(f"Phase {phase_num}: Using key '{key}' for file_id '{file_id}'")
            return files[key].get("status", "pending")

    # Fall back to overall status if no file-specific data exists
    overall_status = phase_data.get("status")
    if overall_status in {"success", "partial", "failed"}:
        return overall_status
    
    return "pending"


def find_phase_dir(phase_num: int, variant: Optional[str] = None) -> Optional[Path]:
    """Find directory for a phase number.

    Args:
        phase_num: Phase number (1-5)
        variant: Optional variant (e.g., 'xtts' for phase3b-xtts-chunking)
    """
    project_root = PROJECT_ROOT

    # Handle Phase 3 variants (Phase 3b for XTTS)
    if phase_num == 3 and variant == "xtts":
        phase_name = "phase3b-xtts-chunking"
    else:
        mapping = {
            1: "phase1-validation",
            2: "phase2-extraction",
            3: "phase3-chunking",
            4: "phase4_tts",
            5: "phase5_enhancement"
        }
        phase_name = mapping.get(phase_num)

    if not phase_name:
        return None

    phase_dir = project_root / phase_name
    if phase_dir.exists():
        return phase_dir

    logger.error(f"Phase {phase_num} directory not found: {phase_dir}")
    return None


def load_phase3_chunks(file_id: str, pipeline_json: Path) -> Tuple[str, List[str]]:
    """Return the resolved Phase 3 key and its chunk paths."""
    state = PipelineState(pipeline_json, validate_on_read=False)
    pipeline = state.read()
    phase3_files = pipeline.get("phase3", {}).get("files", {})

    resolved_id = file_id
    chunks: List[str] = []

    if file_id in phase3_files:
        chunks = phase3_files[file_id].get("chunk_paths", [])
    else:
        for key, entry in phase3_files.items():
            if file_id in key or key in file_id:
                logger.info(f"Using Phase 3 file_id: '{key}'")
                resolved_id = key
                chunks = entry.get("chunk_paths", [])
                break

    if not chunks:
        raise RuntimeError(
            f"No chunks found for '{file_id}'. Available keys: {list(phase3_files.keys())}"
        )

    return resolved_id, chunks


def run_phase_with_retry(
    phase_num: int,
    file_path: Path,
    file_id: str,
    pipeline_json: Path,
    max_retries: int = 2,
    voice_id: Optional[str] = None,
    pipeline_mode: str = "commercial",
    tts_engine: Optional[str] = None,
) -> bool:
    """
    Run a phase with retry logic.

    Args:
        phase_num: Phase number (1-5)
        file_path: Input file path
        file_id: File identifier
        pipeline_json: Path to pipeline.json
        max_retries: Maximum retry attempts (default 2)
        voice_id: Optional voice ID for Phase 4 TTS
        pipeline_mode: Pipeline mode (commercial or personal)
        tts_engine: Optional TTS engine override (xtts or kokoro)

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt}/{max_retries} for Phase {phase_num}")
            time.sleep(2)  # Brief pause before retry
        
        success = run_phase(
            phase_num,
            file_path,
            file_id,
            pipeline_json,
            voice_id,
            pipeline_mode,
            tts_engine,
        )
        
        if success:
            return True
    
    logger.error(f"Phase {phase_num} failed after {max_retries + 1} attempts")
    return False


def run_phase(
    phase_num: int,
    file_path: Path,
    file_id: str,
    pipeline_json: Path,
    voice_id: Optional[str] = None,
    pipeline_mode: str = "commercial",
    tts_engine: Optional[str] = None,
) -> bool:
    """
    Run a single phase.

    Args:
        phase_num: Phase number (1-5)
        file_path: Input file path
        file_id: File identifier
        pipeline_json: Path to pipeline.json
        voice_id: Optional voice ID for Phase 4 TTS
        pipeline_mode: Pipeline mode (commercial or personal)
        tts_engine: Optional TTS engine override (xtts or kokoro)

    Returns:
        True if successful, False otherwise
    """
    # Determine engine early (needed for Phase 3 routing)
    engine = tts_engine if tts_engine else get_tts_engine()

    # Special handling for Phase 3 (route to Phase 3b for XTTS)
    if phase_num == 3:
        variant = "xtts" if engine == "xtts" else None
        phase_dir = find_phase_dir(phase_num, variant=variant)
        if not phase_dir:
            return False

        logger.info(f"Phase 3: Using chunking variant for {engine}: {phase_dir}")
        return run_phase_standard(phase_num, phase_dir, file_path, file_id, pipeline_json)

    # Standard phase directory lookup
    phase_dir = find_phase_dir(phase_num)
    if not phase_dir:
        return False

    logger.info(f"Phase {phase_num} directory: {phase_dir}")

    # Special handling for Phase 4 (Multi-Engine TTS)
    if phase_num == 4:
        logger.info(f"Phase 4: Using TTS engine: {engine}")

        # Route to appropriate Phase 4 implementation
        if engine not in {"xtts", "kokoro"}:
            logger.error(f"Unknown TTS engine: {engine}")
            return False

        # Use unified multi-engine system
        return run_phase4_multi_engine(phase_dir, file_id, pipeline_json, voice_id, engine, pipeline_mode)

    # Standard phases (1, 2, 5) use Poetry
    return run_phase_standard(phase_num, phase_dir, file_path, file_id, pipeline_json)


def run_phase_standard(
    phase_num: int,
    phase_dir: Path,
    file_path: Path,
    file_id: str,
    pipeline_json: Path
) -> bool:
    """Run a standard phase using Poetry."""

    # Fast-path reuse for Phase 2: if extraction already exists with matching hash, skip.
    if phase_num == 2 and should_skip_phase2(file_path, file_id, pipeline_json):
        return True

    # Check for venv and install if needed
    venv_dir = phase_dir / ".venv"
    if not venv_dir.exists():
        logger.info(f"Installing dependencies for Phase {phase_num}...")
        try:
            # Configure Poetry to use in-project venv
            subprocess.run(
                ["poetry", "config", "virtualenvs.in-project", "true", "--local"],
                cwd=str(phase_dir),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Install dependencies
            result = subprocess.run(
                ["poetry", "install", "--no-root"],
                cwd=str(phase_dir),
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                logger.error(f"Poetry install failed: {result.stderr}")
                logger.error(f"Poetry stdout: {result.stdout}")
                return False
            logger.info("Dependencies installed successfully")
        except subprocess.TimeoutExpired:
            logger.error(f"Poetry install timeout (300s)")
            return False
        except Exception as e:
            logger.error(f"Poetry install error: {e}")
            return False
    else:
        logger.info(f"Phase {phase_num} venv already exists")
    
    # Special handling for Phase 5 (needs config.yaml update)
    if phase_num == 5:
        concat_hint = os.environ.get("PHASE5_CONCAT_ONLY") == "1"
        processed_dir = phase_dir / "processed"
        existing_wavs = list(processed_dir.glob("enhanced_*.wav"))
        if concat_hint and existing_wavs:
            logger.info("Phase 5: concat-only hint set, detected %d enhanced WAVs. Building MP3...", len(existing_wavs))
            if concat_phase5_from_existing(phase_dir, file_id, pipeline_json):
                archive_final_audiobook(file_id, pipeline_json)
                return True
            logger.warning("Phase 5: concat-only failed; falling back to full run.")
        elif existing_wavs and len(existing_wavs) >= 100:
            logger.info("Phase 5: detected %d enhanced WAVs, attempting concat-only.", len(existing_wavs))
            if concat_phase5_from_existing(phase_dir, file_id, pipeline_json):
                archive_final_audiobook(file_id, pipeline_json)
                return True
            logger.warning("Phase 5: concat-only failed; falling back to full run.")
        return run_phase5_with_config_update(phase_dir, file_id, pipeline_json)
    
    # Build command with direct script path
    # Special handling for Phase 3b (lightweight script)
    if phase_dir.name == "phase3b-xtts-chunking":
        main_script = phase_dir / "sentence_splitter.py"
        if not main_script.exists():
            logger.error(f"Script not found: {main_script}")
            return False
        # Phase 3b is standalone Python (no Poetry)
        cmd = [sys.executable, str(main_script)]
    else:
        # Standard phases use Poetry
        module_names = {
            1: "phase1_validation",
            2: "phase2_extraction",
            3: "phase3_chunking"
        }

        module_name = module_names.get(phase_num)

        script_names = {
            1: "validation.py",
            2: "extraction.py",
            3: "main.py"
        }
        script_name = script_names.get(phase_num, "main.py")
        main_script = phase_dir / "src" / module_name / script_name

        if not main_script.exists():
            logger.error(f"Script not found: {main_script}")
            return False

        # Use relative path from phase directory (critical for Poetry venv resolution)
        script_relative = main_script.relative_to(phase_dir)
        cmd = ["poetry", "run", "python", str(script_relative)]
    
    # Add phase-specific arguments
    if phase_num == 1:
        cmd.extend([f"--file={file_path}", f"--json_path={pipeline_json}"])
    elif phase_num == 2:
        cmd.extend([f"--file={file_path}", f"--file_id={file_id}", f"--json_path={pipeline_json}"])
    elif phase_num == 3:
        # Phase 3 needs config for coherence threshold
        cmd.extend([f"--file_id={file_id}", f"--json_path={pipeline_json}", "--config=config.yaml"])
    
    logger.info(f"Command: {' '.join(cmd)}")
    
    # Execute
    start_time = time.perf_counter()
    try:
        env = get_clean_env_for_poetry()
        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            env=env,  # Clean environment for Poetry virtualenv detection
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=18000
        )
        
        duration = time.perf_counter() - start_time
        
        if result.returncode != 0:
            logger.error(f"Phase {phase_num} FAILED (exit {result.returncode}) in {duration:.1f}s")
            logger.error(f"Error: {result.stderr[-500:]}")  # Last 500 chars
            return False
        
        logger.info(f"Phase {phase_num} SUCCESS in {duration:.1f}s")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"Phase {phase_num} TIMEOUT (600s)")
        return False
    except Exception as e:
        logger.error(f"Phase {phase_num} ERROR: {e}")
        return False


def run_phase4_multi_engine(
    phase_dir: Path,
    file_id: str,
    pipeline_json: Path,
    voice_id: Optional[str] = None,
    engine: str = "xtts",
    pipeline_mode: str = "commercial",
) -> bool:
    """
    Run Phase 4 with multi-engine support (XTTS v2 primary, Kokoro fallback).

    Uses the unified main_multi_engine.py with Poetry environment.

    Args:
        phase_dir: Path to phase4_tts directory
        file_id: File identifier
        pipeline_json: Path to pipeline.json
        voice_id: Optional voice ID for TTS
        engine: Engine name (xtts or kokoro)
        pipeline_mode: Pipeline mode (commercial or personal)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Phase 4 directory: {phase_dir}")

    engines_to_try = [engine]
    if engine == "xtts":
        engines_to_try.append("kokoro")

    for index, engine_name in enumerate(engines_to_try):
        logger.info("Running Phase 4 via %s (attempt %d/%d)", engine_name, index + 1, len(engines_to_try))

        cmd = [
            sys.executable,
            str(phase_dir / "engine_runner.py"),
            f"--engine={engine_name}",
            f"--file_id={file_id}",
            f"--json_path={pipeline_json}",
        ]

        if voice_id:
            cmd.append(f"--voice={voice_id}")
        cmd.append("--config=config.yaml")

        disable_fallback = len(engines_to_try) > 1 and engine_name != engines_to_try[-1]
        if disable_fallback:
            cmd.append("--disable_fallback")

        start_time = time.perf_counter()
        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
        duration = time.perf_counter() - start_time

        if result.stdout:
            logger.info("Phase 4 output (%s):\n%s", engine_name, result.stdout[-1000:])

        if result.returncode == 0:
            logger.info("Phase 4 SUCCESS with %s in %.1fs", engine_name, duration)
            return True

        logger.error("Phase 4 FAILED with %s (exit %s) in %.1fs", engine_name, result.returncode, duration)
        logger.error("stderr tail:\n%s", result.stderr[-500:])

    logger.error("Phase 4 failed for all configured engines")
    return False

def run_phase5_with_config_update(phase_dir: Path, file_id: str, pipeline_json: Path) -> bool:
    """
    Run Phase 5 with config.yaml update.
    
    Phase 5 reads pipeline.json path from config.yaml, not command-line args.
    """
    # Ensure Poetry uses local venv and install dependencies
    logger.info("Configuring Phase 5 environment...")
    
    # Step 1: Configure Poetry to use in-project venv
    try:
        subprocess.run(
            ["poetry", "config", "virtualenvs.in-project", "true", "--local"],
            cwd=str(phase_dir),
            capture_output=True,
            text=True,
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Could not configure Poetry (non-fatal): {e}")
    
    # Step 2: Ensure dependencies are installed (idempotent - fast if already installed)
    logger.info(f"Verifying Phase 5 dependencies...")
    try:
        result = subprocess.run(
            ["poetry", "install", "--no-root"],
            cwd=str(phase_dir),
            env=get_clean_env_for_poetry(),  # Use clean environment for Poetry
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            logger.error(f"Poetry install failed (exit {result.returncode})")
            if result.stdout:
                logger.error(f"STDOUT: {result.stdout}")
            if result.stderr:
                logger.error(f"STDERR: {result.stderr}")
            return False
        logger.info("Dependencies verified/installed successfully")
    except Exception as e:
        logger.error(f"Poetry install error: {e}")
        return False
    
    config_path = phase_dir / "src" / "phase5_enhancement" / "config.yaml"
    
    # Read existing config
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to read Phase 5 config.yaml: {e}")
        return False
    
    # Update pipeline_json path (make it absolute)
    config['pipeline_json'] = str(pipeline_json)
    
    # Phase 5 looks for audio in input_dir (which should point to Phase 4 output)
    # Default is "../phase4_tts/audio_chunks" which should work from phase5_enhancement
    if PHASE4_AUDIO_DIR:
        config['input_dir'] = str(PHASE4_AUDIO_DIR)
    elif 'input_dir' not in config:
        config['input_dir'] = "../phase4_tts/audio_chunks"
    
    # Set quality settings to prevent chunk exclusion
    # Disable quality validation so all chunks are included
    config['quality_validation_enabled'] = False
    config['snr_threshold'] = 10.0
    config['noise_reduction_factor'] = 0.1

    # Allow resume by default; only wipe state if explicitly requested
    if 'resume_on_failure' not in config:
        config['resume_on_failure'] = True
    logger.info("Resume_on_failure=%s", config.get('resume_on_failure'))

    clear_phase5 = os.environ.get("PHASE5_CLEAR", "0") == "1"
    if clear_phase5:
        try:
            state = PipelineState(pipeline_json, validate_on_read=False)
            with state.transaction() as txn:
                if 'phase5' in txn.data:
                    old_chunk_count = len(txn.data.get('phase5', {}).get('chunks', []))
                    logger.info(f"WARNING: Clearing {old_chunk_count} old Phase 5 chunks from pipeline.json")
                    del txn.data['phase5']
            logger.info("✓ Cleared Phase 5 data from pipeline.json")
        except Exception as e:
            logger.warning(f"Could not clear Phase 5 data (non-fatal): {e}")

        import shutil
        processed_dir = phase_dir / "processed"
        output_dir = phase_dir / "output"
        try:
            if processed_dir.exists():
                file_count = len(list(processed_dir.glob("*.wav")))
                if file_count > 0:
                    logger.info(f"WARNING: Clearing {file_count} old files from processed/ directory")
                    shutil.rmtree(processed_dir)
                    processed_dir.mkdir(parents=True, exist_ok=True)
                    logger.info("OK Cleared processed/ directory")

            if output_dir.exists():
                audiobook_path = output_dir / "audiobook.mp3"
                if audiobook_path.exists():
                    logger.info("WARNING: Removing old audiobook.mp3")
                    audiobook_path.unlink()
                    logger.info("OK Removed old audiobook.mp3")
        except Exception as e:
            logger.warning(f"Could not clear processed files (non-fatal): {e}")
    
    # Always refresh audiobook title so metadata matches current input
    config['audiobook_title'] = humanize_title(file_id)

    # Write updated config
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Updated Phase 5 config with pipeline_json: {pipeline_json}")
    except Exception as e:
        logger.error(f"Failed to update Phase 5 config.yaml: {e}")
        return False
    
    # Build command - Phase 5 only accepts --config, --chunk_id, --skip_concatenation
    # Run as module (not script) because main.py uses relative imports
    cmd = [
        "poetry", "run", "python", "-m", "phase5_enhancement.main",
        "--config=config.yaml"
    ]

    logger.info(f"Command: {' '.join(cmd)}")
    
    # Execute
    start_time = time.perf_counter()
    try:
        env = get_clean_env_for_poetry()
        src_path = phase_dir / "src"
        if src_path.exists():
            existing_py_path = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = (
                f"{src_path}{os.pathsep}{existing_py_path}" if existing_py_path else str(src_path)
            )
            logger.info(f"Phase 5 PYTHONPATH override: {env['PYTHONPATH']}")

        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            env=env,  # Clean environment for Poetry virtualenv detection
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=1800  # 30 minutes for full enhancement
        )
        
        duration = time.perf_counter() - start_time
        
        if result.returncode != 0:
            logger.error(f"Phase 5 FAILED (exit {result.returncode}) in {duration:.1f}s")
            logger.error(f"Error: {result.stderr[-1000:]}")
            return False
        
        logger.info(f"Phase 5 SUCCESS in {duration:.1f}s")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"Phase 5 TIMEOUT (1800s)")
        return False
    except Exception as e:
        logger.error(f"Phase 5 ERROR: {e}")
        return False


def run_phase5_5_subtitles(phase5_dir: Path, file_id: str, pipeline_json: Path, enable_subtitles: bool = False) -> bool:
    """
    Phase 5.5: Generate subtitles (optional).

    Args:
        phase5_dir: Path to phase5_enhancement directory
        file_id: File identifier
        pipeline_json: Path to pipeline.json
        enable_subtitles: If False, skip this phase

    Returns:
        True if successful or skipped, False if failed
    """
    if not enable_subtitles:
        logger.info("Phase 5.5 (Subtitles): Skipped (disabled)")
        return True

    logger.info("=== Phase 5.5: Subtitle Generation ===")

    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        pipeline_data = state.read()

        audiobook_path = resolve_phase5_audiobook_path(file_id, pipeline_json, phase5_dir)
        if not audiobook_path.exists():
            logger.error(f"Phase 5.5: Audiobook not found at {audiobook_path}")
            return False

        phase2_data = pipeline_data.get('phase2', {})
        phase2_files = phase2_data.get('files', {}) or {}
        text_file = None
        if phase2_files:
            phase2_file_id = file_id if file_id in phase2_files else next(iter(phase2_files))
            phase2_entry = phase2_files.get(phase2_file_id, {})
            text_file = (
                phase2_entry.get('extracted_text_path')
                or phase2_entry.get('path')
                or phase2_entry.get('output_file')
            )
            if file_id not in phase2_files and phase2_entry:
                logger.warning(
                    "Phase 5.5: file_id '%s' not found in Phase 2, using '%s'",
                    file_id,
                    phase2_file_id,
                )
        else:
            logger.warning("Phase 5.5: No phase2.files entries found in pipeline.json")

        if not text_file:
            text_file = Path("phase2-extraction") / "extracted_text" / f"{file_id}.txt"
            if not text_file.exists():
                logger.warning(
                    "Phase 5.5: Could not find Phase 2 text path, defaulting to %s",
                    text_file,
                )

        # Build subtitle generation command
        # Run as module (not script) because subtitles.py uses relative imports
        cmd = [
            'poetry', 'run', 'python', '-m', 'phase5_enhancement.subtitles',
            '--audio', str(audiobook_path),
            '--file-id', file_id,
            '--output-dir', str(phase5_dir / 'subtitles'),
            '--model', 'small'  # Balance of speed and accuracy
        ]

        # Add reference text if available for WER calculation
        if text_file and Path(text_file).exists():
            cmd.extend(['--reference-text', str(text_file)])
        else:
            text_file = None  # ensure log clarity

        logger.info(f"Phase 5.5: Resolved audiobook path: {audiobook_path}")
        logger.info(f"Phase 5.5: Resolved reference text: {text_file or 'None (using audio-only workflow)'}")

        logger.info(f"Command: {' '.join(cmd)}")

        # Execute subtitle generation
        start_time = time.perf_counter()
        result = subprocess.run(
            cmd,
            cwd=str(phase5_dir),
            env=get_clean_env_for_poetry(),  # Clean environment for Poetry virtualenv detection
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=3600  # 60 minutes for subtitle generation
        )

        duration = time.perf_counter() - start_time

        if result.returncode != 0:
            logger.error(f"Phase 5.5 FAILED (exit {result.returncode}) in {duration:.1f}s")
            logger.error(f"Error: {result.stderr[-1000:]}")

            # Update pipeline.json with failure atomically
            try:
                with state.transaction() as txn:
                    txn.data['phase5_5'] = {
                        'status': 'failed',
                        'error': result.stderr[-500:],
                        'timestamp': time.time()
                    }
            except Exception as e:
                logger.warning(f"Could not update pipeline.json with failure: {e}")

            return False

        # Parse output to get subtitle paths
        srt_path = phase5_dir / 'subtitles' / f'{file_id}.srt'
        vtt_path = phase5_dir / 'subtitles' / f'{file_id}.vtt'
        metrics_path = phase5_dir / 'subtitles' / f'{file_id}_metrics.json'

        # Load metrics if available
        metrics = {}
        if metrics_path.exists():
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)

        # Update pipeline.json with success atomically
        with state.transaction() as txn:
            txn.data['phase5_5'] = {
                'status': 'success',
                'srt_file': str(srt_path),
                'vtt_file': str(vtt_path),
                'metrics': metrics,
                'timestamp': time.time(),
                'duration': duration
            }

        logger.info(f"Phase 5.5 SUCCESS in {duration:.1f}s")
        logger.info(f"SRT: {srt_path}")
        logger.info(f"VTT: {vtt_path}")
        if metrics.get('coverage'):
            logger.info(f"Coverage: {metrics['coverage']:.2%}")
        if metrics.get('wer') is not None:
            logger.info(f"WER: {metrics['wer']:.2%}")

        return True

    except subprocess.TimeoutExpired:
        logger.error("Phase 5.5 TIMEOUT (3600s)")
        return False
    except Exception as e:
        logger.error(f"Phase 5.5 ERROR: {e}", exc_info=True)
        return False


def process_single_chunk(
    phase_dir: Path,
    conda_env: str,
    main_script: str,
    ref_file: str,
    chunk_id: int,
    file_id: str,
    pipeline_json: Path,
    voice_id: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> bool:
    """Process a single TTS chunk with optional voice override."""
    cmd = [
        "conda", "run",
        "-n", conda_env,
        "--no-capture-output",
        "python", main_script,
        f"--chunk_id={chunk_id}",
        f"--file_id={file_id}",
        f"--json_path={pipeline_json}",
        "--config=config.yaml"  # Phase 4 expects --config, not --enable-splitting
    ]
    
    if extra_args:
        cmd.extend(extra_args)

    # Add voice override if specified
    if voice_id:
        cmd.append(f"--voice_id={voice_id}")
    
    # Set UTF-8 encoding for subprocess (critical for Unicode text)
    import os
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=None,  # 20 minutes per chunk
            env=env  # Pass environment with UTF-8 encoding
        )
        
        if result.returncode != 0:
            error_log = phase_dir / f"chunk_{chunk_id}_error.log"
            with open(error_log, 'w', encoding='utf-8', errors='replace') as f:
                f.write(result.stderr)
                f.write("\n\nSTDOUT:\n")
                f.write(result.stdout)
            logger.warning(f"Chunk {chunk_id} failed (logged to {error_log})")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Chunk {chunk_id} timeout (20min)")
        return False
    except Exception as e:
        logger.warning(f"Chunk {chunk_id} error: {e}")
        return False


def summarize_results(pipeline_json: Path):
    """Create summary table of pipeline results."""
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        data = state.read()
    except:
        return
    
    if not RICH_AVAILABLE:
        return
    
    table = Table(title="Pipeline Results")
    table.add_column("Phase", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    for i in range(1, 6):
        phase_key = f"phase{i}"
        phase_data = data.get(phase_key, {})
        status = phase_data.get("status", "pending")
        
        # Get details
        details = ""
        if phase_key == "phase3":
            files = phase_data.get("files", {})
            for fid, fdata in files.items():
                chunk_count = len(fdata.get("chunk_paths", []))
                details = f"{chunk_count} chunks"
                break
        elif phase_key == "phase4":
            files = phase_data.get("files", {})
            for fid, fdata in files.items():
                audio_count = len(fdata.get("chunk_audio_paths", []))
                avg_mos = fdata.get("metrics", {}).get("avg_mos", 0)
                details = f"{audio_count} audio chunks, MOS={avg_mos:.2f}"
                break
        
        # Color-code status
        if status == "success":
            status_display = f"[green]{status}[/green]"
        elif status == "failed":
            status_display = f"[red]{status}[/red]"
        else:
            status_display = f"[yellow]{status}[/yellow]"
        
        table.add_row(f"Phase {i}", status_display, details)
    
    console.print(table)


def run_pipeline(
    file_path: Path,
    voice_id: Optional[str] = None,
    tts_engine: str = "chatterbox",
    mastering_preset: Optional[str] = None,
    phases: List[int] = None,
    pipeline_json: Optional[Path] = None,
    enable_subtitles: bool = False,
    max_retries: int = 3,
    no_resume: bool = False,
    progress_callback=None,
    concat_only: bool = False,
) -> Dict:
    """
    Programmatic interface to run the audiobook pipeline.

    Args:
        file_path: Path to input book file (EPUB, PDF, etc.)
        voice_id: Voice ID to use for TTS
        tts_engine: TTS engine to use ("chatterbox", "f5", "xtts")
        mastering_preset: Audio mastering preset name
        phases: List of phases to run (default: [1,2,3,4,5])
        pipeline_json: Path to pipeline.json (default: PROJECT_ROOT/pipeline.json)
        enable_subtitles: Whether to generate subtitles (Phase 5.5)
        max_retries: Max retries per phase
        no_resume: Disable resume from checkpoint (run all phases fresh)
        progress_callback: Optional callback(phase_num, percentage, message)

    Returns:
        Dict with:
            - success: bool
            - audiobook_path: Path to final audiobook
            - metadata: Dict of pipeline metadata
            - error: Optional error message
    """
    # Resolve paths
    file_path = Path(file_path).resolve()
    if not file_path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "audiobook_path": None,
            "metadata": {}
        }

    file_id = file_path.stem

    if pipeline_json is None:
        pipeline_json = PROJECT_ROOT / "pipeline.json"
    else:
        pipeline_json = Path(pipeline_json).resolve()

    if phases is None:
        phases = [1, 2, 3, 4, 5]

    # Load orchestrator config and update if needed
    orchestrator_config = get_orchestrator_config()
    pipeline_mode = orchestrator_config.get("pipeline_mode", "personal").lower()

    # Load pipeline.json (skip if no_resume is True)
    pipeline_data = {} if no_resume else load_pipeline_json(pipeline_json)

    # Concat-only hint for Phase 5
    if concat_only:
        os.environ["PHASE5_CONCAT_ONLY"] = "1"
    else:
        os.environ.pop("PHASE5_CONCAT_ONLY", None)

    # Run phases
    completed_phases = []

    for phase_num in phases:
        # Call progress callback if provided
        if progress_callback:
            progress_callback(phase_num, 0.0, f"Starting Phase {phase_num}...")

        # Check resume status
        status = check_phase_status(pipeline_data, phase_num, file_id)
        if status == "success":
            logger.info(f"Skipping Phase {phase_num} (already completed)")
            completed_phases.append(phase_num)
            if progress_callback:
                progress_callback(phase_num, 100.0, "Already completed")
            continue

        # Run phase with retries
        logger.info(f"Running Phase {phase_num}...")

        success = run_phase_with_retry(
            phase_num,
            file_path,
            file_id,
            pipeline_json,
            max_retries=max_retries,
            voice_id=voice_id,
            pipeline_mode=pipeline_mode,
            tts_engine=tts_engine,
        )

        if not success:
            return {
                "success": False,
                "error": f"Pipeline failed at Phase {phase_num}",
                "audiobook_path": None,
                "metadata": {}
            }

        logger.info(f"Phase {phase_num} completed successfully")

        if progress_callback:
            progress_callback(phase_num, 100.0, "Complete")

        # Archive after Phase 5
        if phase_num == 5:
            archive_final_audiobook(file_id, pipeline_json)

        completed_phases.append(phase_num)

    # Phase 5.5: Subtitles (optional)
    if 5 in completed_phases and enable_subtitles:
        logger.info("Running Phase 5.5 (Subtitles)...")
        phase5_dir = find_phase_dir(5)
        if phase5_dir:
            success = run_phase5_5_subtitles(
                phase5_dir,
                file_id,
                pipeline_json,
                enable_subtitles=True
            )
            if not success:
                logger.warning("Phase 5.5 (Subtitles) failed - continuing anyway")

    # Find final audiobook path
    audiobook_path = None
    phase5_dir = find_phase_dir(5)
    if phase5_dir:
        audiobook_path = resolve_phase5_audiobook_path(file_id, pipeline_json, phase5_dir)

    # Reload pipeline data for metadata
    pipeline_data = load_pipeline_json(pipeline_json)

    return {
        "success": True,
        "audiobook_path": str(audiobook_path) if audiobook_path else None,
        "metadata": {
            "file_id": file_id,
            "phases_completed": completed_phases,
            "voice_id": voice_id,
            "tts_engine": tts_engine,
            "mastering_preset": mastering_preset,
            "pipeline_data": pipeline_data.get(file_id, {})
        },
        "error": None
    }


def main():
    """Main orchestrator entry point."""
    parser = argparse.ArgumentParser(
        description="Phase 6: Production Orchestrator for Audiobook Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline for a PDF
  python orchestrator.py input/The_Analects_of_Confucius_20240228.pdf

  # Resume from checkpoint
  python orchestrator.py input/book.pdf --pipeline-json=pipeline.json

  # Run specific phases only
  python orchestrator.py input/book.pdf --phases 3 4 5
        """
    )
    
    parser.add_argument(
        "file",
        type=Path,
        help="Input file path (PDF or ebook)"
    )
    parser.add_argument(
        "--pipeline-json",
        type=Path,
        default=Path("../pipeline.json"),
        help="Path to pipeline.json (default: ../pipeline.json)"
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        type=int,
        default=[1, 2, 3, 4, 5],
        help="Phases to run (default: 1 2 3 4 5)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume from checkpoint (run all phases)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum retry attempts per phase (default: 2)"
    )
    parser.add_argument(
        "--voice",
        type=str,
        help="Voice ID for TTS synthesis (e.g., george_mckayland, landon_elkind). Overrides auto-selection from Phase 3."
    )
    parser.add_argument(
        "--enable-subtitles",
        action="store_true",
        help="Generate .srt and .vtt subtitles after Phase 5 (optional)"
    )

    args = parser.parse_args()

    orchestrator_config = get_orchestrator_config()
    pipeline_mode = orchestrator_config.get("pipeline_mode", "commercial").lower()
    
    # Validate input file (resolve path first)
    file_path = args.file.resolve()
    if not file_path.exists():
        print_status(f"[red]ERROR: File not found: {file_path}[/red]")
        return 1
    file_id = file_path.stem
    
    # Resolve pipeline.json path
    pipeline_json = args.pipeline_json.resolve()
    
    # Display header (use -> instead of → for Windows compatibility)
    phase_display = ' -> '.join(map(str, args.phases))
    header = f"""
Audiobook Pipeline - Phase 6 Orchestrator

Input File:    {file_path.name}
File ID:       {file_id}
Pipeline JSON: {pipeline_json}
Phases:        {phase_display}
Resume:        {'Disabled' if args.no_resume else 'Enabled'}
Max Retries:   {args.max_retries}
Pipeline Mode: {pipeline_mode}
"""
    print_panel(header.strip(), "Configuration", "bold cyan")
    
    # Load pipeline.json
    pipeline_data = load_pipeline_json(pipeline_json) if not args.no_resume else {}
    
    # Run phases
    overall_start = time.perf_counter()
    completed_phases = []
    
    # Log voice configuration if specified
    if args.voice:
        print_status(f"[cyan]Voice Override: {args.voice}[/cyan]")
    
    for phase_num in args.phases:
        phase_name = f"Phase {phase_num}"
        
        # Check resume status
        if not args.no_resume:
            status = check_phase_status(pipeline_data, phase_num, file_id)
            if status == "success":
                print_status(f"[green]OK Skipping {phase_name} (already completed)[/green]")
                completed_phases.append(phase_num)
                continue
            elif status in ["failed", "partial"]:
                print_status(f"[yellow]> Retrying {phase_name} (previous status: {status})[/yellow]")
        
        # Run phase with retries (use > instead of ▶ for Windows compatibility)
        print_status(f"\n[bold cyan]> Running {phase_name}...[/bold cyan]")
        
        success = run_phase_with_retry(
            phase_num,
            file_path,
            file_id,
            pipeline_json,
            max_retries=args.max_retries,
            voice_id=args.voice,
            pipeline_mode=pipeline_mode,
        )
        
        if not success:
            play_sound(success=False)
            print_panel(
                f"Pipeline aborted at {phase_name}\n\n"
                f"Check logs above for details.\n"
                f"Fix issues and re-run with same command to resume.",
                "PIPELINE FAILED",
                "bold red"
            )
            return 1
        
        print_status(f"[green]OK {phase_name} completed successfully[/green]")
        play_sound(success=True)

        if phase_num == 5:
            archive_final_audiobook(file_id, pipeline_json)
        completed_phases.append(phase_num)

    auto_subtitles = orchestrator_config.get("auto_subtitles", False)
    if pipeline_mode == "personal":
        subtitles_enabled = args.enable_subtitles
        if auto_subtitles and not subtitles_enabled:
            logger.info("Personal mode: ignoring auto subtitles. Use --enable-subtitles to run Phase 5.5.")
    else:
        subtitles_enabled = args.enable_subtitles or auto_subtitles

    # Phase 5.5: Generate subtitles (optional)
    if 5 in completed_phases and subtitles_enabled:
        print_status(f"\n[bold cyan]> Running Phase 5.5 (Subtitles)...[/bold cyan]")
        phase5_dir = find_phase_dir(5)
        if phase5_dir:
            success = run_phase5_5_subtitles(
                phase5_dir,
                file_id,
                pipeline_json,
                enable_subtitles=True
            )
            if success:
                print_status(f"[green]OK Phase 5.5 (Subtitles) completed successfully[/green]")
            else:
                print_status(f"[yellow]Warning: Phase 5.5 (Subtitles) failed - continuing anyway[/yellow]")

    # Calculate duration
    duration = time.perf_counter() - overall_start
    
    # Display summary (use -> instead of → for Windows compatibility)
    phases_display = ' -> '.join(map(str, completed_phases))
    summary = f"""
Pipeline completed successfully!

Phases Completed: {phases_display}
Total Duration:   {duration:.1f}s ({duration/60:.1f} minutes)

Output Location:
- Chunks: phase3-chunking/chunks/
- Audio:  phase4_tts/audio_chunks/
- Final:  phase5_enhancement/processed/
- Subtitles: phase5_enhancement/subtitles/ (if enabled)

Next Steps:
1. Review pipeline.json for quality metrics
2. Listen to final audiobook in phase5_enhancement/processed/
3. Check for any warnings in logs above
"""
    print_panel(summary.strip(), "SUCCESS", "bold green")
    
    # Show results table
    summarize_results(pipeline_json)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
