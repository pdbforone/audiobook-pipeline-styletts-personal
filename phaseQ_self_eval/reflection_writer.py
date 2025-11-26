"""Phase Q: self-reflection writer (opt-in, non-destructive)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def write_reflection(meta_result: Dict[str, Any], output_dir: Path) -> Path:
    """
    Write a reflection entry to .pipeline/self_eval/reflections/<timestamp>.json
    """
    base = Path(output_dir)
    reflections_dir = base / "reflections"
    reflections_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = reflections_dir / f"{ts}.json"

    payload = {
        "timestamp": ts,
        "meta_score": float(meta_result.get("meta_score", 0.0)),
        "reasoning_summary": meta_result.get("reasoning_summary", ""),
        "concerns": meta_result.get("concerns", []),
        "recommended_focus": meta_result.get("recommended_focus", []),
        "raw": meta_result,
    }
    counter = 1
    while path.exists():
        path = reflections_dir / f"{ts}_{counter}.json"
        counter += 1
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
