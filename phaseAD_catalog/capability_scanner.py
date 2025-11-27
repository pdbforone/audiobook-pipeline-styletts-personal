"""
Phase AD capability scanner (read-only).
Scans configs and filesystem to build a raw capability map for the UI catalog.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _list_phase_dirs(project_root: Path) -> List[str]:
    phases: List[str] = []
    for entry in project_root.iterdir():
        name = entry.name
        if entry.is_dir() and name.lower().startswith("phase") and len(name) >= 6:
            phases.append(name)
    return sorted(phases)


def _detect_engines(cfg: Dict[str, Any]) -> List[str]:
    engines = []
    tts_engines = cfg.get("tts_engines") or {}
    primary = tts_engines.get("primary")
    secondary = tts_engines.get("secondary")
    for eng in (primary, secondary):
        if eng and eng not in engines:
            engines.append(eng)
    tts_engine = cfg.get("tts_engine")
    if tts_engine and tts_engine not in engines:
        engines.append(tts_engine)
    # Explicitly keep Piper disabled
    return [e for e in engines if e and e.lower() != "piper"]


def _collect_flags(cfg: Dict[str, Any]) -> Dict[str, Any]:
    flags = {}
    for key in cfg.keys():
        if key.startswith("phase") or key in {"autonomy", "research", "reasoning", "self_eval", "policy_engine"}:
            flags[key] = cfg.get(key)
    return flags


def _modules_from_flags(cfg: Dict[str, Any]) -> Dict[str, Any]:
    modules = {}
    autonomy = cfg.get("autonomy", {}) or {}
    research = cfg.get("research", {}) or {}
    reasoning = cfg.get("reasoning", {}) or {}
    experiments = cfg.get("experiments", {}) or {}
    modules["autonomy"] = autonomy
    modules["research"] = research
    modules["reasoning"] = reasoning
    modules["experiments"] = experiments
    modules["self_eval"] = cfg.get("self_eval", {}) or {}
    modules["self_evaluation"] = cfg.get("phaseQ_self_evaluation", {}) or {}
    modules["retro"] = cfg.get("phaseR", {}) or {}
    modules["review"] = cfg.get("phaseS", {}) or {}
    modules["audit"] = cfg.get("phaseT", {}) or {}
    modules["schema"] = cfg.get("phaseU", {}) or {}
    modules["harness"] = cfg.get("phaseV", {}) or {}
    modules["global_checks"] = cfg.get("phaseW", {}) or {}
    modules["meta"] = cfg.get("phaseX", {}) or {}
    modules["self_heal"] = cfg.get("phaseY", {}) or {}
    modules["meta_closure"] = cfg.get("phaseZ", {}) or {}
    modules["phaseAA"] = cfg.get("phaseAA", {}) or {}
    modules["phaseAB"] = cfg.get("phaseAB", {}) or {}
    modules["phaseAC"] = cfg.get("phaseAC", {}) or {}
    modules["phaseAD"] = cfg.get("phaseAD", {}) or {}
    return modules


def scan_capabilities(config_path: Path | None = None) -> Dict[str, Any]:
    """
    Scan config and filesystem for capability signals. Read-only.
    """
    project_root = Path(__file__).resolve().parent.parent
    cfg_path = config_path or project_root / "phase6_orchestrator" / "config.yaml"
    cfg = _load_config(cfg_path)

    phases = _list_phase_dirs(project_root)
    engines = _detect_engines(cfg)
    flags = _collect_flags(cfg)
    modules = _modules_from_flags(cfg)

    safety_systems = [
        "readiness",
        "stability_bounds",
        "drift_detection",
        "safety_envelope",
        "safety_escalation",
        "budget",
        "policy_engine",
    ]

    autonomy_layers = [
        "planner",
        "supervised_overrides",
        "autonomous_overrides",
        "self_review",
        "rewards",
        "stability_profiles",
        "memory_feedback",
        "global_safety_envelope",
        "adaptive_brain",
    ]

    research_layers = ["phaseP_research", "phaseR_retro", "phaseW_global", "phaseX_meta"]
    self_eval_layers = ["phaseQ_self_eval", "phaseQ_self_evaluation"]
    ui_components = ["ui/app.py", "dashboard", "capability_catalog"]

    return {
        "phases": phases,
        "engines": engines,
        "modules": modules,
        "flags": flags,
        "safety_systems": safety_systems,
        "autonomy_layers": autonomy_layers,
        "research_layers": research_layers,
        "self_eval_layers": self_eval_layers,
        "ui_components": ui_components,
        "version": "auto-generated",
    }


if __name__ == "__main__":
    catalog = scan_capabilities()
    print(json.dumps(catalog, indent=2))
