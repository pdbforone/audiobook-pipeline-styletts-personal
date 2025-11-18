#!/usr/bin/env python3
"""
Atomic State Manager for pipeline.json

Provides transaction-based, atomic updates to pipeline state with:
- Atomic writes (write-to-temp-then-rename)
- File locking for concurrent access safety
- Automatic backups with rotation
- Schema validation via Pydantic
- Transaction logging for audit trails
- Rollback on errors

Usage:
    from pipeline_common.state_manager import PipelineState

    state = PipelineState("pipeline.json")

    # Simple read
    data = state.read()

    # Atomic transaction
    with state.transaction() as txn:
        txn.data['phase1']['status'] = 'success'
        # Commits atomically on __exit__, rolls back on exception
"""

import json
import logging
import os
import platform
import shutil
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from copy import deepcopy

# Platform-specific file locking imports
_IS_WINDOWS = platform.system() == 'Windows'
if _IS_WINDOWS:
    import msvcrt
else:
    import fcntl

from .models import PipelineSchema, PYDANTIC_AVAILABLE


logger = logging.getLogger(__name__)


class StateError(Exception):
    """Base exception for state management errors"""
    pass


class StateLockError(StateError):
    """Failed to acquire lock"""
    pass


class StateValidationError(StateError):
    """State validation failed"""
    pass


