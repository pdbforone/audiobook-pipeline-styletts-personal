"""Phase Z: Meta-level pipeline-of-pipelines diagnostics (opt-in, read-only)."""

from .meta_kernel import analyze_full_pipeline, collect_phase_states, build_meta_summary
from .invariant_checker import check_invariants
from .dependency_scanner import scan_dependencies
from .phase_health_summarizer import summarize_health
from .meta_reporter import write_meta_report

__all__ = [
    "analyze_full_pipeline",
    "collect_phase_states",
    "build_meta_summary",
    "check_invariants",
    "scan_dependencies",
    "summarize_health",
    "write_meta_report",
]
