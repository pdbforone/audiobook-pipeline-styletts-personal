"""Tests for the observe module."""

import logging
import time
import pytest

from pipeline_common.observe import (
    get_logger,
    configure_logging,
    with_context,
    get_current_context,
    set_context,
    clear_context,
    RunContext,
    timed,
    Timer,
    get_metrics,
)


class TestRunContext:
    """Tests for RunContext."""

    def test_default_context(self):
        clear_context()
        ctx = get_current_context()
        assert ctx.run_id is not None
        assert len(ctx.run_id) == 8  # UUID[:8]
        assert ctx.file_id is None
        assert ctx.phase is None

    def test_set_context(self):
        ctx = RunContext(run_id="test123", file_id="book1", phase="phase4")
        set_context(ctx)
        current = get_current_context()
        assert current.run_id == "test123"
        assert current.file_id == "book1"
        assert current.phase == "phase4"
        clear_context()

    def test_with_context_scoped(self):
        clear_context()
        original = get_current_context()
        original_run_id = original.run_id

        with with_context(file_id="book1", phase="phase4") as ctx:
            assert ctx.file_id == "book1"
            assert ctx.phase == "phase4"
            assert ctx.run_id == original_run_id  # Preserved

        # After context, should revert
        after = get_current_context()
        assert after.file_id is None
        assert after.phase is None

    def test_context_as_dict(self):
        ctx = RunContext(run_id="abc123", file_id="book1", phase="phase3")
        d = ctx.as_dict()
        assert d["run_id"] == "abc123"
        assert d["file_id"] == "book1"
        assert d["phase"] == "phase3"
        assert "chunk_id" not in d  # None values excluded

    def test_context_copy(self):
        ctx = RunContext(run_id="abc", file_id="book1")
        copied = ctx.copy(phase="phase5")
        assert copied.run_id == "abc"
        assert copied.file_id == "book1"
        assert copied.phase == "phase5"


class TestLogger:
    """Tests for logging functionality."""

    def test_get_logger(self):
        logger = get_logger("test.module")
        assert logger.name == "test.module"

    def test_logger_includes_context(self, caplog):
        configure_logging(level=logging.DEBUG)
        logger = get_logger("test.context")

        with with_context(file_id="testbook", phase="phase1"):
            with caplog.at_level(logging.INFO):
                logger.info("Test message")

        # Context should be in the log record
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert hasattr(record, "file_id")
        assert record.file_id == "testbook"


class TestMetrics:
    """Tests for metrics functionality."""

    def setup_method(self):
        get_metrics().clear()

    def test_timer_context_manager(self):
        with Timer("test_operation", log_result=False) as t:
            time.sleep(0.01)

        assert t.duration >= 0.01
        stats = get_metrics().get_stats("test_operation")
        assert stats["count"] == 1

    def test_timed_decorator(self):
        @timed("decorated_func", log_result=False)
        def slow_function():
            time.sleep(0.01)
            return "done"

        result = slow_function()
        assert result == "done"

        stats = get_metrics().get_stats("decorated_func")
        assert stats["count"] == 1
        assert stats["mean_seconds"] >= 0.01

    def test_counter(self):
        registry = get_metrics()
        registry.increment("chunks_processed")
        registry.increment("chunks_processed")
        registry.increment("chunks_failed")

        counters = registry.get_counters()
        assert counters["chunks_processed"] == 2
        assert counters["chunks_failed"] == 1

    def test_gauge(self):
        registry = get_metrics()
        registry.set_gauge("memory_mb", 512.5)
        registry.set_gauge("cpu_percent", 45.2)

        gauges = registry.get_gauges()
        assert gauges["memory_mb"] == 512.5
        assert gauges["cpu_percent"] == 45.2

    def test_summary(self):
        registry = get_metrics()

        with Timer("op1", log_result=False):
            time.sleep(0.01)
        with Timer("op1", log_result=False):
            time.sleep(0.01)

        registry.increment("counter1", 5)
        registry.set_gauge("gauge1", 100.0)

        summary = registry.get_summary()
        assert "timings" in summary
        assert "op1" in summary["timings"]
        assert summary["timings"]["op1"]["count"] == 2
        assert summary["counters"]["counter1"] == 5
        assert summary["gauges"]["gauge1"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
