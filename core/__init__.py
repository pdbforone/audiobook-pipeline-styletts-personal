"""
Core module - Shared infrastructure for the audiobook pipeline.

This module provides:
- Engine capability registry
- Benchmarking utilities
- Adaptive chunking
- Common data structures
"""

from .engine_registry import EngineRegistry, EngineCapabilities, TextLimits

__all__ = [
    "EngineRegistry",
    "EngineCapabilities",
    "TextLimits",
]
