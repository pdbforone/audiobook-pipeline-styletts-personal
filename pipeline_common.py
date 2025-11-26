"""
Shared constants and utilities for the audiobook pipeline.

This module provides common definitions used across the UI and orchestrator.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Canonical list of phase keys in execution order
PHASE_KEYS: List[str] = [
    "phase1",
    "phase2",
    "phase3",
    "phase4",
    "phase5",
    "phase5_5",
]


class StateError(Exception):
    """Raised when pipeline state operations fail."""
    pass


class PipelineState:
    """
    Thread-safe wrapper around pipeline.json state file.

    Provides read/write access to the pipeline JSON with optional validation.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """Return the path to the pipeline.json file."""
        return self._path

    def read(self, validate: bool = True) -> Dict[str, Any]:
        """
        Read and return the pipeline state.

        Args:
            validate: If True, raise StateError on missing/invalid file.
                     If False, return empty dict on errors.

        Returns:
            The parsed pipeline.json contents.

        Raises:
            StateError: If validate=True and the file is missing or invalid.
        """
        if not self._path.exists():
            if validate:
                raise StateError(f"Pipeline state file not found: {self._path}")
            return {}

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            if validate:
                raise StateError(f"Invalid JSON in pipeline state: {e}")
            logger.warning("Failed to parse pipeline.json: %s", e)
            return {}
        except Exception as e:
            if validate:
                raise StateError(f"Failed to read pipeline state: {e}")
            logger.warning("Error reading pipeline.json: %s", e)
            return {}

    def write(self, data: Dict[str, Any], validate: bool = True) -> None:
        """
        Write data to the pipeline state file.

        Args:
            data: The dictionary to write as JSON.
            validate: If True, raise StateError on write failures.

        Raises:
            StateError: If validate=True and the write fails.
        """
        try:
            # Ensure parent directory exists
            self._path.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically via temp file
            temp_path = self._path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_path.replace(self._path)

        except Exception as e:
            if validate:
                raise StateError(f"Failed to write pipeline state: {e}")
            logger.error("Error writing pipeline.json: %s", e)

    def get_phase_status(self, phase_key: str, file_id: Optional[str] = None) -> str:
        """
        Get the status of a specific phase.

        Args:
            phase_key: The phase key (e.g., "phase1", "phase4").
            file_id: Optional file ID for file-specific status.

        Returns:
            Status string or "pending" if not found.
        """
        data = self.read(validate=False)
        phase_data = data.get(phase_key, {})

        if file_id:
            files = phase_data.get("files", {})
            file_info = files.get(file_id, {})
            return file_info.get("status", "pending")

        return phase_data.get("status", "pending")
