from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

LOG_ROOT = Path(".pipeline") / "policy_logs"
OVERRIDES_PATH = Path(".pipeline") / "tuning_overrides.json"


def load_policy_events(log_root: Path = LOG_ROOT) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not log_root.exists():
        return events
    for path in sorted(log_root.glob("*.log")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
    return events


def compute_dashboard_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    rtf_points: List[Tuple[float, float]] = []
    engine_counts: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()
    system_points: List[Tuple[float, float, float]] = []

    for event in events:
        timestamp = _parse_ts(event.get("timestamp"))
        phase = event.get("phase")
        metrics = event.get("metrics") or {}
        if phase == "phase4" and event.get("event") == "phase_end":
            rtf = metrics.get("avg_rt_factor")
            if isinstance(rtf, (int, float)):
                rtf_points.append((timestamp, float(rtf)))
            engine = metrics.get("selected_engine") or metrics.get("requested_engine")
            if engine:
                engine_counts[str(engine)] += 1
        if event.get("event") == "phase_failure":
            for err in event.get("errors") or []:
                failure_counts[str(err)] += 1
        cpu = event.get("cpu_percent")
        mem = event.get("memory_percent")
        if isinstance(cpu, (int, float)) and isinstance(mem, (int, float)):
            system_points.append((timestamp, float(cpu), float(mem)))

    chunk_history = load_chunk_history()
    metrics = {
        "rtf_points": sorted(rtf_points, key=lambda item: item[0]),
        "chunk_history": chunk_history,
        "engine_counts": engine_counts,
        "failure_counts": failure_counts,
        "system_points": sorted(system_points, key=lambda item: item[0]),
    }
    return metrics


def load_chunk_history(overrides_path: Path = OVERRIDES_PATH) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    if not overrides_path.exists():
        return history
    try:
        with overrides_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle) or {}
    except json.JSONDecodeError:
        return history
    overrides = data.get("overrides", {})
    current = (
        overrides.get("phase3", {}).get("chunk_size")
        if isinstance(overrides, dict)
        else None
    )
    if isinstance(current, dict):
        history.append(
            {
                "timestamp": data.get("updated"),
                "label": "current",
                "delta_percent": current.get("delta_percent", 0.0),
            }
        )
    for entry in data.get("history", []):
        timestamp = entry.get("timestamp")
        for change in entry.get("changes", []):
            path = change.get("path")
            if path and path.endswith("phase3.chunk_size"):
                value = change.get("value") or {}
                history.append(
                    {
                        "timestamp": timestamp,
                        "label": path,
                        "delta_percent": value.get("delta_percent", 0.0),
                    }
                )
    runtime_state = data.get("runtime_state", {}).get("last_run")
    if isinstance(runtime_state, dict):
        history.append(
            {
                "timestamp": runtime_state.get("timestamp"),
                "label": "last_run",
                "delta_percent": (
                    current.get("delta_percent", 0.0) if isinstance(current, dict) else 0.0
                ),
            }
        )
    return history


def _parse_ts(value: Any) -> float:
    if not value:
        return 0.0
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1]
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0
