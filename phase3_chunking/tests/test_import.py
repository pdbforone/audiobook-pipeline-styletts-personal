"""Lightweight import smoke test for Phase 3 chunking package."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "phase3-chunking" / "src"
if not PACKAGE_ROOT.exists():
    pytest.skip("phase3-chunking source directory not found", allow_module_level=True)

if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


def test_phase3_package_imports():
    import phase3_chunking  # noqa: F401

    assert True
