"""Self-heal kernel for Phase Y (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any


def analyze_failures(run_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Extract failure-related info from run_summary."""
    if not isinstance(run_summary, dict):
        return {}
    return run_summary.get("failures") or {}


def detect_breakpoints(run_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Detect structural/consistency breakpoints (read-only)."""
    if not isinstance(run_summary, dict):
        return {}
    return run_summary.get("breakpoints") or {}


def compute_heal_signals(run_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute heal signals, non-destructive.
    Schema:
    {
      "failures": {...},
      "breakpoints": {...},
      "signals": {
          "severity": "low|med|high",
          "confidence": float,
          "notes": str
      }
    }
    """
    failures = analyze_failures(run_summary)
    breakpoints = detect_breakpoints(run_summary)
    sev = "low"
    if failures or breakpoints:
        sev = "med"
    if isinstance(failures, dict) and len(failures) > 5:
        sev = "high"
    confidence = 0.5
    if sev == "high":
        confidence = 0.8
    elif sev == "med":
        confidence = 0.6
    notes = "Phase Y self-heal signals (informational only; no automatic actions)."
    return {
        "failures": failures,
        "breakpoints": breakpoints,
        "signals": {
            "severity": sev,
            "confidence": float(confidence),
            "notes": notes,
        },
    }
