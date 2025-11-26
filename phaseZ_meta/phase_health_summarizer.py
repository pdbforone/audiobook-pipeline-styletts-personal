"""Phase health summarizer for Phase Z (opt-in, read-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def summarize_health(base_dir: Path = Path(".pipeline")) -> Dict[str, Any]:
    """
    Aggregate health signals across phases and learning layers.
    Schema:
    {
      "phase_health": {...},
      "cross_phase_signals": {...},
      "alerts": [...],
      "notes": "string"
    }
    """
    health = {}
    cross = {}
    alerts = []

    # Collect various signals best-effort.
    health["tests"] = _load_json(base_dir / "test_results" / "latest.json")
    cross["drift"] = _load_json(base_dir / "drift" / "drift.json")
    cross["review"] = _load_json(base_dir / "review" / "reports" / "latest.json")
    cross["retro"] = _load_json(base_dir / "research" / "retro_reports" / "latest.json")
    cross["research"] = _load_json(base_dir / "research" / "patterns" / "latest.json")
    cross["predictive"] = _load_json(base_dir / "predictive" / "latest.json")
    cross["self_eval"] = _load_json(base_dir / "self_eval" / "reports" / "latest.json")

    if not health["tests"]:
        alerts.append("no_test_results_found")

    notes = "Phase health summary (Phase Z, read-only)."
    return {
        "phase_health": health,
        "cross_phase_signals": cross,
        "alerts": alerts,
        "notes": notes,
    }
