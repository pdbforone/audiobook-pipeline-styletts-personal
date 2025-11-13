"""Compatibility shim delegating to the multi-engine Phase 4 entry point.

Historically this module provided a Chatterbox-specific pipeline. The project
now exclusively uses the multi-engine implementation in ``main_multi_engine``,
so this module simply forwards to that CLI to preserve existing scripts that
import or execute ``main.py``.
"""

from __future__ import annotations

import sys

from . import main_multi_engine


def main() -> int:
    """Entrypoint retained for backwards compatibility."""
    return main_multi_engine.main()


if __name__ == "__main__":
    sys.exit(main())
