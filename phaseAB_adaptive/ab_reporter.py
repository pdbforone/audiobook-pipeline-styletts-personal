"""
Phase AB reporter: write unified Adaptive Brain summary (read-only).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


def write_ab_summary(report: Dict, base_dir: str = ".pipeline/ab/") -> Path:
    """
    Persist the Adaptive Brain summary under .pipeline/ab/.
    """
    out_dir = Path(base_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    out_path = out_dir / f"ab_summary_{ts}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out_path
