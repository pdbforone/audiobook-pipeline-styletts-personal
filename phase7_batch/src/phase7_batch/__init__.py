"""
Phase 7: Batch Processing for Audiobook Pipeline

This phase coordinates batch processing of multiple audiobook files by calling
Phase 6 orchestrator for each file in parallel with CPU monitoring.
"""

__version__ = "0.1.0"

from .models import BatchConfig, BatchMetadata, BatchSummary

__all__ = ["BatchConfig", "BatchMetadata", "BatchSummary"]
