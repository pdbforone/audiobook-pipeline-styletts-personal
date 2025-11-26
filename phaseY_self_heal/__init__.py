"""Phase Y: Self-Healing Layer (opt-in, read-only suggestions)."""

from .heal_kernel import analyze_failures, detect_breakpoints, compute_heal_signals
from .heal_classifier import classify
from .heal_suggester import suggest_corrections
from .heal_reporter import write_heal_report

__all__ = [
    "analyze_failures",
    "detect_breakpoints",
    "compute_heal_signals",
    "classify",
    "suggest_corrections",
    "write_heal_report",
]
