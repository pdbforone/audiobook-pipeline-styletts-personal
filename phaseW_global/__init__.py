"""Phase W: Global Consistency Layer (opt-in, read-only)."""

from .schema_linter import lint_schemas
from .cross_phase_consistency import analyze_consistency
from .global_analyzer import global_analysis
from .w_reporter import write_phaseW_report

__all__ = [
    "lint_schemas",
    "analyze_consistency",
    "global_analysis",
    "write_phaseW_report",
]
