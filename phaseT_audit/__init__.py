"""Phase T: Audit layer (opt-in, read-only)."""

from .audit_kernel import evaluate_run
from .eval_synthesizer import synthesize_evaluation
from .risk_classifier import classify
from .audit_reporter import write_audit_report
from .schema import EXPECTED_SCHEMAS

__all__ = [
    "evaluate_run",
    "synthesize_evaluation",
    "classify",
    "write_audit_report",
    "EXPECTED_SCHEMAS",
]
