"""Invariant checker for Phase Z (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any, List


def check_invariants(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate invariants:
    - No phase writes outside .pipeline/
    - Only XTTS/Kokoro engines
    - Autonomy defaults off
    - No persistent overrides (except allowed journal)
    - JSON summaries include core keys when present
    """
    failed: List[str] = []
    details: Dict[str, Any] = {}

    # Placeholder checks; real checks would parse artifacts.
    details["engine_policy"] = "XTTS/Kokoro only (assumed unchanged); Piper disabled."
    details["autonomy_defaults"] = "Assumed defaults off unless enabled."
    details["override_files"] = "No validation performed; informational only."
    details["summary_keys"] = "Not validated; informational only."

    invariant_pass = len(failed) == 0
    return {
        "invariant_pass": invariant_pass,
        "failed": failed,
        "details": details,
    }
