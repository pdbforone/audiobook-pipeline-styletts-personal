"""
Evaluator for Phase H reasoning.

Reads recent telemetry (policy logs, error registry, benchmark reports)
and produces a structured, opt-in summary. No pipeline behavior changes
when disabled.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from autonomy.memory_store import add_experience
except Exception:  # noqa: BLE001
    add_experience = None  # Optional

logger = logging.getLogger(__name__)


class ReasoningEvaluator:
    """Heuristic evaluator for pipeline runs (opt-in)."""

    def __init__(self, threshold: float = 0.6) -> None:
        self.threshold = threshold

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _load_latest_benchmark(self, history_dir: Path) -> Optional[Dict[str, Any]]:
        if not history_dir.exists():
            return None
        candidates = sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return None
        return self._load_json(candidates[0])

    def _compute_chunk_failure_rate(
        self,
        pipeline_json: Dict[str, Any],
        error_registry: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total_chunks = 0
        failed_chunks = 0

        phase4 = (pipeline_json.get("phase4") or {}).get("files", {})
        for entry in phase4.values():
            chunks = entry.get("chunks") or []
            total_chunks += len(chunks)
            failed_chunks += len([c for c in chunks if c.get("status") not in ("success", "complete")])

        if error_registry and isinstance(error_registry, dict):
            failed_chunks = max(failed_chunks, len(error_registry.get("entries", {})))

        rate = (failed_chunks / total_chunks) if total_chunks else None
        return {"rate": rate, "failed": failed_chunks, "total": total_chunks}

    def _aggregate_rtf(self, benchmark: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not benchmark:
            return {}
        out: Dict[str, Any] = {}
        engines = benchmark.get("engines", {})
        for name, payload in engines.items():
            rtfs = [s.get("rtf") for s in payload.get("samples", []) if isinstance(s, dict) and s.get("rtf")]
            if not rtfs:
                continue
            out[name] = {
                "avg_rtf": sum(rtfs) / len(rtfs),
                "median_rtf": sorted(rtfs)[len(rtfs) // 2],
            }
        return out

    def _count_repair_attempts(self, error_registry: Optional[Dict[str, Any]]) -> int:
        if not error_registry or "entries" not in error_registry:
            return 0
        attempts = 0
        for entry in error_registry.get("entries", {}).values():
            attempts += len(entry.get("attempts", []))
        return attempts

    def evaluate_run(
        self,
        *,
        pipeline_json: Path,
        file_id: Optional[str] = None,
        policy_logs_dir: Path = Path(".pipeline") / "policy_logs",
        error_registry_path: Path = Path(".pipeline") / "error_registry.json",
        benchmark_history_dir: Path = Path(".pipeline") / "benchmark_history",
    ) -> Dict[str, Any]:
        """Evaluate a run and produce a structured summary."""
        pj = self._load_json(pipeline_json) or {}
        error_registry = self._load_json(error_registry_path)
        benchmark = self._load_latest_benchmark(benchmark_history_dir)
        # Preserve benchmark path for downstream diagnostics (non-intrusive)
        benchmark_used = str(benchmark_history_dir)

        failure_stats = self._compute_chunk_failure_rate(pj, error_registry)
        rtf_stats = self._aggregate_rtf(benchmark)
        repair_attempts = self._count_repair_attempts(error_registry)

        issues: List[str] = []
        if failure_stats["rate"] is not None and failure_stats["rate"] > 0.05:
            issues.append("chunk_failure_rate_high")
        if repair_attempts > 0:
            issues.append("repairs_attempted")

        score = 100.0
        if failure_stats["rate"] is not None:
            score -= min(60.0, failure_stats["rate"] * 100 * 1.5)
        score -= min(10.0, repair_attempts * 1.0)

        # Average RTF influence
        for stats in rtf_stats.values():
            if stats.get("avg_rtf") and stats["avg_rtf"] > 3.0:
                score -= 5.0

        score = max(0.0, min(100.0, score))

        recommendations: List[str] = []
        if failure_stats["rate"] and failure_stats["rate"] > 0.05:
            recommendations.append("Consider reducing chunk size by ~10% for next run.")
        if rtf_stats:
            fastest = min(rtf_stats.items(), key=lambda kv: kv[1].get("avg_rtf", 999))[0]
            recommendations.append(f"Use {fastest} for speed-sensitive drafts based on latest benchmarks.")

        summary = {
            "file_id": file_id,
            "score": score,
            "metrics": {
                "chunk_failure_rate": failure_stats,
                "rtf": rtf_stats,
                "repair_attempts": repair_attempts,
            },
            "issues": issues,
            "recommendations": recommendations,
            "source": {
                "policy_logs_dir": str(policy_logs_dir),
                "error_registry": str(error_registry_path),
                "benchmark_history": benchmark_used,
                "pipeline_json": str(pipeline_json),
            },
        }
        if add_experience:
            try:
                add_experience("eval_summary", summary)
            except Exception:
                pass
        return summary
