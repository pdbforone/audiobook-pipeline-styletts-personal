"""Meta kernel for Phase Z (opt-in, read-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List


def collect_phase_states(base_dir: Path = Path(".pipeline")) -> Dict[str, Any]:
    """Collect phase states from pipeline artifacts (best-effort, read-only)."""
    states: Dict[str, Any] = {}
    for phase in ["phase1", "phase2", "phase3", "phase4", "phase5", "phase6"]:
        path = base_dir / f"{phase}.json"
        if path.exists():
            try:
                states[phase] = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                states[phase] = {}
        else:
            states[phase] = {}
    return states


def build_meta_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """Build a lightweight meta summary."""
    phases_scanned: List[str] = list(state.keys())
    missing_phases = [p for p, v in state.items() if not v]
    health_overview = {p: ("ok" if v else "missing") for p, v in state.items()}
    warnings = []
    if missing_phases:
        warnings.append("missing_phase_data")
    return {
        "phases_scanned": phases_scanned,
        "missing_phases": missing_phases,
        "health_overview": health_overview,
        "warnings": warnings,
        "notes": "Phase Z meta-kernel summary (read-only).",
    }


def analyze_full_pipeline(base_dir: Path = Path(".pipeline")) -> Dict[str, Any]:
    """
    Analyze the full pipeline state without executing phases.
    Returns:
    {
      "phases_scanned": [...],
      "missing_phases": [...],
      "health_overview": {...},
      "warnings": [...],
      "notes": "string"
    }
    """
    state = collect_phase_states(base_dir=base_dir)
    return build_meta_summary(state)
