"""
Centralized logging configuration with context injection.

Provides consistent, structured logging across all phases with automatic
context injection (run_id, file_id, phase) for correlation.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from pipeline_common.observe.context import get_current_context


class ContextFilter(logging.Filter):
    """Filter that injects run context into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_current_context()
        record.run_id = ctx.run_id
        record.file_id = ctx.file_id or "-"
        record.phase = ctx.phase or "-"
        record.chunk_id = ctx.chunk_id or "-"
        record.engine = ctx.engine or "-"
        return True


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging output."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": getattr(record, "run_id", None),
            "file_id": getattr(record, "file_id", None),
            "phase": getattr(record, "phase", None),
        }

        # Add optional context fields if present
        if getattr(record, "chunk_id", "-") != "-":
            log_entry["chunk_id"] = record.chunk_id
        if getattr(record, "engine", "-") != "-":
            log_entry["engine"] = record.engine

        # Include extra fields from record
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for console output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Build context string
        ctx_parts = []
        if getattr(record, "run_id", None):
            ctx_parts.append(f"run={record.run_id}")
        if getattr(record, "file_id", "-") != "-":
            ctx_parts.append(f"file={record.file_id}")
        if getattr(record, "phase", "-") != "-":
            ctx_parts.append(f"phase={record.phase}")
        if getattr(record, "chunk_id", "-") != "-":
            ctx_parts.append(f"chunk={record.chunk_id}")

        ctx_str = f" [{' '.join(ctx_parts)}]" if ctx_parts else ""

        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Build message
        level = record.levelname
        if self.use_colors:
            color = self.COLORS.get(level, "")
            reset = self.COLORS["RESET"]
            level_str = f"{color}{level:8}{reset}"
        else:
            level_str = f"{level:8}"

        message = record.getMessage()

        # Add exception if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return f"{timestamp} {level_str} {record.name}{ctx_str}: {message}"


_configured = False


def configure_logging(
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    structured: bool = False,
    use_colors: bool = True,
) -> None:
    """
    Configure the root logger with consistent formatting.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        structured: If True, use JSON structured logging
        use_colors: If True, colorize console output
    """
    global _configured

    # Convert string level to int
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers
    root.handlers.clear()

    # Add context filter
    context_filter = ContextFilter()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.addFilter(context_filter)

    if structured:
        console.setFormatter(StructuredFormatter())
    else:
        console.setFormatter(ConsoleFormatter(use_colors=use_colors))

    root.addHandler(console)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level)
        file_handler.addFilter(context_filter)
        file_handler.setFormatter(StructuredFormatter())  # Always JSON for files
        root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with context injection.

    This is the primary entry point for obtaining a logger. Loggers obtained
    this way will automatically include run context (run_id, file_id, phase).

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger with context filter
    """
    logger = logging.getLogger(name)

    # Add context filter if not already present
    has_filter = any(isinstance(f, ContextFilter) for f in logger.filters)
    if not has_filter:
        logger.addFilter(ContextFilter())

    return logger
