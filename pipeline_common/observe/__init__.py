"""
Observability Layer - Unified logging, metrics, and tracing for the pipeline.

Design Principles:
- Zero coupling to business logic (decorator-based instrumentation)
- Consistent structured logging across all phases
- Context propagation for correlation (run_id, file_id, phase)
- Optional JSON output for machine parsing

Usage:
    from pipeline_common.observe import get_logger, with_context, timed

    logger = get_logger(__name__)

    @timed("chunk_processing")
    def process_chunk(chunk_id: str) -> dict:
        with with_context(file_id="book1", phase="phase4"):
            logger.info("Processing chunk", extra={"chunk_id": chunk_id})
            ...
"""

from pipeline_common.observe.logger import get_logger, configure_logging
from pipeline_common.observe.context import (
    RunContext,
    with_context,
    get_current_context,
    set_context,
    clear_context,
)
from pipeline_common.observe.metrics import (
    timed,
    Timer,
    MetricsRegistry,
    get_metrics,
)

__all__ = [
    # Logger
    "get_logger",
    "configure_logging",
    # Context
    "RunContext",
    "with_context",
    "get_current_context",
    "set_context",
    "clear_context",
    # Metrics
    "timed",
    "Timer",
    "MetricsRegistry",
    "get_metrics",
]
