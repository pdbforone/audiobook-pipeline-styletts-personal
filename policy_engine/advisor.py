from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple

LOG_ROOT = Path(".pipeline") / "policy_logs"
REPORT_DIR = Path("policy_reports")
ROLLING_WINDOW = 40
HALLUCINATION_WINDOW = 20


def _safe_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    k = (pct / 100.0) * (len(values) - 1)
    lower = int(k)
    upper = min(len(values) - 1, lower + 1)
    weight = k - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _summarize_numbers(values: Iterable[float]) -> Dict[str, float]:
    seq = list(values)
    if not seq:
        return {}
    ordered = sorted(seq)
    return {
        "avg_ms": mean(ordered),
        "p50_ms": _percentile(ordered, 50.0),
        "p95_ms": _percentile(ordered, 95.0),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "samples": len(ordered),
    }


def _summarize_recent(values: deque[float]) -> Dict[str, float]:
    return _summarize_numbers(list(values))


def _build_phase_duration_analysis(summary: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    if not summary:
        return {}
    valid = [(phase, data) for phase, data in summary.items() if data.get("avg_ms") is not None]
    if not valid:
        return {}
    sorted_avg = sorted(valid, key=lambda item: item[1]["avg_ms"])
    analysis: Dict[str, Any] = {}
    slowest = sorted_avg[-1]
    analysis["slowest_phase"] = {"phase": slowest[0], **slowest[1]}
    fastest = sorted_avg[0]
    analysis["fastest_phase"] = {"phase": fastest[0], **fastest[1]}
    variability = sorted(valid, key=lambda item: (item[1]["max_ms"] - item[1]["min_ms"]), reverse=True)
    analysis["most_variable_phase"] = {"phase": variability[0][0], **variability[0][1]}
    return analysis


def _parse_timestamp(value: Any) -> float:
    if not value:
        return 0.0
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1]
    try:
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return 0.0


