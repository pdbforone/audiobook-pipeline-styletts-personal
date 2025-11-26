"""
Phase AB fusion: normalize raw signals into a consistent structure.
"""

from __future__ import annotations

from typing import Any, Dict


def fuse_signals(raw_signals: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize incoming signals to predictable dict shapes."""
    fused: Dict[str, Any] = {}
    for key in [
        "memory",
        "stability",
        "budget",
        "consistency",
        "integration",
        "research",
        "self_eval",
        "retro",
        "health",
        "audit",
        "schema_validation",
        "harmonizer",
        "ui_signals",
        "meta_agent",
        "future_guardrails",
        "activation_safety",
    ]:
        value = raw_signals.get(key, {})
        if value is None:
            value = {}
        fused[key] = value if isinstance(value, dict) else {"value": value}
    return fused
