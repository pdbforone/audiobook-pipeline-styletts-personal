"""Phase Q: Self-evaluation layer (opt-in, informational only)."""

from .self_eval_kernel import score_dimensions, generate_overall_rating, evaluate_run
from .cross_phase_fusion import fuse_phase_outputs
from .rating_explainer import explain_rating
from .self_eval_reporter import write_self_eval_report

__all__ = [
    "score_dimensions",
    "generate_overall_rating",
    "evaluate_run",
    "fuse_phase_outputs",
    "explain_rating",
    "write_self_eval_report",
]
