"""Research lifecycle controller for Phase R (opt-in, read-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from . import patterns, research_reporter, history_analyzer, regression_detector, root_cause
from .evidence_ingestion import ingest_all


RUNS_DIR = Path(".pipeline") / "research" / "runs"


def _ensure_run_dir(run_id: str) -> Path:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def begin_run(run_id: str) -> Path:
    run_dir = _ensure_run_dir(run_id)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    (run_dir / "begin.json").write_text(json.dumps({"run_id": run_id, "started_at": ts}, indent=2), encoding="utf-8")
    return run_dir


def ingest_evidence(run_id: str) -> Dict:
    evidence = ingest_all(run_id, base_dir=".pipeline")
    run_dir = _ensure_run_dir(run_id)
    (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence


def extract_patterns(run_id: str, evidence: Dict | None = None) -> Dict:
    ev = evidence or ingest_all(run_id, base_dir=".pipeline")
    derived = patterns.extract_patterns(ev)
    run_dir = _ensure_run_dir(run_id)
    (run_dir / "patterns.json").write_text(json.dumps(derived, indent=2), encoding="utf-8")
    return derived


def write_report(run_id: str, evidence: Dict | None = None, derived: Dict | None = None) -> Path:
    ev = evidence or ingest_all(run_id, base_dir=".pipeline")
    derived = derived or patterns.extract_patterns(ev)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    history_summary = history_analyzer.analyze_history(base_dir=Path(".pipeline"))
    regressions = regression_detector.detect_regressions(history_summary)
    root_cause_map = root_cause.map_root_causes(regressions, history_summary)
    report = {
        "id": f"retro_{run_id}",
        "summary": "Retrospective run report (informational only).",
        "regressions": regressions,
        "root_causes": root_cause_map,
        "long_term_trends": derived.get("quality_trends", {}),
        "llm_patterns": derived.get("reasoning_patterns", {}),
        "engine_trends": derived.get("engine_trends", {}),
        "chunking_trends": derived.get("chunk_trends", {}),
        "quality_trends": derived.get("quality_trends", {}),
        "created_at": ts,
        "runs_analyzed": len(ev.get("runs", [])) if isinstance(ev.get("runs"), list) else ev.get("runs_analyzed", 0),
    }
    # Persist run-local copy
    run_dir = _ensure_run_dir(run_id)
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Persist retro report
    return research_reporter.write_retro_report(report)
