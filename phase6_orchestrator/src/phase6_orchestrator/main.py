"""Phase 6: Single-File Orchestrator entrypoint.

This thin wrapper imports the production orchestrator module that lives at
phase6_orchestrator/orchestrator.py while keeping the existing CLI entrypoint.
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phase6_orchestrator import orchestrator  # noqa: E402


def main() -> int:
    return orchestrator.main()


if __name__ == "__main__":
    raise SystemExit(main())
