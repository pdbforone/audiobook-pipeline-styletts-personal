"""Phase P: informational quality gate (opt-in, non-blocking)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import json


def _extract_signals(research_signals: Dict[str, Any]) -> Dict[str, Any]:
    analysis = research_signals.get("analysis", {}) if isinstance(research_signals, dict) else {}
    return {
        "phase_summary": analysis.get("phase_summary", {}),
        "failure_patterns": analysis.get("failure_patterns", {}),
        "engine_usage": analysis.get("engine_usage", {}),
        "chunk_distribution": analysis.get("chunk_distribution", {}),
        "memory_notes": analysis.get("memory_notes", {}),
        "policy_notes": analysis.get("policy_notes", {}),
    }


def _detect_issues(signals: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    failures = signals.get("failure_patterns", {}).get("counts", {})
    if any(count > 1 for count in failures.values()):
        issues.append("Repeated failure patterns detected across runs.")

    engines = signals.get("engine_usage", {}).get("frequency", {})
    if len(engines) == 1:
        issues.append("Single-engine dominance observed (monitor diversity).")

    chunk_dist = signals.get("chunk_distribution", {})
    if chunk_dist.get("max") and chunk_dist.get("min") and chunk_dist["max"] > (chunk_dist["min"] or 0) * 5:
        issues.append("Chunk size variance is high across runs.")

    return issues


def evaluate_quality_gate(research_signals: Dict[str, Any], run_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine research insights with run-level summary, producing an informational
    quality gate result. Non-blocking, observational only.
    """
    signals = _extract_signals(research_signals)
    issues = _detect_issues(signals)
    passed = not issues
    notes = "Informational quality gate; does not block pipeline."
    summary_status = {
        "phases": {k: v.get("status") for k, v in signals.get("phase_summary", {}).items()},
        "run_status": run_summary.get("status") if isinstance(run_summary, dict) else None,
    }
    result = {
        "passed": passed,
        "signals_considered": list(signals.keys()),
        "issues": issues,
        "notes": notes,
        "summary_status": summary_status,
    }
    return result


def write_quality_gate(result: Dict[str, Any]) -> str:
    """Write quality gate result to .pipeline/research/quality_gate_<timestamp>.json."""
    out_dir = Path(".pipeline") / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"quality_gate_{ts}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return str(path)
