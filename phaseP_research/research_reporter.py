"""Phase P: research reporting (opt-in, non-intrusive)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class ResearchReporter:
    def __init__(self):
        self.output_dir = Path(".pipeline") / "research"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_report(self, analysis: Dict) -> str:
        """
        Writes JSON report to .pipeline/research/.
        Returns path string.
        Never overwrites existing files.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base = self.output_dir / f"{timestamp}_report.json"
        path = base
        counter = 1
        while path.exists():
            path = self.output_dir / f"{timestamp}_report_{counter}.json"
            counter += 1
        path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        return str(path)
