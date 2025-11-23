"""
Self-Repair Module - Automated failure detection and recovery.

This module provides:
- Log parsing for failure extraction
- Pattern-based root cause detection
- Patch suggestion and staging
- Repair strategies for failed chunks

Key principle: NEVER auto-apply fixes. All changes require human approval.
"""

from .log_parser import LogParser, FailureEvent
from .repair_loop import RepairLoop, DeadChunkRepair

__all__ = [
    "LogParser",
    "FailureEvent",
    "RepairLoop",
    "DeadChunkRepair",
]
