"""
Append-only memory store for Llama-aware context (opt-in).

Writes JSONL entries to .pipeline/llm_memory/memory.jsonl and provides
lightweight query/summarization helpers. No schema enforcement beyond
basic dict acceptance.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMORY_DIR = Path(".pipeline") / "llm_memory"
MEMORY_PATH = MEMORY_DIR / "memory.jsonl"
RUN_MEMORY_DIR = Path(".pipeline") / "memory"
RUN_MEMORY_PATH = RUN_MEMORY_DIR / "memory.jsonl"


def _ensure_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def add_experience(event_type: str, payload: Dict) -> None:
    """Append an experience entry to memory.jsonl with timestamp."""
    _ensure_dir()
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": event_type,
        "payload": payload or {},
    }
    try:
        with MEMORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        # Fail silently to avoid impacting runtime
        return


def query_recent(event_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
    """Return the most recent N events, optionally filtered by type."""
    if not MEMORY_PATH.exists():
        return []
    events: List[Dict] = []
    try:
        with MEMORY_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []

    if event_type:
        events = [e for e in events if e.get("type") == event_type]

    return events[-limit:]


def summarize_history(max_events: int = 200) -> Dict:
    """Generate a summary suitable for Llama consumption (counts, trends)."""
    events = query_recent(limit=max_events)
    counts: Dict[str, int] = {}
    for e in events:
        etype = e.get("type") or "unknown"
        counts[etype] = counts.get(etype, 0) + 1

    return {
        "total_events": len(events),
        "counts": counts,
        "recent": events[-5:],  # small tail sample
        "notes": "Memory summary is read-only and opt-in.",
    }


def extract_engine_stability_patterns(run_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Basic aggregation of engine stability from run history."""
    engines = {}
    for run in run_history or []:
        eval_score = run.get("payload", {}).get("evaluator", {}).get("score")
        engine = run.get("payload", {}).get("evaluator", {}).get("engine_used")
        if engine:
            data = engines.setdefault(engine, {"count": 0, "scores": []})
            data["count"] += 1
            if isinstance(eval_score, (int, float)):
                data["scores"].append(eval_score)
    return engines


def extract_genre_patterns(run_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize genres seen in runs."""
    genres = {}
    for run in run_history or []:
        genre = run.get("payload", {}).get("evaluator", {}).get("genre")
        if genre:
            genres[genre] = genres.get(genre, 0) + 1
    return genres


def extract_chunk_size_patterns(run_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate chunk size hints from run history."""
    chunks = []
    for run in run_history or []:
        cs = run.get("payload", {}).get("evaluator", {}).get("chunk_size")
        if isinstance(cs, (int, float)):
            chunks.append(cs)
    return {"samples": chunks, "count": len(chunks)}


# Phase M: stability helpers (aliases to satisfy new API names)
def extract_genre_stability(run_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    return extract_genre_patterns(run_history)


def extract_chunk_size_stability(run_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    return extract_chunk_size_patterns(run_history)


# ---------------------------------------------------------------------------
# Phase K additions (run-to-run feedback, additive-only)
# ---------------------------------------------------------------------------
def _read_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return entries[-limit:]


def load_recent_events(limit: int = 20) -> List[Dict[str, Any]]:
    """Load recent memory events from the append-only memory log."""
    return query_recent(limit=limit)


def load_run_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Load recent run-level performance entries."""
    RUN_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return _read_jsonl(RUN_MEMORY_PATH, limit)


def load_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """Return normalized run profiles for recent runs."""
    raw_history = load_run_history(limit=limit)
    normalized: List[Dict[str, Any]] = []
    for entry in raw_history:
        if not isinstance(entry, dict):
            continue
        if "run_profile" in entry and isinstance(entry["run_profile"], dict):
            normalized.append(entry["run_profile"])
            continue
        payload = entry.get("payload", {}) if isinstance(entry.get("payload"), dict) else {}
        if "run_profile" in payload and isinstance(payload["run_profile"], dict):
            normalized.append(payload["run_profile"])
            continue
        normalized.append(entry)
    return normalized


def record_run_performance(
    run_id: str,
    file_id: str,
    evaluator_summary: Dict[str, Any],
    diagnostics_summary: Optional[Dict[str, Any]] = None,
    reward: Optional[float] = None,
    engine_used: Optional[str] = None,
    chunk_settings: Optional[Dict[str, Any]] = None,
    duration_seconds: Optional[float] = None,
    phase_failures: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a run performance entry (opt-in only)."""
    RUN_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    evaluator_summary = evaluator_summary or {}
    diagnostics_summary = diagnostics_summary or {}
    chunk_settings = chunk_settings or evaluator_summary.get("chunk_settings") or {}
    engine_used = engine_used or evaluator_summary.get("engine_used")
    duration_seconds = (
        duration_seconds
        if duration_seconds is not None
        else evaluator_summary.get("duration_seconds")
    )
    metrics = evaluator_summary.get("metrics") if isinstance(evaluator_summary, dict) else {}
    run_profile = {
        "run_id": run_id,
        "file_id": file_id,
        "phase_failures": phase_failures
        if phase_failures is not None
        else evaluator_summary.get("phase_failures", {}),
        "metrics": metrics or {},
        "reward": reward,
        "engine_used": engine_used,
        "chunk_settings": chunk_settings,
        "duration_seconds": duration_seconds,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if diagnostics_summary:
        run_profile["diagnostics"] = diagnostics_summary
    entry = {
        "type": "run_performance",
        "payload": {
            "evaluator": evaluator_summary,
            "diagnostics": diagnostics_summary,
            "run_profile": run_profile,
        },
        "timestamp": run_profile["timestamp"],
    }
    entry["run_profile"] = run_profile
    try:
        with RUN_MEMORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        return


def compare_with_previous_runs(current_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return a lightweight comparison against recent runs (informational only)."""
    history = load_run_history(limit=10)
    total = len(history)
    scores = [h.get("payload", {}).get("evaluator", {}).get("score") for h in history if isinstance(h, dict)]
    scores = [s for s in scores if isinstance(s, (int, float))]
    trend = None
    if scores and isinstance(current_summary, dict):
        current_score = current_summary.get("score")
        if isinstance(current_score, (int, float)):
            avg = sum(scores) / len(scores) if scores else None
            trend = "improving" if avg and current_score > avg else "declining" if avg and current_score < avg else "stable"
    return {
        "history_count": total,
        "score_trend": trend,
    }


def load_previous_run() -> Optional[Dict[str, Any]]:
    """Convenience to fetch the most recent run performance entry."""
    history = load_run_history(limit=1)
    return history[-1] if history else None


# ---------------------------------------------------------------------------
# Phase M additive helpers (profiles/metadata aggregation; read-only)
# ---------------------------------------------------------------------------
def load_metadata_history(path: Path = Path(".pipeline/metadata"), limit: int = 20) -> List[Dict[str, Any]]:
    """Load recent metadata artifacts if available (best-effort, read-only)."""
    if not path.exists():
        return []
    files = sorted(path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    out: List[Dict[str, Any]] = []
    for file in files:
        try:
            out.append(json.loads(file.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out
