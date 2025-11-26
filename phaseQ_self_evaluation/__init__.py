"""Phase Q: Self-Evaluation Layer (opt-in, observational only)."""

__all__ = ["compute_metrics", "write_report"]

from .metrics_engine import compute_metrics
from .report_writer import write_report
