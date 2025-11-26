"""Phase Q: meta-evaluator (opt-in, informational only)."""

from __future__ import annotations

from typing import Dict, Any, List


def evaluate_meta(self_evaluation_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate research, forecasting, stability, planner, and reward signals into a meta score.
    Purely evaluative; never mutates upstream state.
    """
    inputs = self_evaluation_inputs or {}
    research_present = bool(inputs.get("research"))
    forecasting_present = bool(inputs.get("forecasting"))
    stability_present = bool(inputs.get("stability"))
    rewards_present = bool(inputs.get("rewards"))
    planner_present = bool(inputs.get("planner"))

    signals_used = {
        "research": research_present,
        "forecasting": forecasting_present,
        "stability": stability_present,
        "rewards": rewards_present,
        "planner": planner_present,
    }

    score_components: List[float] = []
    for flag in signals_used.values():
        score_components.append(0.2 if flag else 0.0)
    meta_score = float(sum(score_components))

    reasoning_summary = "Meta-evaluation derived from available research, forecasting, stability, rewards, and planner signals."
    concerns: List[str] = []
    recommended_focus: List[str] = []

    if not research_present:
        concerns.append("Research signals unavailable.")
    if not forecasting_present:
        concerns.append("Forecasting signals unavailable.")
    if not stability_present:
        concerns.append("Stability signals unavailable.")
    if not rewards_present:
        concerns.append("Reward history unavailable.")
    if not planner_present:
        concerns.append("Planner decisions unavailable.")

    if concerns:
        recommended_focus.append("Increase signal coverage for missing inputs.")

    return {
        "meta_score": meta_score,
        "signals_used": signals_used,
        "reasoning_summary": reasoning_summary,
        "concerns": concerns,
        "recommended_focus": recommended_focus,
    }
