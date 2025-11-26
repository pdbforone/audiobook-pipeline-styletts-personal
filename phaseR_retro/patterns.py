"""Pattern extraction for Phase R (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict


def extract_patterns(evidence: dict) -> dict:
    """
    Output schema:
    {
      "common_failures": {...},
      "engine_trends": {...},
      "quality_trends": {...},
      "reasoning_patterns": {...},
      "chunk_trends": {...},
      "regression_hypotheses": [...]
    }
    """
    ev = evidence or {}
    common_failures = {}
    engine_trends = {}
    quality_trends = {}
    reasoning_patterns = {}
    chunk_trends = {}

    # Basic aggregation
    for log in ev.get("policy_logs", []):
        data = log.get("data") or {}
        failures = data.get("failures") or []
        for f in failures:
            key = f.get("type") or "unknown"
            common_failures[key] = common_failures.get(key, 0) + 1
        engines = data.get("engine_stats") or {}
        for name, stats in engines.items():
            engine_trends.setdefault(name, {}).update(stats if isinstance(stats, dict) else {})
        reasoning = data.get("llm_reasoning") or {}
        if reasoning:
            reasoning_patterns[log.get("path")] = reasoning

    for obs in ev.get("observations", []):
        data = obs.get("data") or {}
        if meta := data.get("meta"):
            chunk_trends[obs.get("path")] = meta

    for bench in ev.get("benchmark_history", []):
        data = bench.get("data") or {}
        quality_trends[bench.get("path")] = data

    regression_hypotheses = []
    if common_failures:
        regression_hypotheses.append("Failure frequency increasing in certain categories.")
    if engine_trends:
        regression_hypotheses.append("Engine metrics show variation across runs.")
    if quality_trends:
        regression_hypotheses.append("Benchmark quality trends observed.")

    return {
        "common_failures": common_failures,
        "engine_trends": engine_trends,
        "quality_trends": quality_trends,
        "reasoning_patterns": reasoning_patterns,
        "chunk_trends": chunk_trends,
        "regression_hypotheses": regression_hypotheses,
    }
