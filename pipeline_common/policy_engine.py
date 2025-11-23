from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

try:  # pragma: no cover - psutil is optional
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore

from policy_engine.advisor import PolicyAdvisor
from policy_engine.policy_engine import TuningOverridesStore

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    pass


POLICY_ENGINE_VERSION = "3.0"


class PolicyEngine:
    """Non-intervention policy observer/advisor."""

    def __init__(
        self,
        *,
        logging_enabled: bool = True,
        learning_mode: str = "observe",
        advisor: Optional[PolicyAdvisor] = None,
        run_id: Optional[str] = None,
    ) -> None:
        self.logging_enabled = logging_enabled
        self.learning_mode = learning_mode
        self._log_root = Path(".pipeline") / "policy_logs"
        self._lock = threading.Lock()
        self._current_day: Optional[str] = None
        self._handle: Optional[Any] = None
        self._advisor = advisor or PolicyAdvisor(log_root=self._log_root)
        self._override_store = TuningOverridesStore()
        self._active_overrides: Dict[str, Any] = {}
        self._run_id = run_id or self._generate_run_id()
        self._sequence = 0

    # ------------------------------------------------------------------ #
    # Public hooks
    # ------------------------------------------------------------------ #
    @property
    def run_id(self) -> str:
        return self._run_id

    def start_new_run(self, run_id: Optional[str] = None) -> None:
        """Reset the per-run identifiers so downstream logs can separate executions."""
        with self._lock:
            self._run_id = run_id or self._generate_run_id()
            self._sequence = 0
            self._active_overrides = {}

    def record_phase_start(self, ctx: Dict[str, Any]) -> None:
        payload = dict(ctx)
        payload.setdefault("status", "starting")
        payload["event"] = payload.get("event") or "phase_start"
        self._record_event(payload)

    def record_phase_end(self, ctx: Dict[str, Any]) -> None:
        payload = dict(ctx)
        payload.setdefault("status", "success")
        payload["event"] = payload.get("event") or "phase_end"
        self._record_event(payload)

    def record_retry(self, ctx: Dict[str, Any]) -> None:
        payload = dict(ctx)
        payload.setdefault("status", "retry")
        payload["event"] = payload.get("event") or "phase_retry"
        self._record_event(payload)

    def record_failure(self, ctx: Dict[str, Any]) -> None:
        payload = dict(ctx)
        payload.setdefault("status", "failed")
        payload["event"] = payload.get("event") or "phase_failure"
        self._record_event(payload)

    def advise(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Return advisory hints derived from accumulated logs."""
        try:
            return self._advisor.advise(ctx)
        except Exception:  # pragma: no cover - defensive
            return {}

    def prepare_run_overrides(
        self, *, file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load tuning overrides and cache the active set for this run."""
        stats = self._advisor.snapshot()
        self._active_overrides = self._override_store.build_run_overrides(
            stats
        )
        if file_id:
            self._active_overrides.setdefault("metadata", {})[
                "file_id"
            ] = file_id
        return self._active_overrides

    def get_active_overrides(self) -> Dict[str, Any]:
        return self._active_overrides or {}

    def complete_run(
        self, *, success: bool, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        stats = self._advisor.snapshot()
        self._override_store.apply_self_driving(stats)
        self._override_store.record_run_outcome(
            run_id=self._run_id,
            success=success,
            overrides=self.get_active_overrides(),
            metadata=metadata,
        )
        self._override_store.save_if_dirty()

    def close(self) -> None:
        with self._lock:
            if self._handle:
                try:
                    self._handle.close()
                except Exception:  # pragma: no cover - defensive
                    pass
                finally:
                    self._handle = None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _record_event(self, payload: Dict[str, Any]) -> None:
        if not self.logging_enabled:
            return

        enriched = dict(payload)
        enriched.setdefault(
            "timestamp",
            datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        )
        enriched.setdefault("learning_mode", self.learning_mode)
        enriched.setdefault("policy_version", POLICY_ENGINE_VERSION)
        enriched.setdefault("run_id", self._run_id)
        enriched.setdefault("sequence", self._next_sequence())
        stats = self._system_stats()
        enriched.setdefault("system_load", stats["system_load"])
        enriched.setdefault("cpu_percent", stats["cpu_percent"])
        enriched.setdefault("memory_percent", stats["memory_percent"])

        with self._lock:
            handle = self._ensure_log_handle_locked()
            if not handle:
                return
            handle.write(
                json.dumps(
                    enriched, default=self._json_default, ensure_ascii=False
                )
                + "\n"
            )
            handle.flush()

    def _ensure_log_handle_locked(self) -> Optional[Any]:
        day = datetime.utcnow().strftime("%Y%m%d")
        if self._handle and self._current_day == day:
            return self._handle

        try:
            self._log_root.mkdir(parents=True, exist_ok=True)
        except Exception:
            return None

        if self._handle:
            try:
                self._handle.close()
            except Exception:
                pass

        log_path = self._log_root / f"{day}.log"
        try:
            self._handle = log_path.open("a", encoding="utf-8")
            self._current_day = day
        except Exception:
            self._handle = None
        return self._handle

    def _system_stats(self) -> Dict[str, Any]:
        if not psutil:
            return {
                "system_load": None,
                "cpu_percent": None,
                "memory_percent": None,
            }

        load: Optional[Any]
        try:
            load = psutil.getloadavg()  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            load = None

        try:
            cpu_percent = psutil.cpu_percent(interval=None)
        except Exception:
            cpu_percent = None

        try:
            memory_percent = psutil.virtual_memory().percent
        except Exception:
            memory_percent = None

        return {
            "system_load": load,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
        }

    @staticmethod
    def _json_default(value: Any) -> Any:  # pragma: no cover - defensive
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        try:
            return str(value)
        except Exception:
            return "unserializable"

    @staticmethod
    def _generate_run_id() -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        return f"run-{timestamp}-{uuid.uuid4().hex[:8]}"

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def __del__(self) -> None:  # pragma: no cover - defensive
        try:
            self.close()
        except Exception:
            pass
