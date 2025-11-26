"""Regression detector for Phase R (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict


def detect_regressions(history_summary: dict) -> dict:
    """
    Return exactly this schema:
    {
      "regression_detected": bool,
      "severity": "low"|"medium"|"high",
      "signals": {
         "engine_regressions": {...},
         "speed_regressions": {...},
         "audio_quality": {...},
         "failure_spikes": {...},
         "llm_reasoning": {...},
         "chunk_boundary_drift": {...}
      },
      "supporting_runs": [...],
      "time_window": {...}
    }
    """
    summary = history_summary or {}
    signals: Dict = {
        "engine_regressions": summary.get("engine_regressions", {}),
        "speed_regressions": {},
        "audio_quality": summary.get("benchmarks", {}),
        "failure_spikes": summary.get("failures_over_time", {}),
        "llm_reasoning": summary.get("llm_reasoning_patterns", {}),
        "chunk_boundary_drift": summary.get("chunk_quality_trends", {}),
    }

    regression_detected = any(bool(v) for v in signals.values())
    severity = "low"
    if regression_detected:
        non_empty = sum(1 for v in signals.values() if v)
        severity = "medium" if non_empty <= 2 else "high"

    return {
        "regression_detected": regression_detected,
        "severity": severity,
        "signals": signals,
        "supporting_runs": list((summary.get("failures_over_time") or {}).keys()),
        "time_window": {"lookback_runs": summary.get("runs_analyzed", 0)},
    }
