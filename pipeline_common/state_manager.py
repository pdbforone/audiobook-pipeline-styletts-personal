#!/usr/bin/env python3
"""Atomic, typed state manager for pipeline.json.

This module provides a single source of truth for reading and writing
``pipeline.json`` with the following guarantees:

- Atomic writes using a temp file + ``os.replace`` on the same filesystem.
- Best-effort file locking to coordinate concurrent writers.
- Automatic backups with rotation and simple restore helpers.
- Minimal structural validation on reads to catch corruption early.
- Optional strict validation via Pydantic when available.
- Transactional updates through ``PipelineState.transaction()``.

Public surface (kept stable for existing consumers):
    - PipelineState
    - StateError (and derived exceptions)
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

_IS_WINDOWS = platform.system() == "Windows"
if _IS_WINDOWS:
    import msvcrt
else:  # pragma: no cover - platform specific
    import fcntl

from .models import PYDANTIC_AVAILABLE, PipelineSchema

logger = logging.getLogger(__name__)

# Type aliases
JsonDict = Dict[str, Any]
TransactionRecord = Dict[str, Any]

# Known phase keys for summaries
_PHASE_KEYS: tuple[str, ...] = (
    "phase1",
    "phase2",
    "phase3",
    "phase4",
    "phase5",
    "phase5_5",
    "phase6",
    "phase7",
)

# Default sections expected in a valid pipeline.json
DEFAULT_REQUIRED_SECTIONS: tuple[str, ...] = (
    "phases",
    "chunks",
    *(_PHASE_KEYS),
)


class StateError(Exception):
    """Base exception for state management errors."""


class StateLockError(StateError):
    """Raised when lock acquisition times out."""


class StateValidationError(StateError):
    """Raised when validation fails."""


class StateBackupManager:
    """Manage automatic backups with rotation."""

    def __init__(self, state_path: Path, max_backups: int = 50) -> None:
        self.state_path = state_path
        self.backup_dir = state_path.parent / ".pipeline" / "backups"
        self.max_backups = max_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Optional[Path]:
        """Create a timestamped backup of the current state file."""
        if not self.state_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"{self.state_path.stem}_{timestamp}.json.bak"
        backup_path = self.backup_dir / backup_name

        try:
            shutil.copy2(self.state_path, backup_path)
            logger.debug("Created backup: %s", backup_path.name)
            return backup_path
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Backup failed: %s", exc)
            return None

    def rotate_backups(self) -> None:
        """Remove old backups, keeping the most recent ones."""
        try:
            backups = sorted(
                self.backup_dir.glob(f"{self.state_path.stem}_*.json.bak"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old_backup in backups[self.max_backups :]:
                old_backup.unlink(missing_ok=True)
                logger.debug("Rotated old backup: %s", old_backup.name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Backup rotation failed: %s", exc)

    def list_backups(self, limit: int = 10) -> List[Path]:
        """Return the most recent backups."""
        backups = sorted(
            self.backup_dir.glob(f"{self.state_path.stem}_*.json.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return backups[:limit]

    def restore_backup(self, backup_path: Path) -> bool:
        """Restore state from a backup file."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, self.state_path)
            logger.info("Restored backup: %s", backup_path.name)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Restore failed: %s", exc)
            return False


class StateTransactionLog:
    """Append-only transaction log for auditability."""

    def __init__(self, state_path: Path) -> None:
        self.log_path = state_path.parent / ".pipeline" / "transactions.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_transaction(
        self,
        operation: str,
        success: bool,
        details: Optional[TransactionRecord] = None,
    ) -> None:
        record: TransactionRecord = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "success": success,
            "pid": os.getpid(),
            "details": details or {},
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(record) + "\n")
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Transaction log write failed: %s", exc)


