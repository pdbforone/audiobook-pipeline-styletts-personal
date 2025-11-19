from __future__ import annotations

import asyncio
import logging
import math
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from phase6_orchestrator.orchestrator import run_pipeline
from pipeline_common import PipelineState, StateError

from ui.models import (
    FileSystemProgress,
    IncompleteWork,
    Phase4ChunkSummary,
    Phase4Summary,
    PhaseStatusSummary,
    PipelineStatus,
)

logger = logging.getLogger(__name__)


class PipelineAPI:
    """Single entry point for pipeline state, logs, and orchestration."""

    def __init__(self, project_root: Path, log_files: Optional[Dict[str, Path]] = None) -> None:
        self.project_root = Path(project_root).resolve()
        self.state = PipelineState(self.project_root / "pipeline.json")
        self.log_files = log_files or {}
        self._cancel_event = threading.Event()

    @property
    def pipeline_path(self) -> Path:
        return self.state.path

    def reset_cancel(self) -> None:
        self._cancel_event.clear()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    # ------------------------------------------------------------------ #
    # State accessors
    # ------------------------------------------------------------------ #
    def _read_state(self) -> Dict[str, Any]:
        try:
            return self.state.read(validate=False)
        except (StateError, FileNotFoundError) as exc:
            logger.warning("Pipeline state unavailable: %s", exc)
            return {}
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unexpected state read failure: %s", exc)
            return {}

    def _collect_file_ids(self, data: Dict[str, Any]) -> List[str]:
        """Return all known file_ids from the canonical phase-first schema."""
        file_ids: set[str] = set()
        for phase_key in ["phase1", "phase2", "phase3", "phase4", "phase5"]:
            phase_block = data.get(phase_key) or {}
            files = phase_block.get("files") or {}
            if isinstance(files, dict):
                file_ids.update(files.keys())
        if not file_ids and isinstance(data.get("file_id"), str):
            file_ids.add(data["file_id"])
        return sorted(file_ids)

    def write_state(self, data: Dict[str, Any], validate: bool = True) -> bool:
        """Persist pipeline state atomically."""
        try:
            self.state.write(data, validate=validate)
            return True
        except Exception as exc:
            logger.warning("Failed to write pipeline state: %s", exc)
            return False

    def get_file_ids(self) -> List[str]:
        data = self._read_state()
        try:
            return self._collect_file_ids(data)
        except Exception as exc:
            logger.warning("Failed to list file ids: %s", exc)
            return []

    def check_incomplete_work(self) -> Optional[IncompleteWork]:
        data = self._read_state()
        try:
            for file_id in self._collect_file_ids(data):
                phases_complete: List[int] = []
                phases_incomplete: List[int] = []

                for phase in [1, 2, 3, 4, 5]:
                    status = self._phase_status(data, file_id, phase)
                    if status == "success":
                        phases_complete.append(phase)
                    else:
                        phases_incomplete.append(phase)

                if phases_complete and phases_incomplete:
                    return IncompleteWork(
                        file_id=file_id,
                        phases_complete=phases_complete,
                        phases_incomplete=phases_incomplete,
                        last_phase=max(phases_complete) if phases_complete else 0,
                    )
        except Exception as exc:
            logger.warning("Failed to detect incomplete work: %s", exc)
        return None

    def _phase_status(self, data: Dict[str, Any], file_id: str, phase_num: int) -> str:
        phase_key = f"phase{phase_num}"
        try:
            phase = data.get(phase_key, {}) or {}
            files = phase.get("files", {}) or {}
            entry = files.get(file_id, {}) if isinstance(files, dict) else {}
            return entry.get("status") or phase.get("status") or "missing"
        except Exception:
            return "unknown"

    def _process_snapshot(self) -> List[str]:
        lines: List[str] = []
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_info"]):
                cmd = " ".join(proc.info.get("cmdline") or [])[:120]
                name = proc.info.get("name") or ""
                if any(key in cmd for key in ["phase4", "phase5", "orchestrator.py"]):
                    mem_info = proc.info.get("memory_info")
                    mem_mb = (mem_info.rss if mem_info else 0) / (1024 * 1024)
                    lines.append(
                        f"- PID {proc.pid}: {name} ({cmd}) | CPU {proc.info.get('cpu_percent',0):.1f}% | RAM {mem_mb:.0f} MB"
                    )
        except Exception as exc:
            lines.append(f"- (process scan failed: {exc})")
        return lines

    def _count_files(self, pattern: str) -> int:
        try:
            return len(list(self.project_root.glob(pattern)))
        except Exception:
            return 0

    def get_status(self, file_id: Optional[str]) -> Optional[PipelineStatus]:
        if not file_id:
            return None

        data = self._read_state()
        phases = [PhaseStatusSummary(phase=p, status=self._phase_status(data, file_id, p)) for p in range(1, 6)]

        fs_progress = FileSystemProgress(
            chunk_txt=self._count_files(f"phase3-chunking/chunks/{file_id}_chunk_*.txt"),
            phase4_wav=self._count_files("phase4_tts/audio_chunks/*.wav"),
            phase5_wav=self._count_files("phase5_enhancement/processed/enhanced_*.wav"),
            mp3_exists=(self.project_root / "phase5_enhancement" / "processed" / "audiobook.mp3").exists(),
        )

        return PipelineStatus(file_id=file_id, phases=phases, fs_progress=fs_progress, processes=self._process_snapshot())

    # ------------------------------------------------------------------ #
    # Phase 4 summary
    # ------------------------------------------------------------------ #
    def get_phase4_summary(self, file_id: Optional[str], page: int = 1, page_size: int = 20) -> Optional[Phase4Summary]:
        if not file_id:
            return None

        data = self._read_state()
        try:
            phase4_files = (data.get("phase4", {}) or {}).get("files", {}) or {}
            entry = phase4_files.get(file_id)
            if not entry or not isinstance(entry, dict):
                return None

            chunk_keys = sorted([k for k in entry.keys() if k.startswith("chunk_")])
            page = max(1, int(page))
            page_size = max(1, min(100, int(page_size)))
            start = (page - 1) * page_size
            subset = chunk_keys[start : start + page_size]

            rows: List[Phase4ChunkSummary] = []
            for cid in subset:
                meta = entry.get(cid)
                status = "-"
                engine = "-"
                rt_factor: Optional[float] = None
                audio_path = "-"
                if isinstance(meta, dict):
                    status = meta.get("status") or meta.get("state") or "-"
                    engine = meta.get("engine_used") or meta.get("engine") or "-"
                    rt_factor = meta.get("rt_factor") if isinstance(meta.get("rt_factor"), (int, float)) else None
                    audio_path = meta.get("output_path") or meta.get("path") or meta.get("chunk_audio_path") or "-"
                elif isinstance(meta, (list, tuple)) and meta:
                    audio_path = str(meta[0])
                elif meta is not None:
                    audio_path = str(meta)
                rows.append(Phase4ChunkSummary(chunk_id=cid, status=status, engine=engine, rt_factor=rt_factor, audio_path=str(audio_path)))

            total_chunks = entry.get("total_chunks") or len(chunk_keys)
            completed = entry.get("chunks_completed") or 0
            failed = entry.get("chunks_failed") or 0
            duration_sec = entry.get("duration_seconds")
            requested_engine = entry.get("requested_engine") or entry.get("engine") or "unknown"
            total_pages = max(1, math.ceil(len(chunk_keys) / page_size)) if chunk_keys else 1

            return Phase4Summary(
                file_id=file_id,
                requested_engine=requested_engine,
                total_chunks=total_chunks or len(chunk_keys),
                completed=completed or 0,
                failed=failed or 0,
                duration_seconds=duration_sec if isinstance(duration_sec, (int, float)) else None,
                page=page,
                total_pages=total_pages,
                chunks=rows,
            )
        except Exception as exc:
            logger.warning("Failed to build Phase 4 summary: %s", exc)
            return None

    # ------------------------------------------------------------------ #
    # Logs
    # ------------------------------------------------------------------ #
    def tail_log(self, log_key: str, lines: int = 200) -> str:
        path = self.log_files.get(log_key)
        if not path:
            return "Log not found."
        if not path.exists():
            return f"Log not found at {path}"

        try:
            with open(path, "rb") as f:
                f.seek(0, 2)
                end = f.tell()
                block = 4096
                buffer = b""
                while len(buffer.splitlines()) <= lines and f.tell() > 0:
                    seek_pos = max(0, f.tell() - block)
                    f.seek(seek_pos)
                    buffer = f.read(end - seek_pos) + buffer
                    f.seek(seek_pos)
                    if seek_pos == 0:
                        break
                tail = b"\n".join(buffer.splitlines()[-lines:])
            return tail.decode("utf-8", errors="replace") or "(empty log)"
        except Exception as exc:
            logger.warning("Failed to tail log %s: %s", log_key, exc)
            return f"Failed to read log: {exc}"

    # ------------------------------------------------------------------ #
    # Orchestration
    # ------------------------------------------------------------------ #
    async def run_pipeline_async(
        self,
        *,
        file_path: Path,
        voice_id: str,
        tts_engine: str,
        mastering_preset: str,
        phases: List[int],
        enable_subtitles: bool,
        max_retries: int,
        no_resume: bool,
        concat_only: bool,
        progress_callback: Any = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        cancel_handle = cancel_event or self._cancel_event
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                self._run_pipeline_sync,
                file_path,
                voice_id,
                tts_engine,
                mastering_preset,
                phases,
                enable_subtitles,
                max_retries,
                no_resume,
                concat_only,
                progress_callback,
                cancel_handle,
            )
        except Exception as exc:
            logger.exception("Pipeline execution failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def _run_pipeline_sync(
        self,
        file_path: Path,
        voice_id: str,
        tts_engine: str,
        mastering_preset: str,
        phases: List[int],
        enable_subtitles: bool,
        max_retries: int,
        no_resume: bool,
        concat_only: bool,
        progress_callback: Any,
        cancel_handle: threading.Event,
    ) -> Dict[str, Any]:
        def wrapped_progress(phase: int, percentage: float, message: str) -> None:
            if cancel_handle.is_set():
                raise KeyboardInterrupt("Pipeline cancelled by user")
            if progress_callback:
                try:
                    progress_callback((phase - 1) / 7 + percentage / 700, desc=f"Phase {phase}: {message}")
                except Exception:
                    # Progress callbacks should never break the pipeline
                    logger.debug("Progress callback failed", exc_info=True)

        try:
            return run_pipeline(
                file_path=file_path,
                voice_id=voice_id,
                tts_engine=tts_engine,
                mastering_preset=mastering_preset,
                phases=phases,
                pipeline_json=self.pipeline_path,
                enable_subtitles=enable_subtitles,
                max_retries=int(max_retries),
                no_resume=no_resume,
                progress_callback=wrapped_progress,
                concat_only=concat_only,
            )
        except KeyboardInterrupt:
            logger.info("Pipeline run cancelled by user")
            return {"success": False, "error": "cancelled"}
        except Exception as exc:
            logger.exception("Pipeline run failed: %s", exc)
            return {"success": False, "error": str(exc)}
