"""Cross-phase observation hooks for Phase R (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

OBS_DIR = Path(".pipeline") / "research" / "observations"


def _write_snapshot(phase: str, meta: Dict[str, Any]) -> None:
    try:
        OBS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = OBS_DIR / f"{ts}_{phase}.json"
        payload = {"phase": phase, "timestamp": ts, "meta": meta or {}}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        # Observations must never interfere with runtime
        return


def observe_phase1(meta: Dict[str, Any]) -> None:
    _write_snapshot("phase1", meta)


def observe_phase2(meta: Dict[str, Any]) -> None:
    _write_snapshot("phase2", meta)


def observe_phase3(meta: Dict[str, Any]) -> None:
    _write_snapshot("phase3", meta)


def observe_phase4(meta: Dict[str, Any]) -> None:
    _write_snapshot("phase4", meta)


def observe_phase5(meta: Dict[str, Any]) -> None:
    _write_snapshot("phase5", meta)


def observe_phase6(meta: Dict[str, Any]) -> None:
    _write_snapshot("phase6", meta)
