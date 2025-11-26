"""Phase P: lightweight, deterministic research analysis."""

from __future__ import annotations

from collections import Counter
from typing import Dict, Any, List


class ResearchAnalyzer:
    def _phase_summary(self, phase_metrics: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        for phase_key, data in phase_metrics.items():
            status = data.get("status") if isinstance(data, dict) else None
            summary[phase_key] = {"status": status}
        return summary

    def _failure_patterns(self, failures: Dict[str, List[str]]) -> Dict[str, Any]:
        counts = {k: len(v) for k, v in failures.items()}
        return {"counts": counts, "examples": {k: v[:3] for k, v in failures.items()}}

    def _engine_usage(self, engine_stats: Dict[str, Any]) -> Dict[str, Any]:
        engines = [v.get("engine_used") for v in engine_stats.values() if isinstance(v, dict)]
        freq = Counter([e for e in engines if e])
        return {"frequency": dict(freq)}

    def _chunk_distribution(self, chunk_stats: Dict[str, Any]) -> Dict[str, Any]:
        counts = [v.get("chunk_count", 0) for v in chunk_stats.values() if isinstance(v, dict)]
        if not counts:
            return {"counts": [], "min": None, "max": None, "avg": None}
        return {
            "counts": counts,
            "min": min(counts),
            "max": max(counts),
            "avg": sum(counts) / len(counts),
        }

    def analyze(self, collected: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accepts raw collected signals and returns a structured analysis dict.
        Only performs cheap, safe, deterministic analysis.
        Never writes to disk.
        """
        phase_metrics = collected.get("phase_metrics", {})
        failures = collected.get("failure_patterns", {})
        engine_stats = collected.get("engine_stats", {})
        chunk_stats = collected.get("chunk_stats", {})

        analysis: Dict[str, Any] = {
            "phase_summary": self._phase_summary(phase_metrics) if phase_metrics else {},
            "failure_patterns": self._failure_patterns(failures) if failures else {},
            "engine_usage": self._engine_usage(engine_stats) if engine_stats else {},
            "chunk_distribution": self._chunk_distribution(chunk_stats) if chunk_stats else {},
            "memory_notes": collected.get("memory_signals", {}),
            "policy_notes": collected.get("policy_signals", {}),
        }
        return analysis
