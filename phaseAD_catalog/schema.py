"""
Minimal schema utilities for Phase AD catalog validation.
"""

from __future__ import annotations

from typing import Any, Dict, List


REQUIRED_TOP_LEVEL = {"phase_list", "capabilities", "ui_exposable", "metadata"}


def validate_catalog(payload: Dict[str, Any]) -> bool:
    """
    Minimal schema validation for catalog.json.
    """
    if not isinstance(payload, dict):
        return False
    if not REQUIRED_TOP_LEVEL.issubset(set(payload.keys())):
        return False

    if not isinstance(payload.get("phase_list"), list):
        return False
    if not isinstance(payload.get("capabilities"), dict):
        return False
    if not isinstance(payload.get("ui_exposable"), list):
        return False
    if not isinstance(payload.get("metadata"), dict):
        return False

    caps = payload.get("capabilities", {})
    required_caps_keys: List[str] = [
        "phases",
        "modules",
        "flags",
        "safety_systems",
        "autonomy_layers",
        "research_layers",
        "self_eval_layers",
        "ui_components",
        "engines",
        "version",
    ]
    for key in required_caps_keys:
        if key not in caps:
            return False
    return True
