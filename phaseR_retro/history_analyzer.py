"""Retrospective history analyzer (Phase R, opt-in, read-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def analyze_history(lookback: int = 20, base_dir: Path = Path(".pipeline")) -> dict:
    """
    Read-only retrospective analysis.
    Parse: policy_logs, benchmark_history, error_registry.json,
           self_eval/reports if present.
    Return exactly this schema:
    {
      "runs_analyzed": int,
      "failures_over_time": {...},
      "common_error_types": {...},
      "engine_regressions": {...},
      "chunk_quality_trends": {...},
      "llm_reasoning_patterns": {...},
      "benchmarks": {...}
    }
    """
    policy_logs_dir = base_dir / "policy_logs"
    benchmark_dir = base_dir / "benchmark_history"
    error_registry_path = base_dir / "error_registry.json"
    self_eval_dir = base_dir / "self_eval" / "reports"

    failures_over_time: Dict = {}
    common_error_types: Dict = {}
    engine_regressions: Dict = {}
    chunk_quality_trends: Dict = {}
    llm_reasoning_patterns: Dict = {}
    benchmarks: Dict = {}

    runs_analyzed = 0

    # Policy logs (lightweight scan)
    if policy_logs_dir.exists():
        for path in sorted(policy_logs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:lookback]:
            data = _load_json(path)
            runs_analyzed += 1
            failures = data.get("failures") or []
            if failures:
                failures_over_time[path.stem] = len(failures)
                for f in failures:
                    err_type = f.get("type") or "unknown"
                    common_error_types[err_type] = common_error_types.get(err_type, 0) + 1
            engine_info = data.get("engine_stats") or {}
            for name, stats in engine_info.items():
                engine_regressions.setdefault(name, {}).update(stats if isinstance(stats, dict) else {})
            llm = data.get("llm_reasoning") or {}
            if llm:
                llm_reasoning_patterns[path.stem] = llm

    # Benchmark history
    if benchmark_dir.exists():
        for path in sorted(benchmark_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:lookback]:
            data = _load_json(path)
            benchmarks[path.stem] = data.get("results") or data

    # Error registry
    errors = _load_json(error_registry_path)
    if errors:
        failures_over_time["error_registry_total"] = len(errors.get("errors", [])) if isinstance(errors.get("errors"), list) else 0
        for entry in errors.get("errors", []):
            err_type = entry.get("type") or "unknown"
            common_error_types[err_type] = common_error_types.get(err_type, 0) + 1
            phase = entry.get("phase")
            if phase:
                chunk_quality_trends[phase] = chunk_quality_trends.get(phase, 0) + 1

    # Self-eval reports
    if self_eval_dir.exists():
        for path in sorted(self_eval_dir.glob("self_eval_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:lookback]:
            data = _load_json(path)
            runs_analyzed += 1
            dims = data.get("dimensions") or {}
            if dims:
                chunk_quality_trends[path.stem] = dims
            llm_reasoning_patterns[path.stem] = data.get("signals", {})

    return {
        "runs_analyzed": runs_analyzed,
        "failures_over_time": failures_over_time,
        "common_error_types": common_error_types,
        "engine_regressions": engine_regressions,
        "chunk_quality_trends": chunk_quality_trends,
        "llm_reasoning_patterns": llm_reasoning_patterns,
        "benchmarks": benchmarks,
    }
