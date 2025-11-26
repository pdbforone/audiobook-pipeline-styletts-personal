"""Research state initializer for Phase R (opt-in)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def ensure_research_state(base_dir: str | Path = ".pipeline") -> Path:
    base = Path(base_dir)
    research_root = base / "research"
    dirs = [
        research_root,
        research_root / "observations",
        research_root / "evidence",
        research_root / "patterns",
        research_root / "runs",
        research_root / "retro_reports",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    version_path = research_root / "research_version.json"
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if not version_path.exists():
        version_path.write_text(json.dumps({"version": "R1", "initialized_at": ts}, indent=2), encoding="utf-8")
    return research_root
