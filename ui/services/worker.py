from __future__ import annotations

import asyncio
import threading
from typing import Any, Awaitable, Callable, Dict, Optional


class PipelineWorker:
    """Simple cancellable worker wrapper for pipeline runs."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._cancel_event = threading.Event()
        self._lock = asyncio.Lock()
        self._status: str = "idle"
        self._progress: float = 0.0
        self._last_message: str = ""

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(
        self,
        runner: Callable[[threading.Event, Callable[[float, Optional[str]], None]], Awaitable[Any]],
    ) -> Any:
        async with self._lock:
            if self.is_running:
                raise RuntimeError("A pipeline run is already in progress")
            self._cancel_event = threading.Event()
            self._status = "running"
            self._progress = 0.0
            self._last_message = ""
            self._task = asyncio.create_task(self._wrap_run(runner))
        return await self._task

    async def _wrap_run(
        self,
        runner: Callable[[threading.Event, Callable[[float, Optional[str]], None]], Awaitable[Any]],
    ) -> Any:
        try:
            return await runner(self._cancel_event, self._update_progress)
        except asyncio.CancelledError:
            self._status = "cancelled"
            raise
        except Exception as exc:
            self._status = f"error: {exc}"
            raise
        finally:
            self._cancel_event.set()

    def cancel(self) -> None:
        self._cancel_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            self._status = "cancelled"

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.is_running,
            "state": self._status,
            "progress": self._progress,
            "last_message": self._last_message,
        }

    def _update_progress(self, value: float, message: Optional[str] = None) -> None:
        self._progress = value
        if message:
            self._last_message = message
