"""Phase U: Unified Safety-Integrity Layer (opt-in, read-only)."""

from .integrity_kernel import evaluate_integrity
from .signal_hub import collect_signals
from .consistency_unifier import unify
from .integrity_reporter import write_integrity_report

__all__ = [
    "evaluate_integrity",
    "collect_signals",
    "unify",
    "write_integrity_report",
]
