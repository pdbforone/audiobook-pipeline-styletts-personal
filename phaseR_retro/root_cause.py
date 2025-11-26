"""Root-cause mapper for Phase R (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict


def map_root_causes(regressions: dict, history_summary: dict) -> dict:
    """
    Read-only mapping of regressions → evidence.

    Return:
    {
      "probable_cause": str,
      "evidence": [...],
      "affected_engines": [...],
      "affected_phases": [...],
      "example_failures": [...],
      "confidence": float,
      "notes": str
    }
    """
    reg = regressions or {}
    summary = history_summary or {}
    signals = reg.get("signals") or {}
    evidence = []
    affected_engines = list((signals.get("engine_regressions") or {}).keys())
    affected_phases = list((signals.get("chunk_boundary_drift") or {}).keys())
    example_failures = list((summary.get("failures_over_time") or {}).keys())

    if signals.get("failure_spikes"):
        evidence.append("Failure spikes observed across runs.")
    if affected_engines:
        evidence.append("Engine regression signals present.")
    if affected_phases:
        evidence.append("Chunk boundary drift detected.")

    probable_cause = "insufficient_data"
    if affected_engines:
        probable_cause = "engine_behavior_change"
    elif signals.get("llm_reasoning"):
        probable_cause = "llm_reasoning_shift"
    elif signals.get("failure_spikes"):
        probable_cause = "pipeline_instability"

    confidence = 0.3
    if affected_engines and signals.get("failure_spikes"):
        confidence = 0.6
    if affected_engines and affected_phases and signals.get("failure_spikes"):
        confidence = 0.75

    return {
        "probable_cause": probable_cause,
        "evidence": evidence,
        "affected_engines": affected_engines,
        "affected_phases": affected_phases,
        "example_failures": example_failures,
        "confidence": confidence,
        "notes": "Heuristic, informational-only mapping (no runtime impact).",
    }
