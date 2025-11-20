from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

OVERRIDES_PATH = Path(".pipeline") / "tuning_overrides.json"


class TuningOverridesStore:
    """Manage human-approved overrides and runtime state."""

    def __init__(self, path: Path = OVERRIDES_PATH) -> None:
        self.path = path
        self.data = self._load()
        self._dirty = False

    def _load(self) -> Dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle) or {}
        except (FileNotFoundError, json.JSONDecodeError):
            payload = {}
        payload.setdefault("version", 1)
        payload.setdefault("overrides", {})
        payload.setdefault("history", [])
        payload.setdefault("runtime_state", {})
        return payload

    def get_phase_overrides(self, phase: str) -> Dict[str, Any]:
        overrides = self.data.setdefault("overrides", {})
        value = overrides.get(phase, {})
        return value if isinstance(value, dict) else {}

    def get_retry_overrides(self) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        overrides = self.data.setdefault("overrides", {})
        for phase, payload in overrides.items():
            if isinstance(payload, dict) and "retry_policy" in payload:
                retry = payload["retry_policy"]
                if isinstance(retry, dict):
                    results[phase] = retry
        return results

    def runtime_state(self) -> Dict[str, Any]:
        state = self.data.setdefault("runtime_state", {})
        if not isinstance(state, dict):
            state = {}
            self.data["runtime_state"] = state
        return state

    def mark_dirty(self) -> None:
        self._dirty = True

    def save_if_dirty(self) -> None:
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, sort_keys=True)
        self._dirty = False

    def build_run_overrides(self, stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Construct runtime overrides while honoring safety limits."""
        results: Dict[str, Any] = {}
        overrides = self.data.setdefault("overrides", {})
        state = self.runtime_state()

        if "voice_success_streak" not in state and stats:
            state["voice_success_streak"] = stats.get("recent_good_runs", 0)
            self.mark_dirty()

        phase3 = overrides.get("phase3", {})
        chunk_override = phase3.get("chunk_size")
        if isinstance(chunk_override, dict):
            chunk_payload = self._build_chunk_override(chunk_override)
            if chunk_payload:
                results.setdefault("phase3", {})["chunk_size"] = chunk_payload

        phase4 = overrides.get("phase4", {})
        engine_override = phase4.get("engine")
        if isinstance(engine_override, dict):
            engine_payload = self._build_engine_override(engine_override)
            if engine_payload:
                results.setdefault("phase4", {})["engine"] = engine_payload

        voice_override = phase4.get("voice_variant")
        if isinstance(voice_override, dict):
            voice_payload = self._build_voice_override(voice_override, state)
            if voice_payload:
                results.setdefault("phase4", {})["voice"] = voice_payload

        rtf_target = phase4.get("rtf_target")
        if isinstance(rtf_target, dict):
            target = rtf_target.get("target")
            try:
                target_value = max(1.0, float(target))
            except (TypeError, ValueError):
                target_value = 1.0
            results.setdefault("phase4", {})["rtf_target"] = {
                "target": target_value,
                "reason": rtf_target.get("reason"),
            }

        retry_overrides = self.get_retry_overrides()
        if retry_overrides:
            results["retry_policy"] = retry_overrides

        if results:
            results["metadata"] = {
                "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            }
        return results

    def apply_self_driving(self, stats: Optional[Dict[str, Any]]) -> None:
        if not stats:
            return
        adaptive = stats.get("adaptive_deltas") or {}
        safety = stats.get("safety_flags") or {}
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        chunk_delta = adaptive.get("chunk_size")
        if chunk_delta is not None:
            self._tune_chunk_from_reward(float(chunk_delta), bool(safety.get("revert_chunk")), timestamp)
        engine_bias = adaptive.get("engine_bias")
        if safety.get("revert_engine"):
            self._clear_engine_override()
        elif engine_bias and engine_bias > 0.05:
            self._promote_best_engine(stats, timestamp)
        if safety.get("voice_alert"):
            self._clear_voice_override()

    def _build_chunk_override(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mode = str(payload.get("mode") or "")
        if not mode:
            return None
        delta = payload.get("delta_percent", 15)
        try:
            delta_value = min(20.0, abs(float(delta)))
        except (TypeError, ValueError):
            delta_value = 15.0
        if "reduce" in mode.lower():
            signed = -delta_value
        elif "increase" in mode.lower() or "larger" in mode.lower():
            signed = delta_value
        else:
            return None
        return {
            "delta_percent": signed,
            "reason": payload.get("reason"),
            "source": payload.get("source"),
        }

    def _build_engine_override(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        confidence = payload.get("confidence")
        try:
            score = float(confidence)
        except (TypeError, ValueError):
            score = 0.0
        if score < 0.70:
            return None
        preferred = payload.get("preferred") or payload.get("engine")
        if not preferred:
            return None
        result = deepcopy(payload)
        result["preferred"] = preferred
        return result

    def _build_voice_override(self, payload: Dict[str, Any], state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        voice_id = payload.get("voice_id")
        if not voice_id:
            return None
        streak = state.get("voice_success_streak", 0)
        try:
            streak_value = int(streak)
        except (TypeError, ValueError):
            streak_value = 0
        if streak_value < 3:
            return None
        return deepcopy(payload)

    def record_run_outcome(
        self,
        *,
        run_id: str,
        success: bool,
        overrides: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        state = self.runtime_state()
        voice_applied = bool((overrides.get("phase4") or {}).get("voice"))
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        state["last_run"] = {
            "run_id": run_id,
            "timestamp": timestamp,
            "success": bool(success),
            "metadata": metadata or {},
            "overrides": {
                key: list(value.keys()) if isinstance(value, dict) else value
                for key, value in overrides.items()
            },
        }
        self._update_voice_streak(success, voice_applied)
        self.mark_dirty()

    def _update_voice_streak(self, success: bool, voice_override_applied: bool) -> None:
        state = self.runtime_state()
        streak = state.get("voice_success_streak", 0)
        try:
            streak_value = int(streak)
        except (TypeError, ValueError):
            streak_value = 0
        if not success:
            streak_value = 0
        elif voice_override_applied:
            streak_value = 0
        else:
            streak_value += 1
        state["voice_success_streak"] = streak_value
        self.mark_dirty()

    def _tune_chunk_from_reward(self, delta: float, revert: bool, timestamp: str) -> None:
        overrides = self.data.setdefault("overrides", {})
        phase3 = overrides.setdefault("phase3", {})
        entry = phase3.setdefault("chunk_size", {"mode": "increase_chunk_size"})
        current = entry.get("delta_percent", 0.0)
        try:
            current_value = float(current)
        except (TypeError, ValueError):
            current_value = 0.0
        if revert:
            new_value = 0.0
        else:
            new_value = current_value + max(-2.0, min(2.0, delta))
        new_value = max(-20.0, min(20.0, new_value))
        entry["delta_percent"] = round(new_value, 2)
        entry["mode"] = "reduce_chunk_size" if new_value < 0 else "increase_chunk_size"
        entry["reason"] = "Self-driving adaptive tuning"
        entry["source"] = "self_driving"
        entry["updated_at"] = timestamp
        self.mark_dirty()

    def _clear_engine_override(self) -> None:
        phase4 = self.data.setdefault("overrides", {}).get("phase4")
        if isinstance(phase4, dict) and "engine" in phase4:
            phase4.pop("engine", None)
            self.mark_dirty()

    def _clear_voice_override(self) -> None:
        phase4 = self.data.setdefault("overrides", {}).get("phase4")
        if isinstance(phase4, dict) and "voice_variant" in phase4:
            phase4.pop("voice_variant", None)
            self.mark_dirty()

    def _promote_best_engine(self, stats: Dict[str, Any], timestamp: str) -> None:
        engine_rel = stats.get("engine_reliability") or {}
        if not engine_rel:
            return
        best_engine, best_score = max(engine_rel.items(), key=lambda item: item[1])
        overrides = self.data.setdefault("overrides", {})
        phase4 = overrides.setdefault("phase4", {})
        entry = phase4.setdefault("engine", {})
        entry["preferred"] = best_engine
        entry["confidence"] = best_score
        entry["reason"] = "Self-driving engine selection"
        entry["source"] = "self_driving"
        entry["updated_at"] = timestamp
        self.mark_dirty()
