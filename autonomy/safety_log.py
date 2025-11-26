"""
Safety event logging for Phase J (additive-only).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def log_safety_event(event: str, details: Dict[str, Any]) -> None:
    """
    Writes structured safety event logs to:
    .pipeline/policy_runtime/safety_events/<timestamp>.json
    """
    try:
        ts = datetime.utcnow().isoformat() + "Z"
        out_dir = Path(".pipeline") / "policy_runtime" / "safety_events"
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {"event": event, "timestamp": ts, "details": details or {}}
        out_path = out_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        return
