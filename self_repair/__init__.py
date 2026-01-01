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

# Unified error categories used across the pipeline
# These categories are used by:
# - LogParser for log analysis
# - ErrorRegistry for failure tracking
# - LlamaReasoner for AI failure analysis
# - PolicyAdvisor for recommendations
ERROR_CATEGORIES = (
    "oom",        # Out of memory errors
    "timeout",    # Operation timeouts
    "truncation", # Text too long / needs splitting
    "quality",    # Audio quality issues (silence, WER)
    "schema",     # Validation / data structure errors
    "io",         # File system / I/O errors
    "unknown",    # Unclassified failures
)

# Human-readable descriptions for error categories
ERROR_CATEGORY_DESCRIPTIONS = {
    "oom": "Out of Memory - Process ran out of RAM or GPU memory",
    "timeout": "Timeout - Operation exceeded time limit",
    "truncation": "Truncation - Text too long for processing",
    "quality": "Quality Issue - Audio silence, corruption, or WER problems",
    "schema": "Schema Error - Data validation or structure mismatch",
    "io": "I/O Error - File not found, permissions, or disk issues",
    "unknown": "Unknown - Unclassified failure requiring investigation",
}

__all__ = [
    "LogParser",
    "FailureEvent",
    "RepairLoop",
    "DeadChunkRepair",
    "ERROR_CATEGORIES",
    "ERROR_CATEGORY_DESCRIPTIONS",
]
