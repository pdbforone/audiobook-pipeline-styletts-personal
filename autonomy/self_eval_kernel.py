"""Phase Q Self-Evaluation Kernel (opt-in, read-only, non-destructive)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class SelfEvalInput:
    run_summary: Dict = field(default_factory=dict)
    evaluator_summary: Dict = field(default_factory=dict)
    diagnostics_summary: Dict = field(default_factory=dict)
    memory_profile: Dict = field(default_factory=dict)
    stability_profile: Dict = field(default_factory=dict)
    reward_summary: Dict = field(default_factory=dict)
    autonomy_journal: Dict = field(default_factory=dict)
    metadata_summary: Dict = field(default_factory=dict)


@dataclass
class SelfEvalResult:
    overall_rating: float
    verdict: str
    dimensions: Dict[str, float]
    reasons: List[str]
    run_id: Optional[str]
    timestamp: str
    source: str = "phaseQ_self_eval"


class SelfEvalKernel:
    """Pure, heuristic self-evaluation kernel."""

    def build_input(
        self,
        run_summary: Optional[dict] = None,
        evaluator_summary: Optional[dict] = None,
        diagnostics_summary: Optional[dict] = None,
        memory_profile: Optional[dict] = None,
        stability_profile: Optional[dict] = None,
        reward_summary: Optional[dict] = None,
        autonomy_journal: Optional[dict] = None,
        metadata_summary: Optional[dict] = None,
    ) -> SelfEvalInput:
        return SelfEvalInput(
            run_summary=run_summary or {},
            evaluator_summary=evaluator_summary or {},
            diagnostics_summary=diagnostics_summary or {},
            memory_profile=memory_profile or {},
            stability_profile=stability_profile or {},
            reward_summary=reward_summary or {},
            autonomy_journal=autonomy_journal or {},
            metadata_summary=metadata_summary or {},
        )

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _score_dimension(self, name: str, signals: Dict) -> float:
        # Lightweight heuristics based on available signals
        if name == "audio_quality":
            return self._clamp(signals.get("audio_quality", 0.8))
        if name == "stability":
            return self._clamp(signals.get("stability", 0.75))
        if name == "speed":
            return self._clamp(signals.get("speed", 0.7))
        if name == "robustness":
            return self._clamp(signals.get("robustness", 0.7))
        if name == "autonomy_safety":
            return self._clamp(signals.get("autonomy_safety", 0.9))
        return 0.5

    def rate_run(self, input: SelfEvalInput, run_id: Optional[str] = None) -> SelfEvalResult:
        signals = {
            "audio_quality": input.evaluator_summary.get("audio_quality", 0.8),
            "stability": input.stability_profile.get("stability_score", 0.75),
            "speed": input.run_summary.get("speed_score", 0.7),
            "robustness": input.diagnostics_summary.get("robustness", 0.7),
            "autonomy_safety": input.autonomy_journal.get("safety", 0.9),
        }

        dimensions = {
            name: self._score_dimension(name, signals) for name in [
                "audio_quality",
                "stability",
                "speed",
                "robustness",
                "autonomy_safety",
            ]
        }
        present_scores = list(dimensions.values())
        overall = sum(present_scores) / len(present_scores) if present_scores else 0.0
        if overall >= 0.8:
            verdict = "ok"
        elif overall >= 0.5:
            verdict = "needs_attention"
        else:
            verdict = "critical"

        reasons: List[str] = []
        if verdict == "ok":
            reasons.append("Run indicators within healthy thresholds.")
        elif verdict == "needs_attention":
            reasons.append("Some metrics below target; consider review.")
        else:
            reasons.append("Multiple metrics below target; investigate stability/performance.")

        ts = datetime.utcnow().isoformat()
        return SelfEvalResult(
            overall_rating=overall,
            verdict=verdict,
            dimensions=dimensions,
            reasons=reasons,
            run_id=run_id,
            timestamp=ts,
        )

    def explain(self, result: SelfEvalResult) -> str:
        prefix = {
            "ok": "Run appears healthy.",
            "needs_attention": "Run needs attention.",
            "critical": "Run exhibits critical issues.",
        }.get(result.verdict, "Run status unclear.")
        top_reasons = "; ".join(result.reasons[:3])
        return f"{prefix} Reasons: {top_reasons}"

    def to_json(self, result: SelfEvalResult) -> Dict:
        return {
            "run_id": result.run_id,
            "timestamp": result.timestamp,
            "overall_rating": result.overall_rating,
            "verdict": result.verdict,
            "dimensions": result.dimensions,
            "reasons": result.reasons,
            "explanation": self.explain(result),
            "source": result.source,
        }
