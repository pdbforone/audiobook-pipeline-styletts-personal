"""Phase P: lightweight, opt-in research data collection."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List

from .research_config import ResearchConfig


class ResearchCollector:
    def __init__(self, cfg: ResearchConfig):
        self.cfg = cfg

    def _collect_phase_metrics(self, run_state: Dict[str, Any]) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}
        for phase_key, phase_data in run_state.items():
            if not phase_key.startswith("phase"):
                continue
            if isinstance(phase_data, dict):
                metrics[phase_key] = {
                    "status": phase_data.get("status"),
                    "timestamps": phase_data.get("timestamps"),
                    "metrics": phase_data.get("metrics"),
                }
        return metrics

    def _collect_failures(self, run_state: Dict[str, Any]) -> Dict[str, Any]:
        patterns = {
            "tts_failure": re.compile(r"tts", re.IGNORECASE),
            "extraction_failure": re.compile(r"extract|pdf|ocr", re.IGNORECASE),
            "chunk_failure": re.compile(r"chunk", re.IGNORECASE),
        }
        failures: Dict[str, List[str]] = {}
        for phase_key, phase_data in run_state.items():
            if not isinstance(phase_data, dict):
                continue
            errors = phase_data.get("errors") or []
            if isinstance(errors, list):
                for err in errors:
                    if not isinstance(err, str):
                        continue
                    for label, rx in patterns.items():
                        if rx.search(err):
                            failures.setdefault(label, []).append(err)
        return failures

    def _collect_engine_stats(self, run_state: Dict[str, Any]) -> Dict[str, Any]:
        phase4 = run_state.get("phase4", {}) if isinstance(run_state, dict) else {}
        files = phase4.get("files", {}) if isinstance(phase4, dict) else {}
        stats: Dict[str, Any] = {}
        for file_id, data in files.items():
            if not isinstance(data, dict):
                continue
            stats[file_id] = {
                "engine_used": data.get("engine_used"),
                "rtf": data.get("rt_factor"),
                "duration_sec": data.get("duration_sec"),
            }
        return stats

    def _collect_chunk_stats(self, run_state: Dict[str, Any]) -> Dict[str, Any]:
        phase3 = run_state.get("phase3", {}) if isinstance(run_state, dict) else {}
        files = phase3.get("files", {}) if isinstance(phase3, dict) else {}
        stats: Dict[str, Any] = {}
        for file_id, data in files.items():
            if not isinstance(data, dict):
                continue
            chunks = data.get("chunk_paths") or []
            stats[file_id] = {
                "chunk_count": len(chunks) if isinstance(chunks, list) else 0,
                "chunks": list(chunks) if isinstance(chunks, list) else [],
            }
        return stats

    def _collect_memory_signals(self) -> Dict[str, Any]:
        memory_dir = Path(".pipeline") / "memory"
        if not memory_dir.exists():
            return {}
        files = sorted(memory_dir.glob("*.json"))
        return {"memory_files": [str(p) for p in files]}

    def _collect_policy_signals(self) -> Dict[str, Any]:
        policy_dir = Path(".pipeline") / "policy_logs"
        if not policy_dir.exists():
            return {}
        logs = sorted(policy_dir.glob("*.log"))
        last_log = logs[-1] if logs else None
        content = ""
        if last_log and last_log.is_file():
            try:
                content = last_log.read_text(encoding="utf-8")[-4000:]
            except Exception:
                content = ""
        return {
            "policy_logs": [str(p) for p in logs],
            "latest_snippet": content,
        }

    def collect(self, run_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pure function: returns a dict containing ONLY the research-relevant
        raw data from the run_state, following the flags in the config.
        Never mutates run_state.
        Never modifies pipeline behavior.
        """
        if not self.cfg.enable_research:
            return {}

        result: Dict[str, Any] = {}
        if self.cfg.collect_phase_metrics:
            result["phase_metrics"] = self._collect_phase_metrics(run_state)
        if self.cfg.collect_failure_patterns:
            result["failure_patterns"] = self._collect_failures(run_state)
        if self.cfg.collect_engine_stats:
            result["engine_stats"] = self._collect_engine_stats(run_state)
        if self.cfg.collect_chunk_stats:
            result["chunk_stats"] = self._collect_chunk_stats(run_state)
        if self.cfg.collect_memory_signals:
            result["memory_signals"] = self._collect_memory_signals()
        if self.cfg.collect_policy_signals:
            result["policy_signals"] = self._collect_policy_signals()
        return result
