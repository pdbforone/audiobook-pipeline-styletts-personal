"""Shared schemas for Phase T audit layer."""

from __future__ import annotations

EXPECTED_SCHEMAS = {
    "kernel_output": {
        "dimensions": {
            "tts_quality": float,
            "chunk_flow": float,
            "reasoning_clarity": float,
            "engine_stability": float,
        },
        "issues": list,
        "confidence": float,
        "notes": str,
    },
    "synthesized_output": {
        "evaluation_summary": str,
        "dimension_summaries": {
            "tts_quality": str,
            "chunk_flow": str,
            "reasoning_clarity": str,
            "engine_stability": str,
        },
        "combined_confidence": float,
    },
    "risk_output": {
        "risk_level": str,
        "signals": {
            "tts": str,
            "engine": str,
            "chunking": str,
            "llm": str,
        },
        "confidence": float,
        "notes": str,
    },
}
