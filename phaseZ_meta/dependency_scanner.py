"""Dependency scanner for Phase Z (opt-in, read-only)."""

from __future__ import annotations

import importlib
from typing import Dict, List


def _check_import(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def scan_dependencies() -> Dict[str, object]:
    """
    Report missing/optional/disallowed deps.
    Schema:
    {
      "dependencies_ok": bool,
      "missing": [...],
      "warnings": [...],
      "disallowed": [...]
    }
    """
    required = ["yaml", "pydantic"]
    optional = ["numpy", "librosa", "requests", "nltk"]
    disallowed = []
    missing: List[str] = []
    warnings: List[str] = []

    for dep in required:
        if not _check_import(dep):
            missing.append(dep)
    for dep in optional:
        if not _check_import(dep):
            warnings.append(f"optional_missing:{dep}")

    # Disallow Piper
    if _check_import("piper"):
        disallowed.append("piper")

    dependencies_ok = len(missing) == 0 and len(disallowed) == 0
    return {
        "dependencies_ok": dependencies_ok,
        "missing": missing,
        "warnings": warnings,
        "disallowed": disallowed,
    }
