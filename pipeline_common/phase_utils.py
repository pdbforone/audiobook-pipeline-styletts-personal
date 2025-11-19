"""Convenience helpers for working with pipeline phase blocks."""

from __future__ import annotations

from typing import Any, Dict, Tuple


PhasePayload = Dict[str, Any]


def ensure_phase_block(state: Dict[str, Any], phase_key: str) -> PhasePayload:
    """
    Ensure that ``state[phase_key]`` exists and contains the canonical envelope.

    Returns the phase payload so callers can mutate it in place while building up
    ``status``, ``timestamps``, ``artifacts``, ``metrics`` and ``errors``.
    """
    block = state.setdefault(phase_key, {})
    block.setdefault("status", "pending")
    block.setdefault("timestamps", {})
    block.setdefault("artifacts", [])
    block.setdefault("metrics", {})
    block.setdefault("errors", [])
    return block


def ensure_phase_files(block: PhasePayload) -> Dict[str, PhasePayload]:
    """Return the ``files`` mapping for a phase block, seeding an empty dict."""
    files = block.setdefault("files", {})
    if not isinstance(files, dict):
        files = {}
        block["files"] = files
    return files


def ensure_phase_file_entry(
    block: PhasePayload,
    file_id: str,
) -> PhasePayload:
    """
    Ensure a ``files[file_id]`` entry exists with the canonical envelope.

    Returns the per-file record for convenient mutation.
    """
    files = ensure_phase_files(block)
    entry = files.setdefault(file_id, {})
    entry.setdefault("status", "pending")
    entry.setdefault("timestamps", {})
    entry.setdefault("artifacts", [])
    entry.setdefault("metrics", {})
    entry.setdefault("errors", [])
    return entry


def ensure_phase_and_file(
    state: Dict[str, Any],
    phase_key: str,
    file_id: str,
) -> Tuple[PhasePayload, PhasePayload]:
    """
    Convenience helper returning ``(phase_block, file_entry)``.
    """
    block = ensure_phase_block(state, phase_key)
    file_entry = ensure_phase_file_entry(block, file_id)
    return block, file_entry
