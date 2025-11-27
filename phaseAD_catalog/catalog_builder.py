"""
Phase AD catalog builder: normalize scanner output for UI consumption.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def _normalize_phases(phases: List[str]) -> List[str]:
    return sorted({p for p in phases})


def _normalize_capabilities(scanner_output: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "phases": scanner_output.get("phases", []),
        "modules": scanner_output.get("modules", {}),
        "flags": scanner_output.get("flags", {}),
        "safety_systems": scanner_output.get("safety_systems", []),
        "autonomy_layers": scanner_output.get("autonomy_layers", []),
        "research_layers": scanner_output.get("research_layers", []),
        "self_eval_layers": scanner_output.get("self_eval_layers", []),
        "ui_components": scanner_output.get("ui_components", []),
        "engines": scanner_output.get("engines", []),
        "version": scanner_output.get("version", "auto-generated"),
    }
    return normalized


def _build_ui_exposable(scanner_output: Dict[str, Any]) -> List[str]:
    ui_items: List[str] = []
    ui_items.extend(scanner_output.get("phases", []))
    ui_items.extend(scanner_output.get("engines", []))
    ui_items.extend(scanner_output.get("ui_components", []))
    return sorted({i for i in ui_items if i})


def build_catalog(scanner_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build normalized catalog payload.
    """
    phases = _normalize_phases(scanner_output.get("phases", []))
    capabilities = _normalize_capabilities(scanner_output)
    ui_exposable = _build_ui_exposable(scanner_output)

    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "scanner_version": "AD-1.0",
    }

    return {
        "phase_list": phases,
        "capabilities": capabilities,
        "ui_exposable": ui_exposable,
        "metadata": metadata,
    }
