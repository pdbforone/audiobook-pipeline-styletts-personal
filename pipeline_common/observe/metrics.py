"""
Metrics collection and timing utilities.

Provides decorator-based timing, metrics aggregation, and a registry
for tracking pipeline performance.
"""

import time
import functools
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, TypeVar, Union
from collections import defaultdict

from pipeline_common.observe.context import get_current_context
from pipeline_common.observe.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class TimingRecord:
    """Record of a single timing measurement."""

    name: str
    duration_seconds: float
    run_id: Optional[str] = None
    file_id: Optional[str] = None
    phase: Optional[str] = None
    success: bool = True
    timestamp: float = field(default_factory=time.time)


class Timer:
    """
    Context manager for timing code blocks.

    Usage:
        with Timer("chunk_processing") as t:
            process_chunk()
        print(f"Took {t.duration:.2f}s")
    """

    def __init__(self, name: str, log_result: bool = True):
        self.name = name
        self.log_result = log_result
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration: float = 0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time

        ctx = get_current_context()
        success = exc_type is None

        # Record the timing
        record = TimingRecord(
            name=self.name,
            duration_seconds=self.duration,
            run_id=ctx.run_id,
            file_id=ctx.file_id,
            phase=ctx.phase,
            success=success,
        )
        _global_registry.record(record)

        if self.log_result:
            level = "info" if success else "warning"
            getattr(logger, level)(
                f"{self.name} completed in {self.duration:.3f}s",
                extra={"duration": self.duration, "success": success},
            )


def timed(name: Optional[str] = None, log_result: bool = True) -> Callable[[F], F]:
    """
    Decorator to time function execution.

    Args:
        name: Metric name (defaults to function name)
        log_result: Whether to log the timing result

    Usage:
        @timed("chunk_synthesis")
        def synthesize_chunk(chunk_id: str) -> bytes:
            ...
    """
    def decorator(func: F) -> F:
        metric_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with Timer(metric_name, log_result=log_result):
                return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


class MetricsRegistry:
    """
    Thread-safe registry for collecting and aggregating metrics.

    Tracks timing records, counters, and gauges for pipeline observability.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._timings: List[TimingRecord] = []
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}

    def record(self, timing: TimingRecord) -> None:
        """Record a timing measurement."""
        with self._lock:
            self._timings.append(timing)

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        with self._lock:
            self._gauges[name] = value

    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregated statistics for a metric.

        Args:
            name: Metric name to filter by (None for all)

        Returns:
            Dictionary with count, total, mean, min, max, success_rate
        """
        with self._lock:
            if name:
                records = [t for t in self._timings if t.name == name]
            else:
                records = self._timings.copy()

        if not records:
            return {
                "count": 0,
                "total_seconds": 0,
                "mean_seconds": 0,
                "min_seconds": 0,
                "max_seconds": 0,
                "success_rate": 0,
            }

        durations = [r.duration_seconds for r in records]
        successes = sum(1 for r in records if r.success)

        return {
            "count": len(records),
            "total_seconds": sum(durations),
            "mean_seconds": sum(durations) / len(durations),
            "min_seconds": min(durations),
            "max_seconds": max(durations),
            "success_rate": successes / len(records) if records else 0,
        }

    def get_counters(self) -> Dict[str, int]:
        """Get all counter values."""
        with self._lock:
            return dict(self._counters)

    def get_gauges(self) -> Dict[str, float]:
        """Get all gauge values."""
        with self._lock:
            return dict(self._gauges)

    def get_summary(self) -> Dict[str, Any]:
        """Get full metrics summary."""
        with self._lock:
            # Group timings by name
            by_name: Dict[str, List[TimingRecord]] = defaultdict(list)
            for t in self._timings:
                by_name[t.name].append(t)

        summary = {
            "timings": {},
            "counters": self.get_counters(),
            "gauges": self.get_gauges(),
        }

        for name, records in by_name.items():
            durations = [r.duration_seconds for r in records]
            successes = sum(1 for r in records if r.success)
            summary["timings"][name] = {
                "count": len(records),
                "total": sum(durations),
                "mean": sum(durations) / len(durations),
                "success_rate": successes / len(records),
            }

        return summary

    def clear(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._timings.clear()
            self._counters.clear()
            self._gauges.clear()


# Global metrics registry
_global_registry = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    """Get the global metrics registry."""
    return _global_registry
