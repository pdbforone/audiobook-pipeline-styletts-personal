"""Evaluation synthesizer for Phase T (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict


def synthesize_evaluation(kernel_output: Dict, metadata: Dict) -> Dict:
    """
    Return schema:
    {
      "evaluation_summary": str,
      "dimension_summaries": {
        "tts_quality": str,
        "chunk_flow": str,
        "reasoning_clarity": str,
        "engine_stability": str
      },
      "combined_confidence": float
    }
    """
    ko = kernel_output or {}
    dims = ko.get("dimensions") or {}
    summaries = {
        "tts_quality": f"TTS quality at {dims.get('tts_quality', 0.0):.2f}",
        "chunk_flow": f"Chunk flow at {dims.get('chunk_flow', 0.0):.2f}",
        "reasoning_clarity": f"Reasoning clarity at {dims.get('reasoning_clarity', 0.0):.2f}",
        "engine_stability": f"Engine stability at {dims.get('engine_stability', 0.0):.2f}",
    }
    combined_confidence = float(ko.get("confidence", 0.0))
    return {
        "evaluation_summary": "Synthesized evaluation (Phase T, opt-in).",
        "dimension_summaries": summaries,
        "combined_confidence": combined_confidence,
    }
