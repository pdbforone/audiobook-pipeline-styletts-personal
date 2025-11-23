"""
Log Parser - Extract structured failure information from pipeline logs.

Parses logs from:
- Phase 4 TTS (xtts_chunk.log)
- Phase 5 Enhancement
- Phase 6 Orchestrator

Extracts:
- Failure events with timestamps
- Error categories (OOM, timeout, etc.)
- Affected chunks/files
- Stack traces
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FailureEvent:
    """A detected failure in the pipeline."""

    category: str  # oom, timeout, truncation, quality, schema, io, unknown
    message: str
    timestamp: Optional[datetime] = None
    line_number: int = 0
    chunk_id: Optional[str] = None
    file_id: Optional[str] = None
    phase: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: str = "error"  # debug, info, warning, error, critical
    context: Dict[str, str] = field(default_factory=dict)


# Failure detection patterns
FAILURE_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
    "oom": [
        (r"out of memory", "Out of memory error"),
        (r"MemoryError", "Python memory error"),
        (r"CUDA out of memory", "GPU memory exhausted"),
        (r"OOM", "Out of memory"),
        (r"killed", "Process killed (likely OOM)"),
        (r"cannot allocate memory", "Memory allocation failed"),
    ],
    "timeout": [
        (r"timeout", "Operation timed out"),
        (r"timed out", "Timeout reached"),
        (r"exceeded \d+ seconds", "Time limit exceeded"),
        (r"too slow", "Processing too slow"),
        (r"RTF [\d.]+ > [\d.]+", "Real-time factor exceeded threshold"),
    ],
    "truncation": [
        (r"truncat", "Text truncation"),
        (r"text too long", "Text exceeds limit"),
        (r"max.*char.*exceeded", "Character limit exceeded"),
        (r"token limit", "Token limit reached"),
        (r"split required", "Text requires splitting"),
    ],
    "quality": [
        (r"silence detected", "Audio contains silence"),
        (r"no audio", "No audio generated"),
        (r"empty.*wav", "Empty audio file"),
        (r"corrupt", "Corrupted output"),
        (r"invalid.*audio", "Invalid audio format"),
        (r"WER.*\d+%", "Word error rate issue"),
        (r"duration mismatch", "Audio duration mismatch"),
    ],
    "schema": [
        (r"ValidationError", "Pydantic validation error"),
        (r"pydantic", "Schema validation issue"),
        (r"missing.*key", "Missing required field"),
        (r"invalid.*schema", "Schema mismatch"),
        (r"KeyError", "Missing dictionary key"),
    ],
    "io": [
        (r"FileNotFoundError", "File not found"),
        (r"PermissionError", "Permission denied"),
        (r"No such file", "Missing file"),
        (r"cannot open", "Failed to open file"),
        (r"disk.*full", "Disk space exhausted"),
        (r"IOError", "I/O error"),
    ],
}

# Log level patterns
LOG_LEVEL_PATTERN = re.compile(
    r"(DEBUG|INFO|WARNING|ERROR|CRITICAL)",
    re.IGNORECASE
)

# Timestamp patterns
TIMESTAMP_PATTERNS = [
    re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"),
    re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"),
    re.compile(r"(\d{2}:\d{2}:\d{2},\d{3})"),
]

# Chunk ID pattern
CHUNK_ID_PATTERN = re.compile(r"chunk[_-]?(\d+)", re.IGNORECASE)

# File ID pattern
FILE_ID_PATTERN = re.compile(r"file[_-]?id[=:\s]+([^\s,]+)", re.IGNORECASE)


class LogParser:
    """
    Parses pipeline logs to extract structured failure information.

    Usage:
        parser = LogParser()
        events = parser.parse_file("/path/to/orchestrator.log")
        for event in events:
            print(f"{event.category}: {event.message}")
    """

    def __init__(
        self,
        patterns: Optional[Dict[str, List[Tuple[str, str]]]] = None,
    ):
        self.patterns = patterns or FAILURE_PATTERNS
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str]]]:
        """Compile regex patterns for efficiency."""
        compiled = {}
        for category, pattern_list in self.patterns.items():
            compiled[category] = [
                (re.compile(pattern, re.IGNORECASE), desc)
                for pattern, desc in pattern_list
            ]
        return compiled

    def parse_file(
        self,
        log_path: Path,
        max_lines: int = 1000,
        tail: bool = True,
    ) -> List[FailureEvent]:
        """
        Parse a log file for failure events.

        Args:
            log_path: Path to log file
            max_lines: Maximum lines to read
            tail: If True, read last N lines; otherwise first N

        Returns:
            List of FailureEvent objects
        """
        log_path = Path(log_path)
        if not log_path.exists():
            logger.warning(f"Log file not found: {log_path}")
            return []

        try:
            lines = self._read_lines(log_path, max_lines, tail)
            return self.parse_lines(lines, source=str(log_path))
        except Exception as e:
            logger.error(f"Failed to parse log {log_path}: {e}")
            return []

    def _read_lines(
        self,
        path: Path,
        max_lines: int,
        tail: bool,
    ) -> List[str]:
        """Read lines from file, optionally from end."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if tail:
                # Read all and take last N
                all_lines = f.readlines()
                return all_lines[-max_lines:]
            else:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
                return lines

    def parse_lines(
        self,
        lines: List[str],
        source: str = "unknown",
    ) -> List[FailureEvent]:
        """
        Parse log lines for failure events.

        Args:
            lines: List of log lines
            source: Source identifier (e.g., file path)

        Returns:
            List of FailureEvent objects
        """
        events = []
        stack_buffer = []
        in_stack_trace = False

        for line_num, line in enumerate(lines, 1):
            # Check for stack trace continuation
            if in_stack_trace:
                if line.strip().startswith("File ") or line.strip().startswith("Traceback"):
                    stack_buffer.append(line.rstrip())
                    continue
                else:
                    in_stack_trace = False
                    if events:
                        events[-1].stack_trace = "\n".join(stack_buffer)
                    stack_buffer = []

            # Check for traceback start
            if "Traceback (most recent call last)" in line:
                in_stack_trace = True
                stack_buffer = [line.rstrip()]
                continue

            # Check for failure patterns
            event = self._match_line(line, line_num, source)
            if event:
                events.append(event)

        # Handle trailing stack trace
        if stack_buffer and events:
            events[-1].stack_trace = "\n".join(stack_buffer)

        return events

    def _match_line(
        self,
        line: str,
        line_num: int,
        source: str,
    ) -> Optional[FailureEvent]:
        """Check if line matches any failure pattern."""
        for category, patterns in self._compiled_patterns.items():
            for pattern, description in patterns:
                if pattern.search(line):
                    return FailureEvent(
                        category=category,
                        message=line.rstrip(),
                        timestamp=self._extract_timestamp(line),
                        line_number=line_num,
                        chunk_id=self._extract_chunk_id(line),
                        file_id=self._extract_file_id(line),
                        phase=self._extract_phase(source),
                        severity=self._extract_severity(line),
                        context={"source": source, "pattern": description},
                    )
        return None

    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        for pattern in TIMESTAMP_PATTERNS:
            match = pattern.search(line)
            if match:
                try:
                    ts_str = match.group(1)
                    # Try common formats
                    for fmt in [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S",
                        "%H:%M:%S,%f",
                    ]:
                        try:
                            return datetime.strptime(ts_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass
        return None

    def _extract_chunk_id(self, line: str) -> Optional[str]:
        """Extract chunk ID from log line."""
        match = CHUNK_ID_PATTERN.search(line)
        return f"chunk_{int(match.group(1)):04d}" if match else None

    def _extract_file_id(self, line: str) -> Optional[str]:
        """Extract file ID from log line."""
        match = FILE_ID_PATTERN.search(line)
        return match.group(1) if match else None

    def _extract_phase(self, source: str) -> Optional[str]:
        """Infer phase from source path."""
        source_lower = source.lower()
        if "phase4" in source_lower or "tts" in source_lower:
            return "phase4"
        if "phase5" in source_lower or "enhancement" in source_lower:
            return "phase5"
        if "phase6" in source_lower or "orchestrat" in source_lower:
            return "phase6"
        if "phase3" in source_lower or "chunk" in source_lower:
            return "phase3"
        return None

    def _extract_severity(self, line: str) -> str:
        """Extract log level from line."""
        match = LOG_LEVEL_PATTERN.search(line)
        if match:
            return match.group(1).lower()
        # Infer from keywords
        if any(w in line.lower() for w in ["error", "exception", "fail"]):
            return "error"
        if any(w in line.lower() for w in ["warning", "warn"]):
            return "warning"
        return "info"

    def get_summary(self, events: List[FailureEvent]) -> Dict[str, int]:
        """Get failure count by category."""
        summary: Dict[str, int] = {}
        for event in events:
            summary[event.category] = summary.get(event.category, 0) + 1
        return summary

    def get_affected_chunks(self, events: List[FailureEvent]) -> List[str]:
        """Get list of affected chunk IDs."""
        return list(set(
            e.chunk_id for e in events
            if e.chunk_id is not None
        ))
