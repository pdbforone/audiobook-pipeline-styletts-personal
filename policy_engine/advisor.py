from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple

LOG_ROOT = Path(".pipeline") / "policy_logs"
REPORT_DIR = Path("policy_reports")


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

        if phase == "phase3" and file_id:
            rec = recommend_chunk_size(file_id, stats=stats)
            if rec:
                advice["chunk_size"] = rec
        if phase == "phase4" and file_id:
            engine = recommend_engine(file_id, stats=stats)
            if engine:
                advice["engine"] = engine
            voice = recommend_voice_variant(file_id, stats=stats)
            if voice:
                advice["voice_variant"] = voice
        if phase in {"phase4", "phase5", "phase5.5"}:
            retry = recommend_retry_policy(phase or "", stats=stats)
            if retry:
                advice["retry_policy"] = retry

        return advice

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
    phase_duration: Dict[str, List[float]] = defaultdict(list)
    phase_failures: Dict[str, int] = defaultdict(int)
    phase_success: Dict[str, int] = defaultdict(int)
    file_failures: Dict[Tuple[str, str], int] = defaultdict(int)
    chunk_error_count = 0
    chunk_event_total = 0
    engine_success: Dict[str, int] = defaultdict(int)
    engine_failure: Dict[str, int] = defaultdict(int)
    hallucination_flags = 0
    enhancement_failures = 0
    enhancement_total = 0

    for event in events:
        phase = event.get("phase")
        file_id = event.get("file_id")
        status = event.get("status")
        duration = event.get("duration_ms")
        errors = event.get("errors") or []
        metrics = event.get("metrics") or {}

        if event.get("event") == "phase_end" and isinstance(duration, (int, float)):
            phase_duration[phase].append(float(duration))
            phase_success[phase] += 1
        if event.get("event") in {"phase_failure", "phase_retry"}:
            phase_failures[phase] += 1
            if phase and file_id:
                file_failures[(phase, file_id)] += 1
        if phase == "phase3":
            chunk_event_total += 1
            if errors and any("chunk" in str(err).lower() for err in errors):
                chunk_error_count += 1
        if phase == "phase4":
            engine = metrics.get("engine_used") or metrics.get("selected_engine")
            if engine:
                if status == "success" or event.get("event") == "phase_end":
                    engine_success[engine] += 1
                elif event.get("event") == "phase_failure":
                    engine_failure[engine] += 1
            if errors and any("hallucination" in str(err).lower() for err in errors):
                hallucination_flags += 1
        if phase == "phase5":
            enhancement_total += 1
            if event.get("event") == "phase_failure":
                enhancement_failures += 1

    return {
        "phase_duration": {
            key: mean(values) for key, values in phase_duration.items() if values
        },
        "phase_failures": dict(phase_failures),
        "phase_success": dict(phase_success),
        "file_failures": dict(file_failures),
        "chunk_error_rate": (chunk_error_count / chunk_event_total) if chunk_event_total else 0.0,
        "engine_reliability": compute_engine_reliability(engine_success, engine_failure),
        "hallucination_flags": hallucination_flags,
        "enhancement_failure_rate": (
            enhancement_failures / enhancement_total if enhancement_total else 0.0
        ),
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


def recommend_chunk_size(file_id: str, *, stats: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    stats = stats or {}
    phase3_avg = (stats.get("phase_duration") or {}).get("phase3")
    if not phase3_avg:
        return None
    if phase3_avg > 600_000:
        return {
            "action": "reduce_chunk_size",
            "reason": f"Avg Phase 3 duration {phase3_avg/1000:.1f}s indicates large chunks for {file_id}.",
        }
    if phase3_avg < 180_000:
        return {
            "action": "increase_chunk_size",
            "reason": f"Phase 3 completes in {phase3_avg/1000:.1f}s; consider larger chunks to improve throughput.",
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

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
