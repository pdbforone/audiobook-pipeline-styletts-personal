"""
Llama Self-Review agent (opt-in, reflective only).
Produces structured reflections about a run without altering behavior.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .llama_base import LlamaAgent

logger = logging.getLogger(__name__)


class LlamaSelfReview:
    """Reflective LLM agent for post-run analysis (opt-in)."""

    def __init__(self) -> None:
        try:
            self.agent = LlamaAgent()
        except Exception as exc:
            logger.warning("LlamaSelfReview: LlamaAgent unavailable: %s", exc)
            self.agent = None

    def analyze_run(
        self,
        evaluator_summary: Dict[str, Any],
        diagnostics_summary: Dict[str, Any],
        memory_summary: Dict[str, Any],
        planner_recs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Uses Llama to generate reflective reasoning about the run:
        - what worked
        - what failed
        - hypotheses
        - suggested next steps
        Returns a structured JSON-serializable dict.
        """
        prompt = (
            "You are a reflection agent. Summarize the run with insights only.\n"
            "Focus on what worked, what failed, hypotheses, and next steps.\n"
            "Do NOT propose code patches or config changes.\n\n"
            f"Evaluator summary:\n{evaluator_summary}\n\n"
            f"Diagnostics:\n{diagnostics_summary}\n\n"
            f"Memory summary:\n{memory_summary}\n\n"
            f"Planner recommendations:\n{planner_recs}\n\n"
            "Return JSON with keys: worked (list), failed (list), hypotheses (list), next_steps (list), confidence (0-1), notes."
        )

        if not self.agent:
            return {
                "worked": [],
                "failed": [],
                "hypotheses": [],
                "next_steps": [],
                "confidence": 0.0,
                "notes": "LLM not available; reflection stub only.",
            }

        try:
            response = self.agent.query_json(prompt, max_tokens=400, temperature=0.3)
        except Exception as exc:  # noqa: BLE001
            return {
                "worked": [],
                "failed": [],
                "hypotheses": [f"LLM unavailable: {exc}"],
                "next_steps": [],
                "confidence": 0.0,
                "notes": "Reflection failed; no action taken.",
            }

        return {
            "worked": response.get("worked", []) if isinstance(response, dict) else [],
            "failed": response.get("failed", []) if isinstance(response, dict) else [],
            "hypotheses": response.get("hypotheses", []) if isinstance(response, dict) else [],
            "next_steps": response.get("next_steps", []) if isinstance(response, dict) else [],
            "confidence": float(response.get("confidence", 0.0)) if isinstance(response, dict) else 0.0,
            "notes": response.get("notes", "Reflection complete") if isinstance(response, dict) else "Reflection complete",
        }
