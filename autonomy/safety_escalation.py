"""
Safety escalation (lockout) for Phase J (opt-in, additive-only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def evaluate_escalation(safety_state: Dict[str, Any], drift: Dict[str, Any], stability: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """
    Returns:
    {
      "lockout": bool,
      "lockout_reason": str | None,
      "updated_state": dict
    }
    """
    escalation_cfg = getattr(config, "escalation", None) if config else None
    if not escalation_cfg or not getattr(escalation_cfg, "enable", False):
        return {"lockout": False, "lockout_reason": None, "updated_state": safety_state or {}}

    drift_threshold = getattr(escalation_cfg, "drift_threshold", 0) or 0
    lockout_runs = getattr(escalation_cfg, "lockout_runs", 0) or 0

    state = dict(safety_state or {})
    consecutive = state.get("consecutive_drift", 0)
    lockout_remaining = state.get("lockout_remaining", 0)

    if lockout_remaining > 0:
        state["lockout_remaining"] = max(0, lockout_remaining - 1)
        return {"lockout": True, "lockout_reason": "lockout_active", "updated_state": state}

    if drift.get("drift_detected"):
        consecutive += 1
    else:
        consecutive = 0

    state["consecutive_drift"] = consecutive

    if drift_threshold and consecutive >= drift_threshold:
        state["lockout_remaining"] = lockout_runs
        return {"lockout": True, "lockout_reason": "persistent_drift", "updated_state": state}

    return {"lockout": False, "lockout_reason": None, "updated_state": state}


def apply_escalation(lockout: bool, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies escalation effects to state (in-memory only).
    Returns the updated state.
    """
    return state if lockout else state


def load_safety_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_safety_state(path: Path, state: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        return
