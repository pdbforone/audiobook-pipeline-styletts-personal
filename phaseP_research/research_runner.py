"""Phase P: research lifecycle controller (opt-in, non-blocking)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .evidence_ingestion import collect_evidence
from .patterns import extract_patterns


class ResearchRunner:
    def __init__(self, config):
        self.config = config
        self.run_dir: Path | None = None
        self.run_timestamp: str | None = None

    def _ensure_run_dir(self) -> Path:
        base = Path(".pipeline") / "research" / "runs"
        base.mkdir(parents=True, exist_ok=True)
        ts = self.run_timestamp or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.run_timestamp = ts
        self.run_dir = base / ts
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir

    def begin_run(self) -> Path:
        return self._ensure_run_dir()

    def ingest_evidence(self, run_state=None, logs=None) -> Dict[str, Any]:
        run_dir = self._ensure_run_dir()
        evidence = collect_evidence(run_state, logs or [])
        (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        return evidence

    def extract_patterns(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        run_dir = self._ensure_run_dir()
        patterns = extract_patterns(evidence)
        (run_dir / "patterns.json").write_text(json.dumps(patterns, indent=2), encoding="utf-8")
        return patterns

    def write_report(self, analysis: Dict[str, Any]) -> str:
        run_dir = self._ensure_run_dir()
        report_path = run_dir / "report.json"
        report_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        return str(report_path)
