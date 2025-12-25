"""
LlamaDiagnostics - generates run diagnostics without altering configs.

Produces structured observations (patterns, anomalies, hypotheses) based on:
- Evaluator summaries
- Memory summaries
- Benchmark reports
"""

from __future__ import annotations

from typing import Any, Dict

from .llama_base import LlamaAgent


class LlamaDiagnostics(LlamaAgent):
    """Diagnostics agent (opt-in) for post-run analysis."""

    def analyze_runs(
        self,
        evaluator_summary: Dict[str, Any],
        memory_summary: Dict[str, Any],
        benchmarks: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Produce a diagnostic explanation of patterns, trends, anomalies,
        and likely root causes. Should generate hypotheses, not config changes.
        """
        prompt = (
            "You are a diagnostics agent. Analyze the provided summaries and produce observations only.\n"
            "Do NOT suggest config changes or patches. Focus on patterns, anomalies, and hypotheses.\n\n"
            f"Evaluator summary:\n{evaluator_summary}\n\n"
            f"Memory summary:\n{memory_summary}\n\n"
            f"Benchmark report:\n{benchmarks}\n\n"
            "Return JSON with keys: diagnostics {patterns, anomalies, hypotheses, supporting_evidence}, "
            "confidence (0-1), notes. Keep suggestions high-level and non-invasive."
        )

        try:
            response = self.query_json(prompt, max_tokens=400, temperature=0.3)
        except Exception as exc:  # noqa: BLE001
            return {
                "diagnostics": {
                    "patterns": [],
                    "anomalies": [],
                    "hypotheses": [f"LLM unavailable: {exc}"],
                    "supporting_evidence": {},
                },
                "confidence": 0.0,
                "notes": "No config changed. Diagnostics only.",
            }

        # Normalize output
        diagnostics = response.get("diagnostics") if isinstance(response, dict) else {}
        return {
            "diagnostics": diagnostics
            if isinstance(diagnostics, dict)
            else {
                "patterns": [],
                "anomalies": [],
                "hypotheses": [],
                "supporting_evidence": {},
            },
            "confidence": float(response.get("confidence", 0.0)) if isinstance(response, dict) else 0.0,
            "notes": response.get("notes", "No config changed. Diagnostics only.") if isinstance(response, dict) else "No config changed. Diagnostics only.",
        }
