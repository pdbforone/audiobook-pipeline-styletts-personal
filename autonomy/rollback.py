"""
Autonomy rollback journal (informational only, opt-in).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

JOURNAL_DIR = Path(".pipeline") / "autonomy_journal"
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)


def record_changes(run_id: str, changes: Dict[str, Any], reward: float) -> Path:
    """
    Append an entry describing applied changes and associated reward.
    """
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    entry = {
        "timestamp": ts,
        "run_id": run_id,
        "changes": changes,
        "reward": reward,
    }
    path = JOURNAL_DIR / f"{ts}_{run_id}.json"
    path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return path


def rollback_last(n: int = 1) -> Dict[str, Any]:
    """
    Return last n journal entries for manual rollback.
    """
    entries: List[Dict[str, Any]] = []
    if not JOURNAL_DIR.exists():
        return {"entries": []}
    files = sorted(JOURNAL_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    for f in files:
        try:
            entries.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return {"entries": entries}


def get_last_stable_state() -> Dict[str, Any]:
    """
    Load earliest journal entries with positive rewards.
    Does NOT apply changes. Returns suggested stable configuration.
    """
    if not JOURNAL_DIR.exists():
        return {"entries": []}
    entries: List[Dict[str, Any]] = []
    files = sorted(JOURNAL_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            reward = data.get("reward")
            if isinstance(reward, (int, float)) and reward > 0:
                entries.append(data)
        except Exception:
            continue
    return {"entries": entries}