class StateBackupManager:
    """Manages automatic backups with rotation"""

    def __init__(self, state_path: Path, max_backups: int = 50):
        self.state_path = state_path
        self.backup_dir = state_path.parent / ".pipeline" / "backups"
        self.max_backups = max_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Optional[Path]:
        """
        Create timestamped backup of current state.

        Returns:
            Path to backup file, or None if state doesn't exist yet
        """
        if not self.state_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"{self.state_path.stem}_{timestamp}.json.bak"
        backup_path = self.backup_dir / backup_name

        try:
            shutil.copy2(self.state_path, backup_path)
            logger.debug(f"Created backup: {backup_path.name}")
            return backup_path
        except Exception as e:
            logger.warning(f"Backup failed: {e}")
            return None

    def rotate_backups(self):
        """Remove old backups, keeping only max_backups most recent"""
        try:
            backups = sorted(
                self.backup_dir.glob(f"{self.state_path.stem}_*.json.bak"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for old_backup in backups[self.max_backups:]:
                old_backup.unlink()
                logger.debug(f"Rotated old backup: {old_backup.name}")
        except Exception as e:
            logger.warning(f"Backup rotation failed: {e}")

    def list_backups(self, limit: int = 10) -> list[Path]:
        """List most recent backups"""
        return sorted(
            self.backup_dir.glob(f"{self.state_path.stem}_*.json.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]

    def restore_backup(self, backup_path: Path) -> bool:
        """
        Restore state from a backup.

        Returns:
            True if successful
        """
        try:
            shutil.copy2(backup_path, self.state_path)
            logger.info(f"Restored backup: {backup_path.name}")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False


class StateTransactionLog:
    """Append-only transaction log for audit trail"""

    def __init__(self, state_path: Path):
        self.log_path = state_path.parent / ".pipeline" / "transactions.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_transaction(self, operation: str, success: bool, details: Optional[Dict] = None):
        """
        Append transaction record to log.

        Args:
            operation: "read", "write", "commit", "rollback"
            success: Whether operation succeeded
            details: Optional metadata (error message, changed keys, etc.)
        """
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "success": success,
                "pid": os.getpid(),
                "details": details or {}
            }

            with open(self.log_path, 'a') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.warning(f"Transaction log write failed: {e}")


class StateTransaction:
    """
    Context manager for atomic state transactions.

    Provides transactional semantics:
    - Changes staged in memory
    - Validated before commit
    - Atomic write on success
    - Automatic rollback on exception
    """

    def __init__(self, state: 'PipelineState'):
        self.state = state
        self.data: Dict[str, Any] = {}
        self.original_data: Dict[str, Any] = {}
        self.committed = False
        self._lock_cm = None

    def __enter__(self) -> 'StateTransaction':
        """Begin transaction - load current state"""
        # Acquire exclusive lock for entire transaction to guarantee isolation
        self._lock_cm = self.state._file_lock()
        self._lock_cm.__enter__()
        try:
            self.original_data = self.state.read()
            self.data = deepcopy(self.original_data)
            logger.debug("Transaction started")
            return self
        except Exception:
            # If read fails, release lock before propagating error
            if self._lock_cm is not None:
                self._lock_cm.__exit__(*sys.exc_info())
                self._lock_cm = None
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End transaction - commit or rollback"""
        if exc_type is not None:
            # Exception occurred - rollback
            logger.warning(f"Transaction rollback due to {exc_type.__name__}: {exc_val}")
            self.state.transaction_log.log_transaction(
                "rollback",
                success=True,
                details={"reason": str(exc_val)}
            )
            self._release_lock()
            return False  # Re-raise exception

        # No exception - commit
        try:
            self.state._write_atomic(self.data, validate=True)
            self.committed = True
            self.state.transaction_log.log_transaction(
                "commit",
                success=True,
                details={"changed_keys": self._get_changed_keys()}
            )
            logger.debug("Transaction committed")
        except Exception as e:
            logger.error(f"Transaction commit failed: {e}")
            self.state.transaction_log.log_transaction(
                "commit",
                success=False,
                details={"error": str(e)}
            )
            self._release_lock()
            raise

        self._release_lock()
        return True

    def _get_changed_keys(self) -> list[str]:
        """Identify which top-level keys changed"""
        changed = []
        for key in set(self.data.keys()) | set(self.original_data.keys()):
            if self.data.get(key) != self.original_data.get(key):
                changed.append(key)
        return changed

    def _release_lock(self):
        """Release transaction lock if held"""
        if self._lock_cm is not None:
            try:
                self._lock_cm.__exit__(None, None, None)
            finally:
                self._lock_cm = None


class PipelineState:
    """
    Thread-safe, atomic state manager for pipeline.json.

    Features:
    - Atomic writes via temp file + rename
    - File locking for concurrent access
    - Automatic backups with rotation
    - Schema validation
    - Transaction support with rollback
    - Audit logging

    Example:
        state = PipelineState("pipeline.json")

        with state.transaction() as txn:
            txn.data['phase1']['status'] = 'success'
    """

    def __init__(
        self,
        path: str | Path,
        validate_on_read: bool = False,
        max_backups: int = 50,
        backup_before_write: bool = True
    ):
        """
        Initialize state manager.

        Args:
            path: Path to pipeline.json
            validate_on_read: Whether to validate schema on every read
            max_backups: Maximum number of backups to keep
            backup_before_write: Whether to backup before every write
        """
        self.path = Path(path).resolve()
        self.lock_path = self.path.with_suffix('.json.lock')
        self.validate_on_read = validate_on_read
        self.backup_before_write = backup_before_write

        self.backup_manager = StateBackupManager(self.path, max_backups)
        self.transaction_log = StateTransactionLog(self.path)

        logger.debug(f"StateManager initialized: {self.path}")

    def _acquire_lock(self, lock_file):
        """
        Platform-specific lock acquisition.

        Args:
            lock_file: Open file handle to lock

        Raises:
            BlockingIOError/OSError: If lock cannot be acquired immediately
        """
        if _IS_WINDOWS:
            # Windows: Use msvcrt.locking()
            # Lock 1 byte at the beginning of the file
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            # Unix: Use fcntl.flock()
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _release_lock(self, lock_file):
        """
        Platform-specific lock release.

        Args:
            lock_file: Open file handle to unlock
        """
        try:
            if _IS_WINDOWS:
                # Windows: Unlock the byte
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                # Unix: Unlock with fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.warning(f"Lock release failed: {e}")

    @contextmanager
    def _file_lock(self, timeout: float = 10.0):
        """
        Acquire exclusive file lock (cross-platform).

        Works on both Windows (msvcrt) and Unix (fcntl).

        Args:
            timeout: Maximum seconds to wait for lock

        Raises:
            StateLockError: If lock cannot be acquired
        """
        lock_file = None
        try:
            # Open lock file for writing
            lock_file = open(self.lock_path, 'w')
            start_time = time.time()

            # Try to acquire lock with timeout
            while True:
                try:
                    self._acquire_lock(lock_file)
                    logger.debug("Lock acquired")
                    break
                except (BlockingIOError, OSError) as e:
                    # Both platforms raise exceptions when lock unavailable
                    if time.time() - start_time > timeout:
                        raise StateLockError(
                            f"Could not acquire lock after {timeout}s. "
                            f"Another process may be writing to {self.path}"
                        )
                    time.sleep(0.1)

            yield
        finally:
            if lock_file:
                self._release_lock(lock_file)
                lock_file.close()
                logger.debug("Lock released")

    def read(self, validate: bool = None) -> Dict[str, Any]:
        """
        Read current state.

        Args:
            validate: Override validate_on_read setting

        Returns:
            State dictionary (empty dict if file doesn't exist)

        Raises:
            StateValidationError: If validation fails
        """
        if validate is None:
            validate = self.validate_on_read

        if not self.path.exists():
            logger.debug("State file doesn't exist, returning empty state")
            self.transaction_log.log_transaction("read", success=True,
                                                 details={"note": "file_not_found"})
            return {}

        try:
            with open(self.path, 'r') as f:
                data = json.load(f)

            if validate:
                self._validate(data)

            self.transaction_log.log_transaction("read", success=True)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted state file: {e}")
            self.transaction_log.log_transaction("read", success=False,
                                                 details={"error": "json_decode_error"})
            raise StateError(f"Corrupted state file: {e}")
        except Exception as e:
            logger.error(f"Read failed: {e}")
            self.transaction_log.log_transaction("read", success=False,
                                                 details={"error": str(e)})
            raise

    def write(self, data: Dict[str, Any], validate: bool = True):
        """
        Write state atomically.

        Args:
            data: New state dictionary
            validate: Whether to validate before writing

        Raises:
            StateValidationError: If validation fails
        """
        with self._file_lock():
            self._write_atomic(data, validate=validate)

    def _write_atomic(self, data: Dict[str, Any], validate: bool = True):
        """
        Internal atomic write with backup.

        Strategy:
        1. Validate data (if requested)
        2. Create backup of current state
        3. Write to temporary file
        4. Atomic rename temp → actual
        5. Rotate old backups
        """
        # Validate
        if validate:
            self._validate(data)

        # Backup current state
        if self.backup_before_write:
            self.backup_manager.create_backup()

        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Write to unique temp file in same directory (required for atomic rename)
        # Use PID and timestamp to ensure uniqueness
        temp_suffix = f".{os.getpid()}_{time.time()}.tmp"
        temp_path = self.path.with_suffix(temp_suffix)
        try:
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is on disk

            # Atomic rename (only atomic if on same filesystem)
            os.replace(str(temp_path), str(self.path))

            self.transaction_log.log_transaction("write", success=True)
            logger.debug(f"Atomic write completed")
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            logger.error(f"Atomic write failed: {e}")
            self.transaction_log.log_transaction("write", success=False,
                                                 details={"error": str(e)})
            raise
        finally:
            # Rotate backups
            if self.backup_before_write:
                self.backup_manager.rotate_backups()

    def _validate(self, data: Dict[str, Any]):
        """
        Validate data against schema.

        Args:
            data: State dictionary to validate

        Raises:
            StateValidationError: If validation fails
        """
        if not PYDANTIC_AVAILABLE:
            logger.warning("Pydantic not available - skipping validation")
            return

        try:
            PipelineSchema(**data)
        except Exception as e:
            raise StateValidationError(f"Schema validation failed: {e}")

    def transaction(self) -> StateTransaction:
        """
        Create atomic transaction context manager.

        Returns:
            StateTransaction context manager

        Example:
            with state.transaction() as txn:
                txn.data['phase1']['status'] = 'success'
                # Commits on __exit__, rolls back on exception
        """
        return StateTransaction(self)

    def list_backups(self, limit: int = 10) -> list[Path]:
        """List recent backups"""
        return self.backup_manager.list_backups(limit)

    def restore_backup(self, backup_path: Path | str) -> bool:
        """Restore from backup"""
        return self.backup_manager.restore_backup(Path(backup_path))

    def get_transaction_history(self, limit: int = 50) -> list[Dict]:
        """
        Read recent transaction history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of transaction records (most recent first)
        """
        try:
            with open(self.transaction_log.log_path, 'r') as f:
                lines = f.readlines()

            records = []
            for line in reversed(lines[-limit:]):
                try:
                    records.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

            return records
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.warning(f"Failed to read transaction history: {e}")
            return []
