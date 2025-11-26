"""Research reporter for Phase R (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_retro_report(report: dict, base_dir: Path = Path(".pipeline/research/reports/retro")) -> Path:
    """
    Write normalized retro report; never overwrite existing files. Must return report path.
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id = report.get("id") or f"retro_{ts}"
    path = base_dir / f"{report_id}.json"
    counter = 1
    while path.exists():
        path = base_dir / f"{report_id}_{counter}.json"
        counter += 1

    payload = {
        "id": report_id,
        "timestamp": report.get("created_at", ts),
        "summary": report.get("summary", "Phase R retrospective report"),
        "signals": {
            "regressions": report.get("regressions", []),
            "root_causes": report.get("root_causes", []),
        },
        "details": {
            "regressions": report.get("regressions", []),
            "root_causes": report.get("root_causes", []),
            "long_term_trends": report.get("long_term_trends", {}),
            "llm_patterns": report.get("llm_patterns", {}),
            "engine_trends": report.get("engine_trends", {}),
            "chunking_trends": report.get("chunking_trends", {}),
            "quality_trends": report.get("quality_trends", {}),
            "runs_analyzed": report.get("runs_analyzed", 0),
        },
        "notes": report.get("notes", "Retrospective analysis (read-only)."),
        "version": "phaseR",
    }

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
