"""
Reasoning trace recorder (Phase I, opt-in).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def begin_run_trace(run_id: str) -> Dict[str, Any]:
    """
    Initialize a reasoning trace structure for this run.
    Does not write to disk yet.
    Returns an in-memory trace dict.
    """
    return {"run_id": run_id, "started_at": datetime.utcnow().isoformat() + "Z", "events": []}


def record_event(trace: Dict[str, Any], stage: str, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """
    Append a timestamped event to the trace:
    {timestamp, stage, message, payload}
    """
    if trace is None:
        return
    events = trace.setdefault("events", [])
    events.append(
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stage": stage,
            "message": message,
            "payload": payload or {},
        }
    )


def finalize_trace(trace: Dict[str, Any], filepath: str) -> None:
    """
    Write the final trace to a JSON file in .pipeline/traces/.
    Non-destructive. Additive only.
    """
    if not trace:
        return
    try:
        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        trace["finished_at"] = datetime.utcnow().isoformat() + "Z"
        out_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    except Exception:
        return
