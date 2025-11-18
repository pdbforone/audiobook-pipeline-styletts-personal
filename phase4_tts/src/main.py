"""Compatibility shim delegating to the multi-engine Phase 4 entry point.

This module now forwards to the XTTS/Kokoro multi-engine CLI and exists only to
keep older entrypoints working.
"""

from __future__ import annotations

import sys

from . import main_multi_engine


def main() -> int:
    """Entrypoint retained for backwards compatibility."""
    return main_multi_engine.main()


if __name__ == "__main__":
    sys.exit(main())
