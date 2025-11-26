"""Phase T: Global consistency layer (opt-in, read-only)."""

from .schema_registry import get_expected_schema
from .consistency_checker import check_consistency
from .drift_monitor import detect_system_drift
from .health_reporter import write_consistency_report

__all__ = [
    "get_expected_schema",
    "check_consistency",
    "detect_system_drift",
    "write_consistency_report",
]
