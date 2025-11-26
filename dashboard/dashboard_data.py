"""
Dashboard data interface (opt-in).

Provides read-only helpers that surface the latest run artifacts for a future UI.
No pipeline state is modified; functions simply read from existing .pipeline paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_latest_run_summary() -> Dict[str, Any]:
    """Return the most recent run summary from policy_runtime."""
    path = Path(".pipeline") / "policy_runtime" / "last_run_summary.json"
    return _read_json(path) or {}


def load_latest_diagnostics() -> Dict[str, Any]:
    """Return the latest diagnostics entry if present."""
    diag_dir = Path(".pipeline") / "diagnostics"
    if not diag_dir.exists():
        return {}
    candidates = sorted(diag_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {}
    return _read_json(candidates[0]) or {}


def load_latest_planner_recommendations() -> Dict[str, Any]:
    """Return the latest staged planner recommendation."""
    rec_dir = Path(".pipeline") / "staged_recommendations"
    if not rec_dir.exists():
        return {}
    candidates = sorted(rec_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {}
    return _read_json(candidates[0]) or {}


def load_latest_experiment_results() -> Dict[str, Any]:
    """Return the most recent experiment record."""
    exp_dir = Path(".pipeline") / "experiments"
    if not exp_dir.exists():
        return {}
    candidates = sorted(exp_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {}
    return _read_json(candidates[0]) or {}


def load_memory_statistics() -> Dict[str, Any]:
    """Return a lightweight memory summary if available."""
    try:
        from autonomy.memory_store import summarize_history
    except Exception:
        return {}
    try:
        return summarize_history()
    except Exception:
        return {}


def load_benchmark_summaries(limit: int = 5) -> List[Dict[str, Any]]:
    """Return up to `limit` latest benchmark files."""
    history_dir = Path(".pipeline") / "benchmark_history"
    if not history_dir.exists():
        return []
    candidates = sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    out: List[Dict[str, Any]] = []
    for cand in candidates:
        data = _read_json(cand)
        if data:
            out.append(data)
    return out