class PolicyAdvisor:
    """Lightweight analytics layer that reads policy logs and issues suggestions."""

    def __init__(self, log_root: Optional[Path] = None) -> None:
        self.log_root = Path(log_root) if log_root else LOG_ROOT
        self._cache_token: Optional[Tuple[float, int]] = None
        self._stats: Dict[str, Any] = {}

    def advise(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        stats = self._refresh()
        phase = ctx.get("phase")
        file_id = ctx.get("file_id")
        advice: Dict[str, Any] = {}
        suggestions: List[Dict[str, Any]] = []

        def _add_suggestion(kind: str, payload: Dict[str, Any], *, confidence: float = 0.6) -> None:
            suggestions.append(
                {
                    "type": kind,
                    "phase": phase,
                    "confidence": confidence,
                    "payload": payload,
                }
            )

        if phase == "phase3" and file_id:
            rec = recommend_chunk_size(file_id, stats=stats)
            if rec:
                advice["chunk_size"] = rec
                _add_suggestion("chunk_size", rec, confidence=rec.get("confidence", 0.65))

        if phase == "phase4" and file_id:
            engine = recommend_engine(file_id, stats=stats)
            if engine:
                advice["engine"] = engine
                _add_suggestion("engine", engine, confidence=engine.get("confidence", 0.7))
            voice = recommend_voice_variant(file_id, stats=stats)
            if voice:
                advice["voice_variant"] = voice
                _add_suggestion("voice_variant", voice, confidence=0.55)
        if phase in {"phase4", "phase5", "phase5.5"}:
            retry = recommend_retry_policy(phase or "", stats=stats)
            if retry:
                advice["retry_policy"] = retry
                _add_suggestion("retry_policy", retry, confidence=0.5)

        alerts = build_soft_alerts(stats, ctx)
        if alerts:
            suggestions.extend(alerts)

        telemetry = build_telemetry_snapshot(stats)
        if telemetry:
            advice["telemetry"] = telemetry
        if suggestions:
            advice["suggestions"] = suggestions

        return advice

    def snapshot(self) -> Dict[str, Any]:
        """Return cached statistics without emitting new advice."""
        return self._refresh()

    def _refresh(self) -> Dict[str, Any]:
        try:
            snapshot = self._log_snapshot()
        except FileNotFoundError:
            self._stats = {}
            self._cache_token = None
            return self._stats

        if snapshot == self._cache_token and self._stats:
            return self._stats

        events = list(iter_events(self.log_root))
        self._stats = compute_stats(events)
        self._cache_token = snapshot
        return self._stats

    def _log_snapshot(self) -> Tuple[float, int]:
        if not self.log_root.exists():
            raise FileNotFoundError(self.log_root)
        newest_mtime = 0.0
        total_files = 0
        for path in self.log_root.glob("*.log"):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            newest_mtime = max(newest_mtime, mtime)
            total_files += 1
        if total_files == 0:
            raise FileNotFoundError(self.log_root)
        return newest_mtime, total_files


def iter_events(log_root: Path) -> Iterable[Dict[str, Any]]:
    for log_path in sorted(log_root.glob("*.log")):
        try:
            with log_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            continue


def compute_stats(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    def _rolling_deque() -> deque[float]:
        return deque(maxlen=ROLLING_WINDOW)

    phase_duration: Dict[str, List[float]] = defaultdict(list)
    rolling_phase_duration: Dict[str, deque[float]] = defaultdict(_rolling_deque)
    phase_failures: Dict[str, int] = defaultdict(int)
    phase_success: Dict[str, int] = defaultdict(int)
    file_failures: Dict[Tuple[str, str], int] = defaultdict(int)
    chunk_error_count = 0
    chunk_event_total = 0
    engine_success: Dict[str, int] = defaultdict(int)
    engine_failure: Dict[str, int] = defaultdict(int)
    hallucination_flags = 0
    hallucination_by_engine: Dict[str, int] = defaultdict(int)
    hallucination_recent: deque[Dict[str, Any]] = deque(maxlen=HALLUCINATION_WINDOW)
    enhancement_failures = 0
    enhancement_total = 0
    rtf_samples: List[float] = []
    rolling_rt_factor: deque[float] = deque(maxlen=ROLLING_WINDOW)
    rtf_by_engine: Dict[str, List[float]] = defaultdict(list)
    fallback_rates: List[float] = []
    rolling_fallback: deque[float] = deque(maxlen=ROLLING_WINDOW)
    fallback_by_engine: Dict[str, List[float]] = defaultdict(list)
    fallback_recent_by_engine: Dict[str, deque[float]] = defaultdict(_rolling_deque)
    fallback_chunk_counts: List[float] = []
    fallback_chunks_by_engine: Dict[str, List[float]] = defaultdict(list)
    run_info: Dict[str, Dict[str, Any]] = {}

    for record in events:
        event_type = record.get("event")
        phase = record.get("phase")
        file_id = record.get("file_id")
        status = record.get("status")
        duration = record.get("duration_ms")
        errors = record.get("errors") or []
        metrics = record.get("metrics") or {}
        run_id = record.get("run_id")
        if run_id:
            info = run_info.setdefault(run_id, {"failed": False})
            ts = record.get("timestamp")
            if ts and (not info.get("timestamp") or ts < info.get("timestamp")):
                info["timestamp"] = ts
            if event_type == "phase_failure":
                info["failed"] = True
            if errors and any("hallucination" in str(err).lower() for err in errors):
                info["hallucination"] = True
            metrics_bucket = info.setdefault("metrics", {})
            if phase == "phase4" and event_type == "phase_end":
                for key in ("avg_rt_factor", "fallback_rate", "latency_fallback_chunks"):
                    if metrics.get(key) is not None:
                        metrics_bucket[key] = metrics.get(key)

        if event_type == "phase_end" and isinstance(duration, (int, float)):
            value = float(duration)
            phase_duration[phase].append(value)
            phase_success[phase] += 1
            rolling_phase_duration[phase].append(value)
        if event_type in {"phase_failure", "phase_retry"}:
            phase_failures[phase] += 1
            if phase and file_id:
                file_failures[(phase, file_id)] += 1
        if phase == "phase3":
            chunk_event_total += 1
            if errors and any("chunk" in str(err).lower() for err in errors):
                chunk_error_count += 1
        if phase == "phase4":
            engine = (
                metrics.get("engine_used")
                or metrics.get("selected_engine")
                or metrics.get("requested_engine")
            )
            if engine:
                if status == "success" or event_type == "phase_end":
                    engine_success[engine] += 1
                elif event_type == "phase_failure":
                    engine_failure[engine] += 1
            avg_rt = _safe_float(metrics.get("avg_rt_factor"))
            if avg_rt is not None:
                rtf_samples.append(avg_rt)
                rolling_rt_factor.append(avg_rt)
                if engine:
                    rtf_by_engine[engine].append(avg_rt)
            fallback_rate = _safe_float(metrics.get("fallback_rate"))
            if fallback_rate is not None:
                fallback_rates.append(fallback_rate)
                rolling_fallback.append(fallback_rate)
                if engine:
                    fallback_by_engine[engine].append(fallback_rate)
                    fallback_recent_by_engine[engine].append(fallback_rate)
            latency_chunks = _safe_float(metrics.get("latency_fallback_chunks"))
            if latency_chunks is not None:
                fallback_chunk_counts.append(latency_chunks)
                if engine:
                    fallback_chunks_by_engine[engine].append(latency_chunks)
            if errors and any("hallucination" in str(err).lower() for err in errors):
                hallucination_flags += 1
                if engine:
                    hallucination_by_engine[engine] += 1
                hallucination_recent.append(
                    {
                        "timestamp": record.get("timestamp"),
                        "file_id": file_id,
                        "engine": engine,
                    }
                )
        if phase == "phase5":
            enhancement_total += 1
            if event_type == "phase_failure":
                enhancement_failures += 1

    phase_duration_summary = {
        key: _summarize_numbers(values) for key, values in phase_duration.items() if values
    }
    rolling_phase_summary = {
        key: _summarize_recent(window) for key, window in rolling_phase_duration.items() if window
    }
    rtf_stats = _build_rtf_stats(rtf_samples, rolling_rt_factor, rtf_by_engine)
    fallback_stats = _build_fallback_stats(
        fallback_rates,
        rolling_fallback,
        fallback_by_engine,
        fallback_recent_by_engine,
        fallback_chunk_counts,
        fallback_chunks_by_engine,
    )
    hallucination_stats = {
        "total": hallucination_flags,
        "recent_total": len(hallucination_recent),
        "by_engine": dict(hallucination_by_engine),
        "recent_events": list(hallucination_recent),
    }
    rolling_metrics = {
        "phase_duration_ms": rolling_phase_summary,
        "rt_factor": {
            "avg": mean(rolling_rt_factor) if rolling_rt_factor else None,
            "max": max(rolling_rt_factor) if rolling_rt_factor else None,
            "samples": len(rolling_rt_factor),
        },
        "fallback_rate": {
            "avg": mean(rolling_fallback) if rolling_fallback else None,
            "max": max(rolling_fallback) if rolling_fallback else None,
            "samples": len(rolling_fallback),
        },
    }
    run_history = [
        {
            "run_id": run_id,
            "failed": details.get("failed", False),
            "timestamp": details.get("timestamp"),
            "metrics": details.get("metrics", {}),
            "hallucination": details.get("hallucination", False),
        }
        for run_id, details in run_info.items()
    ]
    run_history.sort(key=lambda item: _parse_timestamp(item.get("timestamp")))
    recent_good_runs = 0
    for entry in reversed(run_history):
        if entry.get("failed"):
            break
        recent_good_runs += 1
    run_rewards: List[Dict[str, Any]] = []
    for entry in run_history:
        reward = _compute_run_reward(entry)
        entry["reward"] = reward
        run_rewards.append({"run_id": entry["run_id"], "reward": reward})
    reward_values = [item["reward"] for item in run_rewards]
    reward_average = mean(reward_values) if reward_values else 0.0
    chunk_error_rate = (chunk_error_count / chunk_event_total) if chunk_event_total else 0.0
    engine_reliability_data = compute_engine_reliability(engine_success, engine_failure)
    sorted_engines = sorted(engine_reliability_data.items(), key=lambda item: item[1], reverse=True)
    best_score = sorted_engines[0][1] if sorted_engines else 0.0
    second_score = sorted_engines[1][1] if len(sorted_engines) > 1 else 0.0
    engine_bias = max(0.0, best_score - second_score)
    voice_penalty = min(
        1.0,
        float(hallucination_flags) / max(1, len(run_history)) if run_history else 0.0,
    )
    skill_weights = {
        "chunk_size": max(0.0, 1.0 - chunk_error_rate),
        "engine": best_score,
        "voice": max(0.0, 1.0 - voice_penalty),
    }
    adaptive_deltas = {
        "chunk_size": max(-2.0, min(2.0, reward_average * 2.0)),
        "engine_bias": engine_bias,
    }
    safety_flags = {
        "revert_chunk": reward_average < -0.5,
        "revert_engine": reward_average < -0.75,
        "voice_alert": bool(hallucination_flags),
    }

    return {
        "phase_duration": {
            key: mean(values) for key, values in phase_duration.items() if values
        },
        "phase_duration_summary": phase_duration_summary,
        "phase_duration_recent": rolling_phase_summary,
        "phase_duration_analysis": _build_phase_duration_analysis(phase_duration_summary),
        "phase_failures": dict(phase_failures),
        "phase_success": dict(phase_success),
        "file_failures": dict(file_failures),
        "chunk_error_rate": chunk_error_rate,
        "engine_reliability": engine_reliability_data,
        "hallucination_flags": hallucination_flags,
        "hallucination_stats": hallucination_stats,
        "enhancement_failure_rate": (
            enhancement_failures / enhancement_total if enhancement_total else 0.0
        ),
        "rtf_stats": rtf_stats,
        "engine_fallback_rates": fallback_stats,
        "rolling_metrics": rolling_metrics,
        "run_history": run_history,
        "recent_good_runs": recent_good_runs,
        "run_rewards": run_rewards,
        "reward_average": reward_average,
        "skill_weights": skill_weights,
        "adaptive_deltas": adaptive_deltas,
        "safety_flags": safety_flags,
    }


def _build_rtf_stats(
    samples: List[float],
    rolling: deque[float],
    per_engine: Dict[str, List[float]],
) -> Dict[str, Any]:
    ordered = sorted(samples)
    summary: Dict[str, Any] = {
        "avg": mean(ordered) if ordered else None,
        "p90": _percentile(ordered, 90.0),
        "p99": _percentile(ordered, 99.0),
        "recent_avg": mean(rolling) if rolling else None,
        "samples": len(ordered),
        "rolling_samples": len(rolling),
        "by_engine": {},
    }
    engines: Dict[str, Dict[str, Any]] = {}
    for engine, values in per_engine.items():
        if not values:
            continue
        ordered_vals = sorted(values)
        engines[engine] = {
            "avg": mean(ordered_vals),
            "p90": _percentile(ordered_vals, 90.0),
            "samples": len(ordered_vals),
        }
    summary["by_engine"] = engines
    return summary


def _build_fallback_stats(
    overall_rates: List[float],
    rolling_rates: deque[float],
    per_engine: Dict[str, List[float]],
    per_engine_recent: Dict[str, deque[float]],
    chunk_counts: List[float],
    chunk_counts_by_engine: Dict[str, List[float]],
) -> Dict[str, Any]:
    ordered = sorted(overall_rates)
    overall = {
        "avg_rate": mean(ordered) if ordered else None,
        "recent_rate": mean(rolling_rates) if rolling_rates else None,
        "max_rate": max(ordered) if ordered else None,
        "samples": len(ordered),
        "rolling_samples": len(rolling_rates),
    }
    engines: Dict[str, Dict[str, Any]] = {}
    for engine, values in per_engine.items():
        if not values:
            continue
        ordered_vals = sorted(values)
        recent_window = per_engine_recent.get(engine)
        chunk_counts_for_engine = chunk_counts_by_engine.get(engine) or []
        engines[engine] = {
            "avg_rate": mean(ordered_vals),
            "recent_rate": mean(recent_window) if recent_window else None,
            "samples": len(ordered_vals),
            "avg_latency_chunks": mean(chunk_counts_for_engine) if chunk_counts_for_engine else None,
        }
    return {
        "overall": overall,
        "per_engine": engines,
        "latency_chunks_avg": mean(chunk_counts) if chunk_counts else None,
    }


def compute_engine_reliability(
    success: Dict[str, int],
    failure: Dict[str, int],
) -> Dict[str, float]:
    reliability: Dict[str, float] = {}
    for engine, count in success.items():
        fails = failure.get(engine, 0)
        total = count + fails
        if total:
            reliability[engine] = count / total
    for engine, fails in failure.items():
        if engine not in reliability:
            reliability[engine] = 0.0
    return reliability


def build_soft_alerts(stats: Dict[str, Any], ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    phase = ctx.get("phase")

    def _push(kind: str, message: str, *, confidence: float, extras: Optional[Dict[str, Any]] = None) -> None:
        payload = {"message": message}
        if extras:
            payload.update(extras)
        alerts.append(
            {
                "type": kind,
                "phase": phase,
                "confidence": confidence,
                "payload": payload,
            }
        )

    rtf_stats = stats.get("rtf_stats") or {}
    fallback_stats = stats.get("engine_fallback_rates") or {}
    hallucinations = stats.get("hallucination_stats") or {}
    recent_rt = rtf_stats.get("recent_avg")
    if isinstance(recent_rt, (int, float)) and recent_rt > 4.0:
        _push(
            "rt_factor_alert",
            f"Recent average RT factor {recent_rt:.2f}x exceeds 4.0x target.",
            confidence=0.4,
            extras={"rt_factor": recent_rt},
        )

    overall_fb = (fallback_stats.get("overall") or {}).get("recent_rate")
    if isinstance(overall_fb, (int, float)) and overall_fb > 0.25:
        _push(
            "fallback_alert",
            f"Latency fallback engaged on {overall_fb*100:.1f}% of recent chunks.",
            confidence=0.35,
            extras={"fallback_rate": overall_fb},
        )

    recent_hallu = hallucinations.get("recent_total") or 0
    if recent_hallu:
        _push(
            "hallucination_watch",
            f"{recent_hallu} hallucination warnings detected in the last {HALLUCINATION_WINDOW} events.",
            confidence=0.3,
            extras={"recent_total": recent_hallu, "events": hallucinations.get("recent_events")},
        )

    rolling_phase = (
        (stats.get("phase_duration_recent") or {}).get(phase or "")
        if phase
        else None
    )
    if rolling_phase:
        avg_ms = rolling_phase.get("avg_ms")
        if isinstance(avg_ms, (int, float)) and avg_ms > 600_000:
            _push(
                "phase_duration_watch",
                f"{phase} rolling average duration {avg_ms/1000:.1f}s suggests throughput regression.",
                confidence=0.45,
                extras={"avg_ms": avg_ms},
            )

    return alerts


def build_telemetry_snapshot(stats: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "phase_duration_summary",
        "phase_duration_analysis",
        "phase_duration_recent",
        "rolling_metrics",
        "rtf_stats",
        "engine_fallback_rates",
        "hallucination_stats",
    ]
    snapshot: Dict[str, Any] = {}
    for key in keys:
        value = stats.get(key)
        if value:
            snapshot[key] = value
    return snapshot


def recommend_chunk_size(file_id: str, *, stats: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    stats = stats or {}
    phase3_avg = (stats.get("phase_duration") or {}).get("phase3")
    if not phase3_avg:
        return None
    if phase3_avg > 600_000:
        return {
            "action": "reduce_chunk_size",
            "reason": f"Avg Phase 3 duration {phase3_avg/1000:.1f}s indicates large chunks for {file_id}.",
            "confidence": 0.7,
        }
    if phase3_avg < 180_000:
        return {
            "action": "increase_chunk_size",
            "reason": f"Phase 3 completes in {phase3_avg/1000:.1f}s; consider larger chunks to improve throughput.",
            "confidence": 0.6,
        }
    return None


def recommend_engine(file_id: str, *, stats: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    stats = stats or {}
    reliability = stats.get("engine_reliability") or {}
    if not reliability:
        return None
    best_engine = max(reliability.items(), key=lambda item: item[1])
    if best_engine[1] < 0.55:
        return None
    return {
        "engine": best_engine[0],
        "confidence": best_engine[1],
        "reason": f"Engine {best_engine[0]} shows {best_engine[1]*100:.1f}% success over recent runs.",
    }


def recommend_retry_policy(phase: str, *, stats: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    stats = stats or {}
    failures = (stats.get("phase_failures") or {}).get(phase, 0)
    success = (stats.get("phase_success") or {}).get(phase, 0)
    total = failures + success
    if not total:
        return None
    fail_rate = failures / total
    if fail_rate > 0.35:
        return {
            "phase": phase,
            "suggested_retries": 4,
            "reason": f"{phase} failure rate {fail_rate*100:.1f}% suggests increasing retries.",
        }
    if fail_rate < 0.05:
        return {
            "phase": phase,
            "suggested_retries": 1,
            "reason": f"{phase} failure rate {fail_rate*100:.1f}% is low; consider fewer retries.",
        }
    return None


def recommend_voice_variant(file_id: str, *, stats: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    stats = stats or {}
    failures = stats.get("file_failures") or {}
    phase4_failures = failures.get(("phase4", file_id), 0)
    if phase4_failures >= 2:
        return {
            "action": "switch_voice_variant",
            "reason": f"{phase4_failures} Phase 4 failures detected for {file_id}; consider alternate voice/variant.",
        }
    return None


def generate_report(output_path: Optional[Path] = None) -> Path:
    advisor = PolicyAdvisor()
    stats = advisor._refresh()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = output_path or (REPORT_DIR / "summary.md")

    lines = [
        "# Policy Engine Report",
        "",
        f"Generated: {datetime.utcnow().isoformat(timespec='seconds')}Z",
        "",
        "## Phase Duration (ms)",
    ]
    for phase, avg in sorted((stats.get("phase_duration") or {}).items()):
        lines.append(f"- {phase}: {avg:.0f} ms")

    lines.append("")
    lines.append("## Failure Rates")
    for phase, count in sorted((stats.get("phase_failures") or {}).items()):
        success = (stats.get("phase_success") or {}).get(phase, 0)
        total = count + success
        rate = (count / total * 100) if total else 0.0
        lines.append(f"- {phase}: {rate:.1f}% ({count}/{total})")

    lines.append("")
    lines.append(f"- Chunk error rate: {(stats.get('chunk_error_rate') or 0.0)*100:.1f}%")
    lines.append(f"- Enhancement failure rate: {(stats.get('enhancement_failure_rate') or 0.0)*100:.1f}%")
    lines.append(f"- Hallucination flags: {stats.get('hallucination_flags', 0)}")

    lines.append("")
    lines.append("## Engine Reliability")
    for engine, score in sorted((stats.get("engine_reliability") or {}).items()):
        lines.append(f"- {engine}: {score*100:.1f}% success")

    rtf_stats = stats.get("rtf_stats") or {}
    if rtf_stats:
        lines.append("")
        lines.append("## Real-Time Factor")
        avg_rt = rtf_stats.get("avg")
        if avg_rt is not None:
            lines.append(f"- Average: {avg_rt:.2f}x")
        if rtf_stats.get("p90") is not None:
            lines.append(f"- p90: {rtf_stats['p90']:.2f}x")
        if rtf_stats.get("p99") is not None:
            lines.append(f"- p99: {rtf_stats['p99']:.2f}x")

    fallback = stats.get("engine_fallback_rates") or {}
    overall_fb = fallback.get("overall") or {}
    if fallback:
        lines.append("")
        lines.append("## Engine Fallback Rates")
        if overall_fb:
            rate = overall_fb.get("avg_rate")
            if rate is not None:
                lines.append(f"- Overall latency fallback usage: {rate*100:.1f}%")
        per_engine = fallback.get("per_engine") or {}
        for engine, data in sorted(per_engine.items()):
            rate = data.get("avg_rate")
            if rate is None:
                continue
            lines.append(f"  - {engine}: {rate*100:.1f}% (samples={data.get('samples', 0)})")

    hallu = stats.get("hallucination_stats") or {}
    if hallu:
        lines.append("")
        lines.append("## Hallucination Counters")
        lines.append(f"- Total flagged: {hallu.get('total', 0)}")
        lines.append(f"- Recent window: {hallu.get('recent_total', 0)}")
        by_engine = hallu.get("by_engine") or {}
        for engine, count in sorted(by_engine.items()):
            lines.append(f"  - {engine}: {count}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
def _compute_run_reward(entry: Dict[str, Any]) -> float:
    reward = 1.0
    if entry.get("failed"):
        reward -= 1.5
    metrics = entry.get("metrics") or {}
    fallback = _safe_float(metrics.get("fallback_rate"))
    if fallback:
        reward -= float(fallback) * 0.5
    rt_factor = _safe_float(metrics.get("avg_rt_factor"))
    if rt_factor and rt_factor > 0:
        reward -= max(0.0, (float(rt_factor) - 2.0) * 0.1)
    if entry.get("hallucination"):
        reward -= 0.3
    return reward
