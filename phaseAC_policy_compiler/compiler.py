"""Policy profile compiler for Phase AC (opt-in, read-only, non-destructive)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def _block(name: str, source: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    block_cfg = cfg.get(name) if isinstance(cfg, dict) else {}
    enabled = bool(block_cfg.get("enable")) if isinstance(block_cfg, dict) else False
    return {"enabled": enabled, "source": source, "details": block_cfg if isinstance(block_cfg, dict) else {}}


def compile_policy_profile(config: Any, base_dir: Path = Path(".pipeline")) -> Dict[str, Any]:
    """
    Compile a unified policy profile from existing phase outputs/configs.
    Produces read-only policy intents.
    """
    cfg_dict = config.dict() if hasattr(config, "dict") else (config or {})
    profile = {
        "safety_envelope": _block("autonomy", "phaseJ", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "stability_bounds": _block("autonomy", "phaseJ", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "drift_signals": _block("phaseJ", "phaseJ", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "self_eval": _block("phaseQ", "phaseQ", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "root_cause_analysis": _block("phaseR", "phaseR", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "review_ratings": _block("phaseS", "phaseS", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "audit_signals": _block("phaseT", "phaseT", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "schema_validator": _block("phaseU", "phaseU", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "orchestrator_invariants": _block("phaseV", "phaseV", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "diagnostic_modes": _block("phaseW", "phaseW", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "meta_x": _block("phaseX", "phaseX", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "meta_y": _block("phaseY", "phaseY", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "meta_z": _block("phaseZ", "phaseZ", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "phaseAA": _block("phaseAA", "phaseAA", cfg_dict if isinstance(cfg_dict, dict) else {}),
        "phaseAB": _block("phaseAB", "phaseAB", cfg_dict if isinstance(cfg_dict, dict) else {}),
    }
    profile["base_dir"] = str(base_dir)
    profile["notes"] = "Phase AC compiled profile (read-only, no overrides applied)."
    return profile
