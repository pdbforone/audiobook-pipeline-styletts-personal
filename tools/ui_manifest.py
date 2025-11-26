"""UI capability manifest generator (read-only, opt-in only).

Produces a structured manifest for UI surfaces covering all phases (A–Z) and
core pipeline stages. This is descriptive metadata only; it does not mutate
runtime configuration or enable any phases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml
except Exception:  # noqa: BLE001
    yaml = None  # type: ignore


# Alphabetical phases A–Z plus core numeric phases for completeness.
PHASE_ORDER_ALPHA: Tuple[str, ...] = tuple(f"phase{chr(code)}" for code in range(ord("A"), ord("Z") + 1))
PHASE_ORDER_CORE: Tuple[str, ...] = ("phase1", "phase2", "phase3", "phase4", "phase5", "phase5_5", "phase6", "phase7")

# Mapping from phase key to friendly labels.
PHASE_LABELS: Dict[str, str] = {
    "phase1": "Validation",
    "phase2": "Extraction",
    "phase3": "Chunking",
    "phase4": "TTS",
    "phase5": "Enhancement",
    "phase5_5": "Subtitles",
    "phase6": "Orchestrator",
    "phase7": "Batch",
    "phaseA": "Preflight Sandbox",
    "phaseB": "Input Vetting",
    "phaseC": "Content Filters",
    "phaseD": "Self-Repair",
    "phaseE": "Benchmark",
    "phaseF": "Metadata Enrichment",
    "phaseG": "Autonomy (Gates Off)",
    "phaseH": "Reasoning",
    "phaseI": "Introspection",
    "phaseJ": "Stability & Drift",
    "phaseK": "Readiness & Rewards",
    "phaseL": "Meta-Autonomy Assessment",
    "phaseM": "Test Instrumentation",
    "phaseN": "Integration Suite",
    "phaseO": "Extended Test Mode",
    "phaseP": "Research",
    "phaseQ": "Self-Evaluation",
    "phaseR": "Retrospective",
    "phaseS": "Review & Health",
    "phaseT": "Audit & Consistency",
    "phaseU": "Schema Validator",
    "phaseV": "Migrations",
    "phaseW": "Global Consistency",
    "phaseX": "Meta-Evaluator",
    "phaseY": "Self-Heal (Read-only)",
    "phaseZ": "Meta Diagnostics",
}

# Config sections that map to lettered phases.
PHASE_CONFIG_SOURCES: Dict[str, Tuple[str, ...]] = {
    "phaseA": ("phaseA",),
    "phaseB": ("phaseB",),
    "phaseC": ("phaseC",),
    "phaseD": ("self_repair",),
    "phaseE": ("benchmark",),
    "phaseF": ("metadata",),
    "phaseG": ("autonomy",),
    "phaseH": ("reasoning",),
    "phaseI": ("introspection",),
    "phaseJ": ("phaseJ",),
    "phaseK": ("phaseK",),
    "phaseL": ("phaseL",),
    "phaseM": ("phaseM",),
    "phaseN": ("phaseN",),
    "phaseO": ("phaseO",),
    "phaseP": ("research",),
    "phaseQ": ("phaseQ_self_eval", "phaseQ_self_evaluation"),
    "phaseR": ("phaseR",),
    "phaseS": ("phaseS",),
    "phaseT": ("phaseT", "consistency"),
    "phaseU": ("phaseU",),
    "phaseV": ("phaseV",),
    "phaseW": ("phaseW",),
    "phaseX": ("phaseX",),
    "phaseY": ("phaseY",),
    "phaseZ": ("phaseZ",),
}

# Auxiliary overlays that impact UI toggles but do not correspond to phases directly.
AUXILIARY_KEYS: Tuple[str, ...] = (
    "policy_engine",
    "experiments",
    "genre",
    "rewriter",
    "adaptive_chunking",
    "patches",
    "capabilities",
    "dashboard",
)


@dataclass
class SafetyGates:
    enable: bool = False
    supervised_threshold: Any = None
    override_limits: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "enable": bool(self.enable),
            "supervised_threshold": self.supervised_threshold,
            "override_limits": self.override_limits,
            "notes": self.notes,
        }


def _load_config(config_path: Path) -> Dict[str, Any]:
    """Load YAML config safely."""
    if not config_path.exists() or yaml is None:
        return {}
    try:
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _flatten_settings(data: Any, prefix: str = "") -> Tuple[List[str], List[Dict[str, Any]]]:
    """Flatten nested dictionaries into dot-notated keys for UI presentation."""
    if not isinstance(data, dict):
        return [], []
    keys: List[str] = []
    settings: List[Dict[str, Any]] = []
    for raw_key, value in sorted(data.items(), key=lambda item: item[0]):
        key = f"{prefix}.{raw_key}" if prefix else raw_key
        keys.append(key)
        settings.append({"key": key, "value": value})
        subkeys, subsettings = _flatten_settings(value, key) if isinstance(value, dict) else ([], [])
        keys.extend(subkeys)
        settings.extend(subsettings)
    return keys, settings


def _merge_sections(cfg: Dict[str, Any], sections: Tuple[str, ...]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for section in sections:
        block = cfg.get(section, {})
        if isinstance(block, dict):
            merged = {**merged, **block}
    return merged


def _build_safety_gates(phase_key: str, block: Dict[str, Any]) -> SafetyGates:
    gates = SafetyGates(enable=bool(block.get("enable")) if isinstance(block, dict) else False)
    if not isinstance(block, dict):
        return gates

    if "supervised_threshold" in block:
        gates.supervised_threshold = block.get("supervised_threshold")
    if phase_key == "phaseG":
        budget = block.get("budget", {}) if isinstance(block.get("budget"), dict) else {}
        gates.override_limits = {
            "max_overrides_per_run": budget.get("max_overrides_per_run"),
            "max_change_magnitude": budget.get("max_change_magnitude"),
            "allowed_fields": budget.get("allowed_fields", []),
        }
        gates.supervised_threshold = block.get("supervised_threshold")
        gates.notes = "Autonomy remains disabled; thresholds are informational only."
    else:
        limits = {k: v for k, v in block.items() if "limit" in k or "threshold" in k}
        if limits:
            gates.override_limits = limits
    return gates


def _phase_entry(phase_key: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Create a manifest entry for a single phase."""
    label = PHASE_LABELS.get(phase_key, phase_key)
    block: Dict[str, Any] = {}
    if phase_key in PHASE_CONFIG_SOURCES:
        block = _merge_sections(cfg, PHASE_CONFIG_SOURCES[phase_key])
    elif phase_key in cfg and isinstance(cfg.get(phase_key), dict):
        block = cfg.get(phase_key, {})  # type: ignore[assignment]

    flattened_keys, settings = _flatten_settings(block)
    if not flattened_keys:
        flattened_keys = ["enable"]
        settings = [{"key": "enable", "value": bool(block.get("enable")) if isinstance(block, dict) else False}]

    entry = {
        "phase_key": phase_key,
        "label": label,
        "config_keys": flattened_keys,
        "settings": settings,
        "safety_gates": _build_safety_gates(phase_key, block).as_dict(),
        "category": "autonomy" if phase_key in {"phaseG", "phaseH", "phaseI", "phaseJ", "phaseK", "phaseL"} else "pipeline",
        "enabled_by_default": bool(block.get("enable")) if isinstance(block, dict) else False,
    }
    return entry


