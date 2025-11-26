"""
Phase AB kernel: collect raw signals from prior phases (read-only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _load_latest_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load the most recent JSON file in a directory, if any."""
    if not path.exists():
        return None
    if path.is_file() and path.suffix.lower() == ".json":
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    if path.is_dir():
        candidates = sorted(path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for candidate in candidates:
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


def evaluate_all_sources(run_summary: Dict[str, Any], base_dir: str = ".pipeline") -> Dict[str, Any]:
    """
    Collect best-effort signals from prior phases without mutating state.
    """
    base = Path(base_dir)

    def load_rel(*parts: str) -> Optional[Dict[str, Any]]:
        return _load_latest_json(base.joinpath(*parts))

    signals = {
        "memory": run_summary.get("memory") if isinstance(run_summary, dict) else None,
        "stability": load_rel("stability_profiles") or run_summary.get("stability"),
        "budget": run_summary.get("budget"),
        "consistency": load_rel("consistency") or run_summary.get("consistency"),
        "integration": load_rel("integration") or run_summary.get("integration"),
        "research": load_rel("research") or run_summary.get("research"),
        "self_eval": load_rel("self_eval") or run_summary.get("self_eval"),
        "retro": load_rel("retro") or run_summary.get("retro"),
        "health": load_rel("health") or run_summary.get("health"),
        "audit": load_rel("policy_runtime", "safety_events") or run_summary.get("audit"),
        "schema_validation": load_rel("schema") or run_summary.get("schema_validation"),
        "harmonizer": load_rel("harmonizer") or run_summary.get("harmonizer"),
        "ui_signals": load_rel("ui") or run_summary.get("ui_signals"),
        "meta_agent": load_rel("meta") or run_summary.get("meta_agent"),
        "future_guardrails": load_rel("future_guardrails") or run_summary.get("future_guardrails"),
        "activation_safety": load_rel("autonomy", "final_safety") or run_summary.get("activation_safety"),
    }

    return {k: v for k, v in signals.items() if v is not None}
