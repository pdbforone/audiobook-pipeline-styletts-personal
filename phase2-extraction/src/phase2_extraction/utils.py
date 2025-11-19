"""
Utilities for Phase 2 Extraction

Provides:
- Thread-safe pipeline.json updates
- File type detection
- Retry logic for transient errors
- Helper functions
"""

from __future__ import annotations

import json
import logging
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml
try:
    from pipeline_common import canonicalize_state, validate_pipeline_schema
except Exception:  # pragma: no cover - defensive fallback when pipeline_common not installed
    canonicalize_state = lambda data, **kwargs: data  # type: ignore

    def validate_pipeline_schema(data, **kwargs):  # type: ignore
        return None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {"use_nemo": False}
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load Phase 2 configuration from YAML with sane defaults.

    Args:
        config_path: Optional explicit path to a YAML config file.

    Returns:
        Dict of configuration values with defaults applied.
    """
    config: Dict[str, Any] = DEFAULT_CONFIG.copy()
    path = config_path or DEFAULT_CONFIG_PATH

    if path and path.exists():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                config.update(loaded)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to read config from {path}: {exc}")
    else:
        logger.debug(f"No config file found at {path}, using defaults.")

    return config


def safe_update_json(pipeline_path: Path, phase_name: str, data: Dict[str, Any]) -> None:
    """
    Thread-safe pipeline.json updates with platform-aware locking.
    
    Args:
        pipeline_path: Path to pipeline.json
        phase_name: Phase key to update (e.g., 'phase2')
        data: Data to merge into phase
        
    Prevents race conditions and JSON corruption when multiple processes
    access pipeline.json simultaneously.
    
    Reason: File locking ensures that concurrent reads/writes don't
    corrupt the JSON file. Platform-specific locking handles Windows
    vs Unix differences.
    """
    max_attempts = 5
    delay = 0.5
    
    for attempt in range(max_attempts):
        try:
            with pipeline_path.open('r+', encoding='utf-8') as f:
                # Platform-aware file locking
                if platform.system() == 'Windows':
                    import msvcrt
                    try:
                        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                    except IOError as e:
                        if attempt < max_attempts - 1:
                            logger.debug(f"Lock attempt {attempt+1} failed, retrying...")
                            time.sleep(delay)
                            continue
                        raise
                else:
                    import fcntl
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except IOError as e:
                        if attempt < max_attempts - 1:
                            logger.debug(f"Lock attempt {attempt+1} failed, retrying...")
                            time.sleep(delay)
                            continue
                        raise
                
                try:
                    # Read current content
                    current = json.load(f)
                    
                    # Ensure phase exists
                    if phase_name not in current:
                        current[phase_name] = {}
                    
                    # Deep merge: update nested dicts properly
                    def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
                        """Recursively merge update into base."""
                        for key, value in update.items():
                            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                                base[key] = deep_merge(base[key], value)
                            else:
                                base[key] = value
                        return base
                    
                    current[phase_name] = deep_merge(current[phase_name], data)

                    try:
                        current = canonicalize_state(current)
                        validate_pipeline_schema(current)
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning("Pipeline schema enforcement skipped: %s", exc)
                    
                    # Write back
                    f.seek(0)
                    json.dump(current, f, indent=2, ensure_ascii=False)
                    f.truncate()
                    
                    logger.debug(f"Successfully updated {phase_name} in pipeline.json")
                    
                finally:
                    # Unlock
                    if platform.system() == 'Windows':
                        try:
                            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                        except:
                            pass
                    else:
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        except:
                            pass
                
                return  # Success!
                
        except (IOError, OSError) as e:  # pragma: no cover - depends on platform locks
            if attempt < max_attempts - 1:
                logger.warning(f"Pipeline update attempt {attempt+1} failed: {e}, retrying...")
                time.sleep(delay)
            else:
                logger.error(f"Failed to update pipeline.json after {max_attempts} attempts")
                raise


def with_retry(func: Callable[[], Any], max_attempts: int = 3, delay: float = 1.0) -> Any:
    """
    Retry function on transient errors.
    
    Args:
        func: Function to retry (should take no arguments)
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        
    Returns:
        Result of successful function call
        
    Raises:
        Last exception if all attempts fail
        
    Reason: Handles transient errors like file locks, network issues,
    temporary permission problems. Exponential backoff gives system
    time to recover.
    """
    for attempt in range(max_attempts):
        try:
            return func()
        except (IOError, OSError, PermissionError) as e:
            if attempt == max_attempts - 1:
                logger.error(f"Failed after {max_attempts} attempts: {e}")
                raise
            
            wait_time = delay * (2 ** attempt)  # Exponential backoff
            logger.warning(f"Attempt {attempt+1} failed: {e}, retrying in {wait_time}s...")
            time.sleep(wait_time)


def detect_format(path: Path) -> str:
    """
    Detect file format using extension and MIME type.
    
    Args:
        path: Path to file
        
    Returns:
        Format string: 'pdf', 'docx', 'epub', 'html', 'txt'
        
    Strategy:
    1. Check file extension
    2. Validate with MIME type if python-magic available
    3. Fall back to extension only if MIME fails
    
    Reason: Combining extension and MIME detection prevents
    misidentification from renamed files or missing extensions.
    """
    ext = path.suffix.lower()
    
    # Try MIME detection if available
    if MAGIC_AVAILABLE:
        try:
            mime = magic.from_file(str(path), mime=True)
            logger.debug(f"MIME type detected: {mime}")
            
            # MIME-based detection (more reliable)
            if 'pdf' in mime:
                return 'pdf'
            elif 'word' in mime or 'officedocument' in mime:
                return 'docx'
            elif 'epub' in mime:
                return 'epub'
            elif 'html' in mime:
                return 'html'
            elif 'text' in mime or 'plain' in mime:
                return 'txt'
                
        except Exception as e:
            logger.debug(f"MIME detection failed: {e}, falling back to extension")
    
    # Extension-based detection (fallback)
    if ext == '.pdf':
        return 'pdf'
    elif ext in ('.docx', '.doc'):
        return 'docx'
    elif ext == '.epub':
        return 'epub'
    elif ext in ('.html', '.htm'):
        return 'html'
    elif ext in ('.txt', '.md', '.text'):
        return 'txt'
    
    # Default to txt with warning
    logger.warning(
        f"Ambiguous format for {path.name} (ext={ext}) - "
        f"defaulting to 'txt'. Consider using a standard extension."
    )
    return 'txt'


def calculate_yield(original_size: int, extracted_length: int) -> float:
    """
    Calculate text yield percentage.
    
    Args:
        original_size: Original file size in bytes
        extracted_length: Length of extracted text in characters
        
    Returns:
        Yield as a float between 0.0 and 1.0+
        
    Reason: Yield helps detect extraction problems. Very low yield
    suggests OCR needed or extraction failure. Very high yield may
    indicate duplicate content or extraction artifacts.
    """
    if original_size == 0:
        return 0.0
    
    # Rough approximation: 1 char ≈ 1 byte for text content
    # This is imperfect but useful for detecting major issues
    yield_pct = extracted_length / original_size
    
    if yield_pct < 0.5:
        logger.warning(
            f"Low text yield ({yield_pct:.1%}) - "
            f"file may be scanned or extraction may have failed"
        )
    elif yield_pct > 2.0:
        logger.warning(
            f"High text yield ({yield_pct:.1%}) - "
            f"extracted text may contain duplicates or artifacts"
        )
    
    return yield_pct


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def log_error(
    pipeline_path: Path,
    phase_name: str,
    file_id: str,
    message: str,
    severity: str = "blocking",
) -> None:
    """
    Log an error to pipeline.json in standardized format.
    
    Args:
        pipeline_path: Path to pipeline.json
        phase_name: Phase where error occurred
        file_id: File identifier related to the error
        message: Human-readable message
        severity: 'blocking' or 'warning'
        
    Reason: Standardized error format makes debugging easier and
    ensures users get actionable fix instructions.
    """
    error_entry = {
        "file_id": file_id,
        "message": message,
        "phase": phase_name,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    try:
        with pipeline_path.open('r+', encoding='utf-8') as f:
            data = json.load(f)
            
            if phase_name not in data:
                data[phase_name] = {}
            if 'errors' not in data[phase_name]:
                data[phase_name]['errors'] = []
            
            data[phase_name]['errors'].append(error_entry)
            
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()
        
        logger.error(f"[{phase_name}:{file_id}] {message}")
        
    except Exception as e:
        logger.error(f"Failed to log error to pipeline.json: {e}")
        logger.error(f"Original error: [{phase_name}:{file_id}] {message}")
