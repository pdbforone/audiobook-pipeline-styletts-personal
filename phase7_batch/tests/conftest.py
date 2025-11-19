"""Test configuration for Phase 7 ensuring shared modules are resolvable."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_on_sys_path() -> None:
    """Insert the repository root at the beginning of sys.path."""
    repo_root = Path(__file__).resolve().parents[2]
    repo_str = str(repo_root)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


_ensure_repo_on_sys_path()
