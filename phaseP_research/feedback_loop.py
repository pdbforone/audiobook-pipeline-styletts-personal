"""Phase P: research feedback loop (append-only, observational)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter


def _load_history(history_path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if history_path.exists():
        with history_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    return records


def _write_history(history_path: Path, records: List[Dict[str, Any]]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec) + "\n")


def _build_aggregates(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_runs = len(records)
    user_intent_clusters: Counter = Counter()
    stylistic_trends: Counter = Counter()
    engine_pref: Counter = Counter()
    failure_hypotheses: Counter = Counter()

    for rec in records:
        analysis = rec.get("analysis", {}) if isinstance(rec, dict) else {}
        policy = analysis.get("policy_notes", {}) if isinstance(analysis, dict) else {}
        memory = analysis.get("memory_notes", {}) if isinstance(analysis, dict) else {}
        engine_usage = analysis.get("engine_usage", {}).get("frequency", {}) if isinstance(analysis, dict) else {}
        failures = analysis.get("failure_patterns", {}).get("counts", {}) if isinstance(analysis, dict) else {}

        for k, v in policy.items():
            if isinstance(v, str):
                user_intent_clusters.update([k])
        for k, v in memory.items():
            if isinstance(v, str):
                stylistic_trends.update([k])
        for eng, count in engine_usage.items():
            engine_pref.update([eng] * int(count or 1))
        for cat, count in failures.items():
            if count:
                failure_hypotheses.update([cat])

    aggregates = {
        "total_runs": total_runs,
        "user_intent_clusters": list(user_intent_clusters.keys()),
        "stylistic_trends": list(stylistic_trends.keys()),
        "engine_preference_signals": dict(engine_pref),
        "failure_hypotheses": list(failure_hypotheses.keys()),
    }
    return aggregates


def update_research_feedback(history: Dict[str, Any], latest_signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge long-horizon research signals with the latest insights.
    Append-only, never prescriptive, never modifies pipeline behavior.
    """
    out_dir = Path(".pipeline") / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    history_path = out_dir / "history.jsonl"
    aggregates_path = out_dir / "aggregates.json"

    records = _load_history(history_path)
    records.append(latest_signals)
    _write_history(history_path, records)

    aggregates = _build_aggregates(records)
    aggregates_path.write_text(json.dumps(aggregates, indent=2), encoding="utf-8")
    return aggregates
