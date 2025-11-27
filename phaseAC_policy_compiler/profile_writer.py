"""Profile writer for Phase AC (read-only outputs)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def write_policy_profile(profile: Dict[str, Any], base_dir: Path = Path(".pipeline/policy_profiles")) -> Path:
    """
    Write policy profile to .pipeline/policy_profiles/<timestamp>.json without overwriting existing files.
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = base_dir / f"{ts}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{ts}_{counter}.json"
        counter += 1
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return path
