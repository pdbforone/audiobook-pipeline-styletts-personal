"""
Patch simulation (dry-run only, opt-in).

Never applies patches; operates in a temp directory and returns a structured
simulation result.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict


def simulate_patch(patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a safe dry-run of the patch:
    - load target module into isolated subprocess (placeholder)
    - run evaluator on sample chunk(s) (placeholder)
    - collect diagnostics
    - return structured results
    """
    patch_id = patch.get("id") or patch.get("target") or "unknown"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        # Placeholder: no real execution, just a structured response.
        metrics = {
            "simulated_checks": ["import_test", "lint_placeholder"],
            "tmp_dir": str(tmp_dir),
        }

    return {
        "patch_id": str(patch_id),
        "simulated": True,
        "metrics": metrics,
        "improvement": False,
        "notes": "Dry-run only.",
    }
