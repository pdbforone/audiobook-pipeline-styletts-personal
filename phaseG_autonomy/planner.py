"""
Planning scaffold for Phase G autonomy.

This version stays inert unless explicitly invoked. It can read
`pipeline.json`, derive simple recommendations (e.g., smaller chunk
size or safer engine selection), and optionally persist them to a
lightweight recommendations file. No core pipeline behavior is changed
by default.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from autonomy.memory_store import query_recent, summarize_history, add_experience
except Exception:  # noqa: BLE001
    query_recent = None
    summarize_history = None
    add_experience = None
try:
    from autonomy.profiles import choose_overrides_from_profile, maybe_explore
except Exception:  # noqa: BLE001
    choose_overrides_from_profile = None
    maybe_explore = None
try:
    from autonomy.predictive import forecast_outcomes
except Exception:  # noqa: BLE001
    forecast_outcomes = None
try:
    from long_horizon.forecaster import build_forecast
except Exception:  # noqa: BLE001
    build_forecast = None


def _load_latest_fused_profile(history_dir: Path = Path(".pipeline/profile_history")) -> Optional[Dict[str, Any]]:
    """Load the most recent fused profile snapshot (if any)."""
    if not history_dir.exists():
        return None
    candidates = sorted(
        history_dir.glob("fused_profile_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def apply_profile_insights(base_recommendations: Dict[str, Any], fused_profile: Optional[Dict[str, Any]], config: Any) -> Dict[str, Any]:
    """
    Modify recommendation confidence or rationale using fused profiles.
    Does NOT change default behavior.
    Does NOT create new overrides automatically.
    Only adjusts:
      - confidence weighting
      - rationale explanations
    """
    if not fused_profile:
        return base_recommendations

    recommendations = dict(base_recommendations or {})
    profile_confidence = fused_profile.get("confidence")
    if isinstance(profile_confidence, (int, float)):
        recommendations["confidence"] = max(
            recommendations.get("confidence", 0.0),
            min(1.0, profile_confidence),
        )

    notes = recommendations.get("notes", "")
    rationale = fused_profile.get("rationale") or "Profile-informed weighting (no overrides applied)."
    recommendations["notes"] = f"{notes} {rationale}".strip()

    recommendations["profile_context"] = {
        "engine_preference": fused_profile.get("engine_preference"),
        "chunk_size_preference": fused_profile.get("chunk_size_preference"),
        "rewrite_policy_preference": fused_profile.get("rewrite_policy_preference"),
        "weights": fused_profile.get("weights"),
        "confidence": fused_profile.get("confidence"),
    }
    return recommendations


class AutonomyPlanner:
    """Minimal planner for autonomy workflows (opt-in)."""

    def __init__(
        self,
        *,
        mode: str = "disabled",
        output_path: Optional[Path] = None,
        recommendations_dir: Optional[Path] = None,
        policy_kernel_enabled: bool = False,
        autonomy_mode: Optional[str] = None,
    ) -> None:
        self.mode = mode
        self.output_path = output_path or Path(".pipeline") / "autonomy_recommendations.json"
        self.recommendations_dir = recommendations_dir or Path(".pipeline") / "staged_recommendations"
        self.policy_kernel_enabled = policy_kernel_enabled
        self.run_history: Optional[List[Dict[str, Any]]] = None
        self.autonomy_mode = autonomy_mode

    def propose_steps(self, goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return a list of proposed steps for the given goals."""
        return [{"goal": g, "action": "analyze", "status": "pending"} for g in goals]

    def update_plan(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Update internal plan state based on feedback."""
        return {"feedback": feedback, "status": "recorded"}

    def suggest_policy_update(self, pipeline_json: Path) -> Dict[str, Any]:
        """
        Inspect pipeline.json and propose conservative tuning.

        - If Phase 4 has failures recorded, suggest a small chunk-size reduction.
        - If fallback is used heavily, suggest switching to the secondary engine.
        """
        try:
            data = json.loads(Path(pipeline_json).read_text(encoding="utf-8"))
        except Exception:
            return {"status": "error", "reason": "unreadable_pipeline_json"}

        phase4 = (data.get("phase4") or {}).get("files", {})
        suggestions: Dict[str, Any] = {"status": "ok", "recommendations": []}
        for file_id, entry in phase4.items():
            failed = entry.get("failed_chunks") or []
            fallback_rate = entry.get("metrics", {}).get("fallback_rate")
            if failed:
                suggestions["recommendations"].append(
                    {
                        "file_id": file_id,
                        "phase": "phase3",
                        "chunk_size": {"delta_percent": -5.0, "reason": "auto_chunk_reduce"},
                    }
                )
            if isinstance(fallback_rate, (int, float)) and fallback_rate > 0.25:
                suggestions["recommendations"].append(
                    {
                        "file_id": file_id,
                        "phase": "phase4",
                        "engine": {"action": "prefer_secondary", "reason": "high_fallback_rate"},
                    }
                )

        if self.apply and suggestions["recommendations"]:
            self._write_recommendations(suggestions)
        return suggestions

    def _write_recommendations(self, payload: Dict[str, Any]) -> None:
        """Persist recommendations without mutating existing overrides."""
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            # Fail silently to avoid impacting runtime
            return

    def _write_staged(self, payload: Dict[str, Any]) -> Optional[Path]:
        """Write a staged recommendations file (recommend_only)."""
        try:
            self.recommendations_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = self.recommendations_dir / f"{ts}_recommendations.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return path
        except Exception:
            return None

    def recommend(
        self,
        *,
        benchmark_history: Path = Path(".pipeline/benchmark_history"),
        evaluator_summary: Path = Path(".pipeline/policy_runtime/last_run_summary.json"),
        tuning_overrides: Path = Path(".pipeline/tuning_overrides.json"),
        diagnostics_dir: Path = Path(".pipeline/diagnostics"),
        pipeline_json: Path = Path("../pipeline.json"),
        genre_config: Optional[Any] = None,
        experiments_cfg: Optional[Any] = None,
        autonomy_cfg: Optional[Any] = None,
        autonomy_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate recommendation JSON using the latest telemetry.

        Modes:
            - disabled: no output
            - recommend_only: write staged recommendations, do not apply
        """
        if self.mode == "disabled":
            return {"status": "disabled"}

        payload: Dict[str, Any] = {
            "planner_mode": self.mode,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "confidence": 0.5,
            "suggested_changes": {},
            "experiments": [],
            "sources": {
                "benchmark_history": str(benchmark_history),
                "evaluator_summary": str(evaluator_summary),
                "tuning_overrides": str(tuning_overrides),
            },
            "notes": "Planner never auto-applies changes.",
        }

        benchmark = self._load_latest(benchmark_history)
        evaluator = self._load_json(evaluator_summary)
        overrides = self._load_json(tuning_overrides)
        memory_insights = summarize_history() if summarize_history else None
        recent_memory = query_recent(limit=50) if query_recent else None
        diagnostics = self._load_latest(diagnostics_dir)
        latest_diag = self.load_latest_diagnostics()
        if latest_diag:
            diagnostics = latest_diag

        if evaluator and evaluator.get("metrics", {}).get("chunk_failure_rate", {}).get("rate") is not None:
            payload["suggested_changes"]["phase3.chunk_size"] = {
                "action": "reduce" if evaluator["metrics"]["chunk_failure_rate"]["rate"] > 0.05 else "maintain",
                "reason": "failure_rate_over_threshold" if evaluator["metrics"]["chunk_failure_rate"]["rate"] > 0.05 else "stable",
            }

        if benchmark and benchmark.get("recommendations", {}).get("engine_defaults"):
            payload["suggested_changes"]["phase4.engine_defaults"] = benchmark["recommendations"]["engine_defaults"]

        if overrides:
            payload["suggested_changes"]["overrides_snapshot"] = overrides

        payload["experiments"] = [
            "Try Kokoro for short fiction drafts",
            "Reduce chunk size for dense philosophy",
        ]
        # Limit experiments based on config (opt-in)
        if experiments_cfg and getattr(experiments_cfg, "enable", False):
            limit = getattr(experiments_cfg, "limit_per_run", 1)
            payload["experiments"] = payload["experiments"][: max(1, limit)]
        else:
            payload["experiments"] = []

        payload["insights_used"] = []
        if evaluator:
            payload["insights_used"].append("evaluator")
        if benchmark:
            payload["insights_used"].append("benchmarks")
        if memory_insights:
            payload["insights_used"].append("memory")
            payload["memory_summary"] = memory_insights
        if recent_memory:
            payload["memory_recent"] = recent_memory
        if diagnostics:
            payload["insights_used"].append("diagnostics")
            payload["diagnostics"] = diagnostics

        fused_profile = None
        if autonomy_cfg and getattr(autonomy_cfg, "enable_profile_fusion", False):
            fused_profile = _load_latest_fused_profile()
            if fused_profile:
                payload["insights_used"].append("profile_fusion")
                payload = apply_profile_insights(payload, fused_profile, autonomy_cfg)

        profiles_cfg = getattr(autonomy_cfg, "profiles", None) if autonomy_cfg else None
        profiles_enabled = bool(getattr(profiles_cfg, "enable", False)) if profiles_cfg else False
        active_profile = fused_profile if fused_profile else None
        if profiles_enabled and choose_overrides_from_profile and active_profile:
            cfg_dict = getattr(profiles_cfg, "__dict__", {}) if profiles_cfg else {}
            base_overrides = choose_overrides_from_profile(active_profile, cfg_dict)
            profile_overrides = maybe_explore(
                active_profile,
                base_overrides,
                cfg_dict,
            ) if maybe_explore else base_overrides

            if profile_overrides:
                safe_overrides = dict(profile_overrides)
                try:
                    if getattr(autonomy_cfg, "enable_policy_limits", False):
                        from autonomy.autonomy_policy import check_policy  # type: ignore

                        safe_overrides = check_policy(safe_overrides)
                except Exception:
                    safe_overrides = dict(profile_overrides)
                try:
                    if getattr(autonomy_cfg, "budget", None):
                        from autonomy.autonomy_budget import enforce_budget  # type: ignore

                        safe_overrides = enforce_budget({"suggested_changes": safe_overrides}, autonomy_cfg).get(
                            "suggested_changes", safe_overrides
                        )
                except Exception:
                    safe_overrides = safe_overrides

                payload["suggested_changes"].update(safe_overrides)
                payload["insights_used"].append("profile_overrides")
                base_conf = payload.get("confidence", 0.5)
                profile_conf = active_profile.get("confidence") if isinstance(active_profile, dict) else None
                if isinstance(profile_conf, (int, float)):
                    payload["confidence"] = min(1.0, max(base_conf, profile_conf))
                else:
                    payload["confidence"] = base_conf

        if getattr(autonomy_cfg, "enable_forecasting", False) and forecast_outcomes:
            try:
                history = []  # Planner remains recommend-only; forecasting is informational.
                trends_stub = {
                    "score_trend": {"slope": None},
                    "reward_trend": {"slope": None},
                    "anomaly_trend": {"slope": None},
                }
                payload["forecast"] = forecast_outcomes(history, trends_stub)
            except Exception:
                pass

        # Optional genre classification
        if genre_config and getattr(genre_config, "enable_classifier", False):
            sample_text = self._load_sample_text(pipeline_json)
            if sample_text:
                try:
                    from genre_classifier.genre_classifier import classify_text

                    genre_scores = classify_text(sample_text, use_llama=getattr(genre_config, "use_llama", False))
                    payload["genre"] = genre_scores
                    payload["insights_used"].append("genre")
                except Exception:
                    pass

        # Optional policy kernel consolidation
        if autonomy_cfg and getattr(autonomy_cfg, "policy_kernel_enabled", False):
            try:
                from autonomy.policy_kernel import combine_insights

                payload["policy_kernel"] = combine_insights(
                    evaluator_summary=evaluator,
                    diagnostics=diagnostics,
                    memory_summary=memory_insights,
                    benchmarks=benchmark,
                    genre_info=payload.get("genre") or {},
                )
            except Exception:
                if getattr(autonomy_cfg, "policy_kernel_debug", False):
                    payload["policy_kernel"] = {"error": "combine_insights_failed"}

        # Optional confidence calibration using run history
        try:
            if autonomy_cfg and getattr(autonomy_cfg, "enable_confidence_calibration", False):
                from autonomy.memory_store import load_run_history

                self.run_history = load_run_history(limit=10)
                payload["confidence"] = self.calibrate_confidence(payload, self.run_history or [])
        except Exception:
            pass

        if self.mode == "recommend_only":
            self._write_staged(payload)
            if add_experience:
                try:
                    add_experience("planner_action", {"status": "staged", "payload": payload})
                except Exception:
                    pass
        elif self.mode == "enforce":
            # Future: enforce by mutating overrides
            self._write_recommendations(payload)
            if add_experience:
                try:
                    add_experience("planner_action", {"status": "enforce", "payload": payload})
                except Exception:
                    pass

        # Autonomous-mode recommendation bundle (never auto-applied here)
        if autonomy_mode == "autonomous":
            payload["autonomous_recommendations"] = self.build_autonomous_recommendations(payload)

        return payload

    @staticmethod
    def load_latest_diagnostics() -> Dict[str, Any]:
        """Return the latest diagnostics JSON from .pipeline/diagnostics/."""
        diag_dir = Path(".pipeline") / "diagnostics"
        if not diag_dir.exists():
            return {}
        candidates = sorted(diag_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return {}
        try:
            return json.loads(candidates[0].read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _load_json(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _load_latest(self, directory: Path) -> Optional[Dict[str, Any]]:
        if not directory.exists():
            return None
        candidates = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return None
        return self._load_json(candidates[0])

    def _load_sample_text(self, pipeline_json: Path) -> Optional[str]:
        """Load a small text sample from pipeline.json if available."""
        try:
            data = self._load_json(pipeline_json)
        except Exception:
            data = None
        if not data:
            return None
        files = (data.get("phase2") or {}).get("files") or {}
        if not files:
            return None
        first_file = next(iter(files.values()))
        text = first_file.get("text") or ""
        return text[:8000] if text else None

    @staticmethod
    def calibrate_confidence(recommendations: Dict[str, Any], run_history: List[Dict[str, Any]]) -> float:
        """
        Modify the confidence score based on past success rates.
        Does not change recommendations, only adjusts confidence.
        """
        base_conf = float(recommendations.get("confidence", 0.5))
        if not run_history:
            return base_conf

        successes = 0
        total = 0
        for run in run_history:
            payload = run.get("payload") or {}
            eval_score = payload.get("evaluator", {}).get("score")
            if isinstance(eval_score, (int, float)):
                total += 1
                if eval_score >= 70:
                    successes += 1

        if total == 0:
            return base_conf

        success_rate = successes / total
        # Adjust confidence mildly based on success rate
        adjusted = base_conf + (success_rate - 0.5) * 0.2
        return max(0.0, min(1.0, adjusted))

    def build_autonomous_recommendations(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a recommendation set intended for autonomous mode.
        """
        return {
            "changes": {
                "phase3.chunk_size": insights.get("suggested_changes", {}).get("phase3.chunk_size"),
                "phase4.engine_preference": insights.get("suggested_changes", {}).get("phase4.engine_defaults"),
                "rewrite_policy": insights.get("suggested_changes", {}).get("rewrite_policy"),
            },
            "confidence": insights.get("confidence", 0.5),
            "change_magnitude": "small",
        }
