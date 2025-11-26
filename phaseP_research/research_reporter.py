"""Phase P: research reporting (opt-in, non-intrusive)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class ResearchReporter:
    def __init__(self):
        self.output_dir = Path(".pipeline") / "research" / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_report(self, analysis: Dict) -> str:
        """
        Writes normalized JSON report to .pipeline/research/reports/.
        Returns path string. Never overwrites existing files.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_id = analysis.get("id") or f"research_{timestamp}"
        path = self.output_dir / f"{report_id}.json"
        counter = 1
        while path.exists():
            path = self.output_dir / f"{report_id}_{counter}.json"
            counter += 1

        payload = {
            "id": report_id,
            "timestamp": analysis.get("timestamp", timestamp),
            "summary": analysis.get("summary", "Phase P research signals"),
            "signals": analysis.get("signals", {}),
            "details": analysis,
            "notes": analysis.get("notes", "Research collection (read-only)."),
            "version": "phaseP",
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)
