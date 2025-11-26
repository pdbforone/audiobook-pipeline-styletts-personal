"""Drift monitor for Phase T (opt-in, read-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def detect_system_drift(history_dir: Path = Path(".pipeline")) -> dict:
    """
    Aggregate signals across history to detect potential drift.
    """
    policy_logs = []
    bench = []
    self_eval = []
    patterns = []
    retro = []
    error_registry = _load_json(history_dir / "error_registry.json")

    policy_dir = history_dir / "policy_logs"
    bench_dir = history_dir / "benchmark_history"
    self_eval_dir = history_dir / "self_eval" / "reports"
    patterns_dir = history_dir / "research" / "patterns"
    retro_dir = history_dir / "research" / "retro_reports"

    if policy_dir.exists():
        policy_logs = list(policy_dir.glob("*.json"))
    if bench_dir.exists():
        bench = list(bench_dir.glob("*.json"))
    if self_eval_dir.exists():
        self_eval = list(self_eval_dir.glob("self_eval_*.json"))
    if patterns_dir.exists():
        patterns = list(patterns_dir.glob("*.json"))
    if retro_dir.exists():
        retro = list(retro_dir.glob("*.json"))

    # Heuristic signals
    signals = {
        "engine_performance": len(policy_logs),
        "failure_rate": len((error_registry.get("errors") or [])) if isinstance(error_registry.get("errors"), list) else 0,
        "quality_trend": len(bench),
        "chunking_skew": len(patterns),
        "metadata_skew": len(self_eval),
    }

    severity = "low"
    drift_detected = any(v > 0 for v in signals.values())
    if signals.get("failure_rate", 0) > 5:
        severity = "medium"
    if signals.get("failure_rate", 0) > 10:
        severity = "high"

    supporting_evidence: List[str] = []
    if drift_detected:
        if signals.get("failure_rate"):
            supporting_evidence.append("failure_rate_nonzero")
        if signals.get("engine_performance"):
            supporting_evidence.append("policy_logs_present")
        if signals.get("quality_trend"):
            supporting_evidence.append("benchmark_history_present")

    return {
        "drift_detected": drift_detected,
        "severity": severity,
        "signals": signals,
        "supporting_evidence": supporting_evidence,
    }