def _auxiliary_entries(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for key in AUXILIARY_KEYS:
        block = cfg.get(key, {}) if isinstance(cfg.get(key), dict) else {}
        flattened_keys, settings = _flatten_settings(block)
        entries.append(
            {
                "name": key,
                "config_keys": flattened_keys,
                "settings": settings,
                "notes": "Read-only overlay; does not change defaults.",
            }
        )
    return entries


def generate_ui_capabilities(
    config_path: Path = Path("phase6_orchestrator/config.yaml"),
    output_path: Path = Path(".pipeline/reference/ui_capabilities.json"),
) -> Path:
    """Generate the UI capability manifest JSON."""
    cfg = _load_config(config_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    phases: List[Dict[str, Any]] = []

    # Core numeric phases
    for key in PHASE_ORDER_CORE:
        phases.append(_phase_entry(key, cfg))

    # Alphabet phases A–Z
    for key in PHASE_ORDER_ALPHA:
        phases.append(_phase_entry(key, cfg))

    manifest = {
        "version": "2.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_config": str(config_path),
        "phases": phases,
        "auxiliary": _auxiliary_entries(cfg),
        "notes": "UI capability manifest (read-only). Piper remains disabled; XTTS/Kokoro only. No autonomy enabled.",
    }
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output_path


__all__ = ["generate_ui_capabilities"]


if __name__ == "__main__":
    generate_ui_capabilities()
