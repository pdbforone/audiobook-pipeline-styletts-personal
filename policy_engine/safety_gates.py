"""
Safety Gates for PolicyEngine

Distilled from Phase AA/AB: Prevents unsafe autonomous decisions.
Checks readiness, drift, stability, and budget constraints before allowing
autonomous mode to make changes.
"""

from __future__ import annotations

from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class SafetyGates:
    """
    Unified safety checking for autonomous operations.

    Prevents PolicyEngine from making unsafe adjustments by checking:
    - Readiness (enough data to make decisions)
    - Drift (unexpected behavior changes)
    - Stability (consistent performance)
    - Budget constraints (limits on changes)
    """

    def __init__(self):
        self.min_runs_for_autonomy = 5
        self.max_failure_rate = 0.35
        self.max_drift_percent = 25.0

    def check_gates(
        self,
        run_summary: Dict[str, Any],
        learning_mode: str = "observe"
    ) -> Dict[str, Any]:
        """
        Check all safety gates.

        Returns:
            {
                "allow_autonomy": bool,
                "blocked_reasons": list[str],
                "downgrade_to_supervised": bool,
                "warnings": list[str]
            }
        """
        blocked_reasons: List[str] = []
        warnings: List[str] = []
        downgrade = False

        # Gate 1: Readiness check
        readiness = self._check_readiness(run_summary)
        if not readiness["ready"]:
            blocked_reasons.append("insufficient_data")
            downgrade = True
            logger.warning(f"Safety gate: {readiness['reason']}")

        # Gate 2: Failure rate check
        failure_check = self._check_failure_rate(run_summary)
        if failure_check["too_high"]:
            blocked_reasons.append("high_failure_rate")
            downgrade = True
            logger.warning(f"Safety gate: Failure rate {failure_check['rate']:.1%} > {self.max_failure_rate:.1%}")

        # Gate 3: Drift detection
        drift = self._check_drift(run_summary)
        if drift["detected"]:
            blocked_reasons.append("performance_drift")
            warnings.append(f"Drift detected: {drift['description']}")
            logger.warning(f"Safety gate: {drift['description']}")

        # Gate 4: Stability check
        stability = self._check_stability(run_summary)
        if not stability["stable"]:
            blocked_reasons.append("unstable_performance")
            warnings.append(f"Instability: {stability['reason']}")

        # Gate 5: Learning mode check
        if learning_mode == "observe":
            # Observe mode never allows autonomous changes
            blocked_reasons.append("observe_mode_active")

        allow_autonomy = len(blocked_reasons) == 0

        result = {
            "allow_autonomy": allow_autonomy,
            "blocked_reasons": blocked_reasons,
            "downgrade_to_supervised": downgrade,
            "warnings": warnings,
            "checks": {
                "readiness": readiness,
                "failure_rate": failure_check,
                "drift": drift,
                "stability": stability
            }
        }

        if not allow_autonomy:
            logger.info(f"Safety gates BLOCKED autonomy: {', '.join(blocked_reasons)}")
        else:
            logger.info("Safety gates PASSED: Autonomy allowed")

        return result

    def _check_readiness(self, run_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Check if there's enough data to make autonomous decisions."""
        total_runs = run_summary.get("total_runs", 0)

        if total_runs < self.min_runs_for_autonomy:
            return {
                "ready": False,
                "reason": f"Need {self.min_runs_for_autonomy} runs, have {total_runs}",
                "runs": total_runs,
                "required": self.min_runs_for_autonomy
            }

        return {
            "ready": True,
            "runs": total_runs,
            "required": self.min_runs_for_autonomy
        }

    def _check_failure_rate(self, run_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Check if failure rate is within acceptable bounds."""
        total_runs = run_summary.get("total_runs", 0)
        failed_runs = run_summary.get("failed_runs", 0)

        if total_runs == 0:
            return {"too_high": False, "rate": 0.0}

        failure_rate = failed_runs / total_runs

        return {
            "too_high": failure_rate > self.max_failure_rate,
            "rate": failure_rate,
            "threshold": self.max_failure_rate,
            "failed": failed_runs,
            "total": total_runs
        }

    def _check_drift(self, run_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Detect unexpected changes in performance."""
        recent_stats = run_summary.get("recent_performance", {})
        historical_stats = run_summary.get("historical_performance", {})

        if not recent_stats or not historical_stats:
            return {"detected": False, "description": "Insufficient data for drift detection"}

        # Check RTF drift
        recent_rtf = recent_stats.get("avg_rtf", 0)
        historical_rtf = historical_stats.get("avg_rtf", 0)

        if historical_rtf > 0:
            rtf_change_percent = abs((recent_rtf - historical_rtf) / historical_rtf * 100)

            if rtf_change_percent > self.max_drift_percent:
                return {
                    "detected": True,
                    "description": f"RTF drifted {rtf_change_percent:.1f}% (recent: {recent_rtf:.2f}, historical: {historical_rtf:.2f})",
                    "metric": "rtf",
                    "change_percent": rtf_change_percent
                }

        return {"detected": False}

    def _check_stability(self, run_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Check for consistent performance."""
        recent_runs = run_summary.get("recent_runs", [])

        if len(recent_runs) < 3:
            return {
                "stable": True,  # Not enough data to judge instability
                "reason": "Insufficient recent runs"
            }

        # Check for alternating success/failure pattern (instability indicator)
        if len(recent_runs) >= 4:
            last_4 = recent_runs[-4:]
            success_pattern = [r.get("success", False) for r in last_4]

            # Pattern like [True, False, True, False] indicates instability
            alternating = all(
                success_pattern[i] != success_pattern[i+1]
                for i in range(len(success_pattern) - 1)
            )

            if alternating:
                return {
                    "stable": False,
                    "reason": "Alternating success/failure pattern detected",
                    "pattern": success_pattern
                }

        return {"stable": True}

    def get_recommended_mode(self, safety_result: Dict[str, Any]) -> str:
        """
        Recommend learning mode based on safety check results.

        Returns:
            - "autonomous": Safe to allow autonomous adjustments
            - "supervised": Require human approval
            - "observe": Only observe, no changes
        """
        if not safety_result["allow_autonomy"]:
            if safety_result["downgrade_to_supervised"]:
                return "supervised"
            return "observe"

        return "autonomous"
