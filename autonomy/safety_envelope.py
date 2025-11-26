"""
Safety envelope for Phase J (opt-in, additive-only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def apply_safety_envelope(
    readiness: Dict[str, Any],
    stability: Dict[str, Any],
    drift: Dict[str, Any],
    config: Any,
) -> Dict[str, Any]:
    """
    Returns:
    {
      "safe": bool,
      "blocked_reasons": list[str]
    }
    """
    reasons: List[str] = []
    safe = True

    if readiness and not readiness.get("ready", True):
        safe = False
        reasons.append("readiness_block")

    if stability and stability.get("violations"):
        safe = False
        reasons.extend(stability.get("violations", []))

    if drift and drift.get("drift_detected"):
        safe = False
        if drift.get("details"):
            reasons.append(str(drift.get("details")))

    return {
        "safe": safe,
        "blocked_reasons": reasons,
    }


def _load_safety_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_safety_state(path: Path, state: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        return


def escalation_logic(drift: Dict[str, Any], history_state: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """
    Tracks consecutive drift runs.
    If threshold reached:
        return {"lockout": True, "lockout_for": N}
    Else:
        return {"lockout": False}
    """
    escalation_cfg = getattr(config, "escalation", None) if config else None
    if not escalation_cfg or not getattr(escalation_cfg, "enable", False):
        return {"lockout": False}

    drift_threshold = getattr(escalation_cfg, "drift_threshold", 0) or 0
    lockout_runs = getattr(escalation_cfg, "lockout_runs", 0) or 0

    consecutive = history_state.get("consecutive_drift", 0)
    lockout_remaining = history_state.get("lockout_remaining", 0)

    if lockout_remaining > 0:
        lockout_remaining -= 1
        return {"lockout": True, "lockout_for": lockout_remaining, "state": {"consecutive_drift": 0, "lockout_remaining": lockout_remaining}}

    if drift.get("drift"):
        consecutive += 1
    else:
        consecutive = 0

    if drift_threshold and consecutive >= drift_threshold:
        lockout_remaining = lockout_runs
        return {"lockout": True, "lockout_for": lockout_remaining, "state": {"consecutive_drift": consecutive, "lockout_remaining": lockout_remaining}}

    return {"lockout": False, "state": {"consecutive_drift": consecutive, "lockout_remaining": lockout_remaining}}


def update_safety_state(path: Path, state: Dict[str, Any]) -> None:
    _write_safety_state(path, state)


def load_safety_state(path: Path) -> Dict[str, Any]:
    return _load_safety_state(path)