class PipelineState:
    """Atomic, validated manager for ``pipeline.json``."""

    def __init__(
        self,
        path: str | Path,
        validate_on_read: bool = False,
        max_backups: int = 50,
        backup_before_write: bool = True,
        required_sections: Optional[Iterable[str]] = None,
        structural_validation: bool = True,
    ) -> None:
        """
        Args:
            path: Path to the pipeline.json file.
            validate_on_read: Whether to run Pydantic validation on read.
            max_backups: Maximum number of backups to retain.
            backup_before_write: Whether to create a backup before writes.
            required_sections: Top-level keys that must be present when data is not empty.
            structural_validation: Enforce minimal structural validation on reads/writes.
        """
        self.path = Path(path).resolve()
        self.lock_path = self.path.with_suffix(f"{self.path.suffix}.lock")
        self.validate_on_read = validate_on_read
        self.structural_validation = structural_validation
        self.backup_before_write = backup_before_write
        self.required_sections: tuple[str, ...] = tuple(required_sections or DEFAULT_REQUIRED_SECTIONS)

        self.backup_manager = StateBackupManager(self.path, max_backups=max_backups)
        self.transaction_log = StateTransactionLog(self.path)

        logger.debug("PipelineState initialized for %s", self.path)

    # ------------------------------------------------------------------ #
    # Locking helpers
    # ------------------------------------------------------------------ #
    def _acquire_lock(self, lock_file) -> None:
        if _IS_WINDOWS:
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:  # pragma: no cover - platform specific
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _release_lock(self, lock_file) -> None:
        try:
            if _IS_WINDOWS:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - platform specific
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Lock release failed: %s", exc)

    @contextmanager
    def _file_lock(self, timeout: float = 10.0) -> Iterator[None]:
        """Acquire an exclusive lock on the lock file."""
        lock_file = None
        try:
            lock_file = open(self.lock_path, "w")
            start_time = time.time()
            while True:
                try:
                    self._acquire_lock(lock_file)
                    logger.debug("Lock acquired for %s", self.path)
                    break
                except (BlockingIOError, OSError):
                    if time.time() - start_time > timeout:
                        raise StateLockError(
                            f"Could not acquire lock for {self.path} after {timeout}s."
                        )
                    time.sleep(0.1)
            yield
        finally:
            if lock_file:
                self._release_lock(lock_file)
                lock_file.close()
                logger.debug("Lock released for %s", self.path)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def read(self, validate: Optional[bool] = None) -> JsonDict:
        """Read current state from disk."""
        run_validation = self.validate_on_read if validate is None else validate

        if not self.path.exists():
            self._log_transaction("read", True, {"note": "file_not_found"})
            return {}

        try:
            with open(self.path, "r", encoding="utf-8") as state_file:
                data = json.load(state_file)

            self._validate_basic(data)
            if run_validation:
                self._validate_schema(data)

            self._log_transaction("read", True)
            return data
        except json.JSONDecodeError as exc:
            self._log_transaction("read", False, {"error": "json_decode_error"})
            raise StateError(f"Corrupted state file: {exc}") from exc
        except StateValidationError:
            self._log_transaction("read", False, {"error": "validation_error"})
            raise
        except Exception as exc:
            self._log_transaction("read", False, {"error": str(exc)})
            raise

    def write(self, data: JsonDict, validate: bool = True) -> None:
        """Write the provided state to disk atomically."""
        with self._file_lock():
            self._write_atomic(data, validate=validate)

    def transaction(self) -> StateTransaction:
        """Create a transaction context manager."""
        return StateTransaction(self)

    def list_backups(self, limit: int = 10) -> List[Path]:
        """Return recent backup files."""
        return self.backup_manager.list_backups(limit)

    def restore_backup(self, backup_path: Path | str) -> bool:
        """Restore state from the given backup file."""
        return self.backup_manager.restore_backup(Path(backup_path))

    def get_transaction_history(self, limit: int = 50) -> List[TransactionRecord]:
        """Return recent transaction records (most recent first)."""
        try:
            with open(self.transaction_log.log_path, "r", encoding="utf-8") as log_file:
                lines = log_file.readlines()

            records: List[TransactionRecord] = []
            for line in reversed(lines[-limit:]):
                try:
                    records.append(json.loads(line.strip()))
                except json.JSONDecodeError:  # pragma: no cover - defensive
                    continue
            return records
        except FileNotFoundError:
            return []
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to read transaction history: %s", exc)
            return []

    # ------------------------------------------------------------------ #
    # UI-friendly helpers (read-only)
    # ------------------------------------------------------------------ #
    def get_status_summary(self) -> JsonDict:
        """Return a lightweight summary of known phase statuses."""
        data = self.read(validate=False)
        summary: JsonDict = {
            "file_id": data.get("file_id"),
            "pipeline_version": data.get("pipeline_version"),
            "phases": {},
            "failed": [],
            "completed": [],
            "in_progress": [],
            "has_errors": False,
        }

        for phase_key in _PHASE_KEYS:
            phase_data = data.get(phase_key)
            status = "missing"
            if isinstance(phase_data, dict):
                status = phase_data.get("status", "unknown")
            elif phase_data is not None:
                status = "invalid"

            summary["phases"][phase_key] = status
            if status == "failed":
                summary["failed"].append(phase_key)
            elif status in ("running", "pending", "partial"):
                summary["in_progress"].append(phase_key)
            elif status == "success":
                summary["completed"].append(phase_key)

        summary["has_errors"] = bool(summary["failed"])
        summary["total_known_phases"] = len(_PHASE_KEYS)
        return summary

    def get_phase_data(self, phase_name: str) -> Optional[JsonDict]:
        """Return a defensive copy of a phase block if present."""
        data = self.read(validate=False)
        phase = data.get(phase_name)
        if isinstance(phase, dict):
            return deepcopy(phase)
        return None

    def get_chunks(self, phase_name: str = "phase3") -> List[JsonDict]:
        """Return the chunk list for a given phase (commonly phase3 or phase5)."""
        phase = self.get_phase_data(phase_name)
        if not phase:
            return []

        chunks = phase.get("chunks")
        if isinstance(chunks, list):
            return deepcopy(chunks)
        if isinstance(chunks, dict):
            # Some pipelines store chunks keyed by id
            return [deepcopy(chunk) for chunk in chunks.values() if isinstance(chunk, dict)]
        return []

    def get_chunk_metadata(
        self,
        chunk_id: Any,
        phase_name: str = "phase3",
    ) -> Optional[JsonDict]:
        """Return metadata for a specific chunk id if present."""
        phase_chunks = self.get_chunks(phase_name)
        for chunk in phase_chunks:
            if chunk.get("id") == chunk_id or chunk.get("chunk_id") == chunk_id:
                return deepcopy(chunk)
        return None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _log_transaction(
        self, operation: str, success: bool, details: Optional[TransactionRecord] = None
    ) -> None:
        if self.transaction_log:
            self.transaction_log.log_transaction(operation, success, details=details)

    def _validate_basic(self, data: JsonDict, *, enforce_sections: Optional[bool] = None) -> None:
        """Lightweight structural validation that does not require Pydantic."""
        if not isinstance(data, dict):
            raise StateValidationError("State file must contain a JSON object at the top level.")

        enforce_sections = self.structural_validation if enforce_sections is None else enforce_sections

        if enforce_sections and data:
            has_required_section = any(section in data for section in self.required_sections)
            metadata_keys = {"file_id", "pipeline_version", "input_file", "version"}
            has_phase_like_key = any(key.startswith("phase") for key in data)
            if (
                not has_required_section
                and not any(key in data for key in metadata_keys)
                and has_phase_like_key
            ):
                expected = "', '".join(self.required_sections[:4])
                raise StateValidationError(
                    f"State missing expected top-level sections (e.g., '{expected}')."
                )

        if self.structural_validation:
            for phase_key in _PHASE_KEYS:
                if (
                    phase_key in data
                    and data[phase_key] is not None
                    and not isinstance(data[phase_key], dict)
                ):
                    raise StateValidationError(f"Phase '{phase_key}' must be an object if present.")

        if "chunks" in data and data["chunks"] is not None:
            if not isinstance(data["chunks"], (list, dict)):
                raise StateValidationError("Top-level 'chunks' must be a list or object.")

    def _validate_schema(self, data: JsonDict) -> None:
        """Optional Pydantic validation."""
        self._validate_basic(data)
        if not PYDANTIC_AVAILABLE:
            logger.debug("Pydantic not available - skipping strict validation.")
            return

        try:
            PipelineSchema(**data)
        except Exception as exc:
            raise StateValidationError(f"Schema validation failed: {exc}") from exc

    def _write_atomic(self, data: JsonDict, validate: bool = True) -> None:
        """Perform an atomic write with optional validation and backups."""
        if validate:
            self._validate_schema(data)
        else:
            self._validate_basic(data, enforce_sections=False)

        if self.backup_before_write:
            self.backup_manager.create_backup()

        self.path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time() * 1000)
        temp_path = self.path.parent / f"{self.path.name}.{os.getpid()}_{timestamp}.tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temp_path, self.path)
            self._log_transaction("write", True)
            logger.debug("Atomic write completed for %s", self.path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            self._log_transaction("write", False, {"error": "atomic_write_failed"})
            raise
        finally:
            if self.backup_before_write:
                self.backup_manager.rotate_backups()


class StateTransaction:
    """Context manager for transactional updates."""

    def __init__(self, state: PipelineState) -> None:
        self.state = state
        self.data: JsonDict = {}
        self.original_data: JsonDict = {}
        self.committed: bool = False
        self._lock_cm = None

    def __enter__(self) -> "StateTransaction":
        self._lock_cm = self.state._file_lock()
        self._lock_cm.__enter__()
        try:
            self.original_data = self.state.read(validate=self.state.validate_on_read)
            self.data = deepcopy(self.original_data)
            return self
        except Exception:
            self._release_lock()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        try:
            if exc_type is not None:
                self.state._log_transaction(
                    "rollback", True, {"reason": str(exc_val) if exc_val else repr(exc_type)}
                )
                return False

            self.state._write_atomic(self.data, validate=True)
            self.committed = True
            self.state._log_transaction("commit", True, {"changed_keys": self._get_changed_keys()})
            return False
        except Exception as exc:
            self.state._log_transaction("commit", False, {"error": str(exc)})
            raise
        finally:
            self._release_lock()

    def _get_changed_keys(self) -> List[str]:
        changed: List[str] = []
        for key in set(self.data.keys()) | set(self.original_data.keys()):
            if self.data.get(key) != self.original_data.get(key):
                changed.append(key)
        return changed

    def _release_lock(self) -> None:
        if self._lock_cm is not None:
            try:
                self._lock_cm.__exit__(None, None, None)
            finally:
                self._lock_cm = None
