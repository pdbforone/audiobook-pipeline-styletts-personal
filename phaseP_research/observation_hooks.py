"""Phase P: shared observation hook utilities (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .research_config import ResearchConfig


def record_phase_observation(phase: str, data: Dict[str, Any], config: ResearchConfig) -> str | None:
    """
    Write a lightweight observation snapshot for a phase.
    Only runs when research is enabled; never mutates inputs or behavior.
    """
    if not getattr(config, "enable_research", False):
        return None
    out_dir = Path(".pipeline") / "research" / "observations"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    payload = {
        "phase": phase,
        "timestamp": ts,
        "input_size": data.get("input_size"),
        "output_size": data.get("output_size"),
        "metadata": data.get("metadata", {}),
    }
    path = out_dir / f"{ts}_{phase}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
