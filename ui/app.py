
#!/usr/bin/env python3
"""
🎙️ Personal Audiobook Studio

Refactored Gradio UI with safe state management, background workers,
and a clear API boundary to the orchestrator pipeline.
"""

from __future__ import annotations

import atexit
from dataclasses import dataclass
import logging
import os
import signal
import socket
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional, Tuple

import gradio as gr
import yaml

# Add project root to path before importing pipeline modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_common import PHASE_KEYS  # noqa: E402
from ui.models import FileSystemProgress, Phase4Summary, PhaseStatusSummary, UISettings  # noqa: E402
from ui.services.pipeline_api import PipelineAPI  # noqa: E402
from ui.services.settings_manager import SettingsManager  # noqa: E402
from ui.services.voice_manager import VoiceManager  # noqa: E402
from ui.services.worker import PipelineWorker  # noqa: E402


VOICE_CONFIG_PATH = PROJECT_ROOT / "phase4_tts" / "configs" / "voice_references.json"
CUSTOM_VOICE_DIR = PROJECT_ROOT / "voice_samples" / "custom"
SETTINGS_PATH = PROJECT_ROOT / ".pipeline" / "ui_settings.json"
LOG_FILES = {
    "Phase 4 (XTTS)": PROJECT_ROOT / "xtts_chunk.log",
    "Pipeline (orchestrator)": PROJECT_ROOT / "phase6_orchestrator" / "orchestrator.log",
    "Phase 5 (enhancement)": PROJECT_ROOT / "phase5_enhancement" / "enhancement.log",
}

ENGINE_MAP = {
    "XTTS v2 (Expressive)": "xtts",
    "Kokoro (CPU-Friendly)": "kokoro",
}

PHASE_DEFINITIONS: List[tuple[str, float, str]] = [
    ("phase1", 1, "Phase 1 – Validation"),
    ("phase2", 2, "Phase 2 – Extraction"),
    ("phase3", 3, "Phase 3 – Chunking"),
    ("phase4", 4, "Phase 4 – Text-to-Speech"),
    ("phase5", 5, "Phase 5 – Enhancement"),
    ("phase5_5", 5.5, "Phase 5.5 – Subtitles"),
]
PHASE_TITLE_MAP = {key: label for key, _, label in PHASE_DEFINITIONS}
PHASE_ORDER_MAP = {key: order for key, order, _ in PHASE_DEFINITIONS}
AVAILABLE_PHASE_KEYS = [key for key, _, _ in PHASE_DEFINITIONS if key in PHASE_KEYS]
PHASE_CHOICE_LOOKUP = {key: f"{key}: {PHASE_TITLE_MAP[key]}" for key in AVAILABLE_PHASE_KEYS}
PHASE_CHOICE_VALUES = [PHASE_CHOICE_LOOKUP[key] for key in AVAILABLE_PHASE_KEYS]
DEFAULT_PHASE_SELECTION = [PHASE_CHOICE_LOOKUP[key] for key in AVAILABLE_PHASE_KEYS if key != "phase5_5"]
RUNNABLE_PHASES = []
for phase_key in AVAILABLE_PHASE_KEYS:
    if phase_key == "phase5_5":
        continue
    order_value = PHASE_ORDER_MAP.get(phase_key)
    if isinstance(order_value, (int, float)):
        RUNNABLE_PHASES.append(int(order_value))
PHASE_CHOICE_TO_KEY = {value: key for key, value in PHASE_CHOICE_LOOKUP.items()}
STATUS_BADGES = {
    "success": "**success**",
    "failed": "**failed**",
    "error": "**error**",
    "running": "**running**",
    "pending": "**pending**",
    "partial": "**partial**",
    "partial_success": "**partial success**",
    "skipped": "**skipped**",
    "missing": "**N/A**",
    "unknown": "**unknown**",
}
SUBTITLE_PHASE_KEY = "phase5_5"

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM CSS
# ============================================================================

CUSTOM_CSS = """
/* Modern palette: navy base with orange accents */
:root {
    --primary-color: #0b1d3a;
    --secondary-color: #f97316;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
    --bg-gradient: linear-gradient(135deg, #0b1d3a 0%, #10294f 50%, #1f3f6b 100%);
}

.gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    max-width: 1400px;
    margin: 0 auto;
}

/* Header styling */
.header {
    background: var(--bg-gradient);
    color: white;
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 15px 35px rgba(0,0,0,0.25);
}

.header h1 {
    margin: 0;
    font-size: 2.5rem;
    font-weight: 800;
    letter-spacing: -0.5px;
}

.header p {
    margin: 0.5rem 0 0 0;
    opacity: 0.9;
    font-size: 1.05rem;
}

/* Tab styling */
.tab-nav {
    border-bottom: 2px solid #e5e7eb;
    margin-bottom: 1.5rem;
}

/* Buttons */
.primary-button {
    background: var(--bg-gradient) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
    transition: all 0.2s;
}

.primary-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(249, 115, 22, 0.35);
}

.secondary-button {
    background: white !important;
    color: var(--primary-color) !important;
    border: 1px solid var(--primary-color) !important;
    font-weight: 600;
}

/* Card styling */
.card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    margin-bottom: 1rem;
}

/* Progress bar styling */
.progress-bar {
    background: var(--bg-gradient);
    height: 8px;
    border-radius: 4px;
    transition: width 0.3s;
}

/* Voice card styling */
.voice-card {
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    transition: all 0.2s;
}

.voice-card:hover {
    border-color: var(--secondary-color);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

"""


@dataclass
class UIState:
    """Session-scoped UI state to avoid cross-user leaking."""

    pipeline_api: PipelineAPI
    worker: PipelineWorker
    active_job: Optional[str] = None
    phase4_page: int = 1
    phase4_page_size: int = 20
    phase5_page: int = 1
    phase5_page_size: int = 10

    @property
    def is_running(self) -> bool:
        return self.worker.is_running

    def mark_job(self, job: str) -> None:
        self.active_job = job

    def clear_job(self) -> None:
        self.active_job = None


class StudioUI:
    """Main UI orchestrator with explicit state injection."""

    def __init__(self) -> None:
        self.voice_manager = VoiceManager(VOICE_CONFIG_PATH, CUSTOM_VOICE_DIR)
        self.settings_manager = SettingsManager(SETTINGS_PATH, PROJECT_ROOT)
        self.settings: UISettings = self.settings_manager.load()
        self.presets = self._load_presets()

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #
    def _create_ui_state(self) -> UIState:
        """Create a session-scoped state container."""
        return UIState(pipeline_api=PipelineAPI(PROJECT_ROOT, log_files=LOG_FILES), worker=PipelineWorker())

    @staticmethod
    def _show_stop_button():
        return gr.update(visible=True)

    @staticmethod
    def _hide_stop_button():
        return gr.update(visible=False)

    @staticmethod
    def _safe_progress(progress_fn: Any, value: float, desc: Optional[str] = None) -> None:
        """Best-effort progress updates that never throw."""
        if not progress_fn:
            return
        try:
            progress_fn(value, desc=desc)
        except Exception:
            logger.debug("Progress callback failed", exc_info=True)

    @staticmethod
    def _run_background(func: Callable[..., Awaitable[Any]], *args, **kwargs):
        """Schedule coroutine work without blocking the Gradio event loop."""
        return gr.utils.run_coro_in_background(func, *args, **kwargs)

    def _build_voice_gallery_html(self) -> str:
        html = '<div style="display: grid; gap: 1rem;">'
        voices = self.voice_manager.refresh()
        for voice_id, meta in list(voices.items())[:10]:
            profiles = ", ".join(meta.preferred_profiles)
            html += f"""
            <div class="voice-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 1.1rem;">{meta.narrator_name}</strong>
                        <p style="margin: 0.25rem 0; opacity: 0.7; font-size: 0.9rem;">{profiles}</p>
                        <p style="margin: 0.25rem 0; opacity: 0.5; font-size: 0.85rem;">{voice_id}</p>
                    </div>
                    <div>
                        <button style="padding: 0.5rem; margin: 0 0.25rem; cursor: pointer;">🎧</button>
                        <button style="padding: 0.5rem; margin: 0 0.25rem; cursor: pointer;">✏️</button>
                    </div>
                </div>
            </div>
            """
        html += "</div>"
        return html

    @staticmethod
    def _phase_choice_list() -> List[str]:
        return list(PHASE_CHOICE_VALUES)

    @staticmethod
    def _default_phase_choices() -> List[str]:
        return list(DEFAULT_PHASE_SELECTION)

    @staticmethod
    @staticmethod
    def _choice_to_phase_key(choice: Optional[str]) -> Optional[str]:
        text = (choice or "").strip()
        if not text:
            return None
        direct = PHASE_CHOICE_TO_KEY.get(text)
        if direct:
            return direct
        prefix = text.split(":", 1)[0].strip().lower()
        if not prefix:
            return None
        normalized = prefix.replace(" ", "").replace(".", "_")
        if normalized in PHASE_TITLE_MAP:
            return normalized
        if normalized.startswith("phase"):
            candidate = normalized
        else:
            candidate = f"phase{normalized}"
        if candidate in PHASE_TITLE_MAP:
            return candidate
        return None

    def _parse_phase_choices(self, choices: Optional[List[str]]) -> Tuple[List[int], bool]:
        parsed: List[int] = []
        subtitles_selected = False
        if not choices:
            return parsed, subtitles_selected
        for choice in choices:
            phase_key = self._choice_to_phase_key(choice)
            if not phase_key:
                continue
            if phase_key == SUBTITLE_PHASE_KEY:
                subtitles_selected = True
                continue
            order_value = PHASE_ORDER_MAP.get(phase_key)
            if not isinstance(order_value, (int, float)):
                continue
            phase_number = int(order_value)
            if phase_number not in RUNNABLE_PHASES:
                continue
            if phase_number not in parsed:
                parsed.append(phase_number)
        return parsed, subtitles_selected

    @staticmethod
    def _phase_key_from_number(value: Any) -> str:
        if isinstance(value, float):
            if value.is_integer():
                suffix = str(int(value))
            else:
                suffix = str(value).replace(".", "_")
        elif isinstance(value, int):
            suffix = str(value)
        else:
            suffix = str(value)
        return f"phase{suffix}"

    @staticmethod
    def _phase_label_from_key(phase_key: str, fallback: Optional[str] = None) -> str:
        if phase_key in PHASE_TITLE_MAP:
            return PHASE_TITLE_MAP[phase_key]
        if fallback:
            return fallback
        if phase_key.startswith("phase"):
            return f"Phase {phase_key.replace('phase', '').replace('_', '.')}"
        return phase_key

    def _format_phase_selection(self, phases: List[int], include_subtitles: bool = False) -> str:
        labels = []
        for phase in phases:
            phase_key = self._phase_key_from_number(phase)
            labels.append(self._phase_label_from_key(phase_key, f"Phase {phase}"))
        if include_subtitles and SUBTITLE_PHASE_KEY in PHASE_TITLE_MAP:
            labels.append(PHASE_TITLE_MAP[SUBTITLE_PHASE_KEY])
        if not labels:
            return "none"
        return ", ".join(labels)

    @classmethod
    def _format_phase_numbers(cls, phases: List[float]) -> str:
        if not phases:
            return "none"
        labels = []
        for phase in phases:
            phase_key = cls._phase_key_from_number(phase)
            labels.append(PHASE_TITLE_MAP.get(phase_key, f"Phase {phase}"))
        return ", ".join(labels)

    def _load_presets(self) -> List[str]:
        presets_path = PROJECT_ROOT / "phase5_enhancement" / "presets" / "mastering_presets.yaml"
        try:
            with open(presets_path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            presets = list((data.get("presets") or {}).keys())
            return presets or ["audiobook_intimate", "audiobook_dynamic", "podcast_standard"]
        except Exception as exc:
            logger.warning("Failed to load mastering presets: %s", exc)
            return ["audiobook_intimate", "audiobook_dynamic", "podcast_standard"]

    def _format_status(self, pipeline_api: PipelineAPI, file_id: Optional[str]) -> str:
        status = pipeline_api.get_status(file_id)
        if not status:
            return "Select a file to view pipeline status."

        phase_lines = [self._format_phase_status_line(summary) for summary in status.phases]
        fs: FileSystemProgress = status.fs_progress
        process_view = "\n".join(status.processes) if status.processes else "- No active pipeline processes detected"

        return f"""
### Pipeline Status for `{status.file_id}`

**Phases**
{chr(10).join(phase_lines)}

**File System Progress (live)**
- Phase 3 chunks (txt): {fs.chunk_txt}
- Phase 4 audio chunks (wav): {fs.phase4_wav}
- Phase 5 enhanced (wav): {fs.phase5_wav}
- Final MP3 present: {"yes" if fs.mp3_exists else "no"}

**Active Processes**
{process_view}
"""

    def _format_phase_status_line(self, summary: PhaseStatusSummary) -> str:
        label = self._phase_label_from_key(summary.key, summary.label)
        status_value = (summary.status or "unknown").lower()
        status_display = STATUS_BADGES.get(status_value, f"**{summary.status or 'unknown'}**")
        detail = ""
        if summary.key == SUBTITLE_PHASE_KEY:
            detail = self._subtitle_status_detail(status_value, summary.errors)
        elif status_value == "missing":
            detail = " – Not available"
        elif summary.errors and status_value in {"failed", "error", "partial", "partial_success"}:
            detail = f" – {summary.errors[0]}"
        return f"- {label}: {status_display}{detail}"

    @staticmethod
    def _subtitle_status_detail(status_value: str, errors: List[str]) -> str:
        if status_value == "success":
            return " – Subtitles done"
        if status_value in {"failed", "error"} or errors:
            message = errors[0] if errors else ""
            suffix = f": {message}" if message else ""
            return f" – Subtitles issue{suffix}"
        if status_value == "running":
            return " – Subtitles in progress"
        if status_value == "pending":
            return " – Subtitles queued"
        if status_value in {"partial", "partial_success"}:
            return " – Subtitles partially complete"
        if status_value == "missing":
            return " – Subtitles not requested"
        return ""

    def _format_phase4_summary(self, summary: Optional[Phase4Summary]) -> str:
        if not summary:
            return "Select a file to view Phase 4 summary."

        chunk_section = []
        for chunk in summary.chunks:
            rt = f"{chunk.rt_factor:.2f}x" if isinstance(chunk.rt_factor, (int, float)) else "-"
            chunk_section.append(
                f"- `{chunk.chunk_id}` | engine={chunk.engine} | rt={rt} | status={chunk.status} | {chunk.audio_path}"
            )

        header_lines = [
            f"### Phase 4 Summary for `{summary.file_id}`",
            f"- Requested engine: **{summary.requested_engine}**",
            f"- Chunks: {summary.completed} completed / {summary.failed} failed / total {summary.total_chunks}",
        ]
        if isinstance(summary.duration_seconds, (int, float)):
            header_lines.append(f"- Duration: {summary.duration_seconds:.1f}s")

        pagination = f"**Page {summary.page}/{summary.total_pages} (showing {len(summary.chunks)} rows)**"
        chunk_text = "\n".join(chunk_section) if chunk_section else "- No chunk rows in this page."
        return f"{chr(10).join(header_lines)}\n{pagination}\n\n{chunk_text}"

    def _resume_message(self, pipeline_api: PipelineAPI) -> Tuple[bool, str]:
        incomplete = pipeline_api.check_incomplete_work()
        if not incomplete:
            return False, ""

        complete = self._format_phase_numbers(incomplete.phases_complete)
        pending = self._format_phase_numbers(incomplete.phases_incomplete)
        message = f"""
## 🔄 Incomplete Generation Found

**Book:** `{incomplete.file_id}`

**Completed phases:** {complete}
**Pending phases:** {pending}

You can:
1. **Resume** by enabling "Resume from checkpoint" and running pending phases
2. **Start fresh** by disabling resume and running all phases
"""
        return True, message

    # ------------------------------------------------------------------ #
    # Callbacks
    # ------------------------------------------------------------------ #
    def handle_cancel(self, ui_state: UIState) -> Tuple[str, UIState]:
        if ui_state.active_job and ui_state.active_job != "single":
            return "⚠️ Batch generation is running; wait for it to finish or stop it from the batch tab.", ui_state

        if not ui_state.worker.is_running:
            return "ℹ️ No active generation to cancel.", ui_state

        ui_state.pipeline_api.request_cancel()
        ui_state.worker.cancel()
        ui_state.clear_job()
        return "⚠️ **Cancellation requested.** The pipeline will stop after the current step.", ui_state

    async def handle_create_audiobook(
        self,
        ui_state: UIState,
        book_file: str,
        voice_selection: str,
        engine_selection: str,
        mastering_preset: str,
        enable_resume: bool,
        max_retries: float,
        generate_subtitles: bool,
        concat_only: bool,
        phase_choices: List[str],
        progress=gr.Progress(track_tqdm=True),
    ) -> Tuple[Optional[str], str, UIState]:
        if not book_file:
            return None, "❌ Please upload a book file.", ui_state

        if ui_state.worker.is_running:
            return None, "⚠️ Another pipeline run is already in progress.", ui_state

        voice_meta = self.voice_manager.get_voice(voice_selection)
        if not voice_meta:
            return None, "❌ Please select a voice.", ui_state

        phases, subtitles_selected = self._parse_phase_choices(phase_choices)
        if not phases:
            return None, "❌ Please select at least one phase to run.", ui_state

        engine = ENGINE_MAP.get(engine_selection, "xtts")
        file_path = Path(book_file)
        retries = int(max_retries)
        no_resume = not bool(enable_resume)
        subtitles_requested = bool(generate_subtitles) or subtitles_selected

        async def runner(cancel_event, update_progress):
            def progress_hook(value: float, desc: Optional[str] = None):
                update_progress(value, desc)
                self._safe_progress(progress, value, desc)

            ui_state.pipeline_api.reset_cancel()
            result = await ui_state.pipeline_api.run_pipeline_async(
                file_path=file_path,
                voice_id=voice_meta.voice_id,
                tts_engine=engine,
                mastering_preset=mastering_preset,
                phases=phases,
                enable_subtitles=subtitles_requested,
                max_retries=retries,
                no_resume=no_resume,
                concat_only=bool(concat_only),
                progress_callback=progress_hook,
                cancel_event=cancel_event,
            )
            return result

        ui_state.mark_job("single")
        try:
            task = self._run_background(ui_state.worker.start, runner)
            result = await task
        except RuntimeError as exc:
            ui_state.clear_job()
            return None, f"⚠️ {exc}", ui_state
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Audiobook generation failed")
            ui_state.clear_job()
            return None, f"❌ Error: {exc}", ui_state
        finally:
            ui_state.clear_job()

        if not result.get("success"):
            error = result.get("error", "Unknown error")
            if error == "cancelled":
                return None, "⚠️ **Generation cancelled.** Partial progress was saved.", ui_state
            return None, f"❌ Error: {error}", ui_state

        audiobook_path = result.get("audiobook_path", "phase5_enhancement/processed/")
        options_list = []
        if no_resume:
            options_list.append("Fresh run (no resume)")
        if retries != 2:
            options_list.append(f"Max retries: {retries}")
        if subtitles_requested:
            options_list.append("Subtitles generated")
        if phases != RUNNABLE_PHASES or subtitles_requested:
            options_list.append(f"Phases: {self._format_phase_selection(phases, include_subtitles=subtitles_requested)}")
        if concat_only:
            options_list.append("Concat only (reuse enhanced WAVs when present)")

        options_text = "\n- ".join(options_list) if options_list else "Default settings"
        return None, f"""
✅ Audiobook generated successfully!

**Configuration:**
- Voice: {voice_meta.voice_id}
- Engine: {engine_selection}
- Mastering: {mastering_preset}

**Options:**
- {options_text}

**Output:**
- Path: `{audiobook_path}`
""", ui_state
    async def handle_batch_audiobooks(
        self,
        ui_state: UIState,
        book_files: List[str],
        voice_selection: str,
        engine_selection: str,
        mastering_preset: str,
        enable_resume: bool,
        max_retries: float,
        generate_subtitles: bool,
        phase_choices: List[str],
        progress=gr.Progress(track_tqdm=True),
    ) -> Tuple[str, UIState]:
        if not book_files:
            return "❌ Please upload one or more book files.", ui_state
        if ui_state.worker.is_running:
            return "⚠️ Another pipeline run is already in progress.", ui_state

        voice_meta = self.voice_manager.get_voice(voice_selection)
        if not voice_meta:
            return "❌ Please select a voice.", ui_state

        phases, subtitles_selected = self._parse_phase_choices(phase_choices)
        if not phases:
            return "❌ Please select at least one phase to run.", ui_state

        engine = ENGINE_MAP.get(engine_selection, "xtts")
        retries = int(max_retries)
        no_resume = not bool(enable_resume)
        subtitles_requested = bool(generate_subtitles) or subtitles_selected

        async def runner(cancel_event, update_progress):
            results = []
            total = len(book_files)
            ui_state.pipeline_api.reset_cancel()
            for idx, book in enumerate(book_files, start=1):
                if cancel_event.is_set():
                    results.append(f"- ❌ Cancelled before processing `{Path(book).name}`")
                    break

                file_path = Path(book)
                self._safe_progress(progress, (idx - 1) / total, f"Batch {idx}/{total}: {file_path.name}")
                update_progress((idx - 1) / total, f"Starting {file_path.name}")

                inner_progress = gr.Progress(track_tqdm=True)

                def progress_hook(value: float, desc: Optional[str] = None):
                    update_progress(value, desc)
                    self._safe_progress(inner_progress, value, desc)

                res = await ui_state.pipeline_api.run_pipeline_async(
                    file_path=file_path,
                    voice_id=voice_meta.voice_id,
                    tts_engine=engine,
                    mastering_preset=mastering_preset,
                    phases=phases,
                    enable_subtitles=subtitles_requested,
                    max_retries=retries,
                    no_resume=no_resume,
                    concat_only=False,
                    progress_callback=progress_hook,
                    cancel_event=cancel_event,
                )

                if res.get("success"):
                    out_path = res.get("audiobook_path", "phase5_enhancement/processed/")
                    results.append(f"- ✅ `{file_path.name}` → `{out_path}`")
                else:
                    results.append(f"- ❌ `{file_path.name}` failed: {res.get('error','unknown error')}")

            self._safe_progress(progress, 1.0, "Batch complete")
            return "\n".join(results)

        ui_state.mark_job("batch")
        try:
            task = self._run_background(ui_state.worker.start, runner)
            result = await task
            return result, ui_state
        except RuntimeError as exc:
            ui_state.clear_job()
            return f"⚠️ {exc}", ui_state
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Batch processing failed")
            ui_state.clear_job()
            return f"❌ Error: {exc}", ui_state
        finally:
            ui_state.clear_job()


    def handle_batch_history_refresh(self, ui_state: UIState) -> str:
        try:
            runs = ui_state.pipeline_api.get_batch_runs()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load batch history: %s", exc)
            return f"❌ Unable to load batch history: {exc}"

        if not runs:
            return "No batch runs recorded yet."

        lines: List[str] = ["### Recent Batch Runs"]
        for run in reversed(runs[-5:]):
            run_id = run.get("run_id", "unknown")
            status = run.get("status", "unknown")
            timestamps = run.get("timestamps", {})
            metrics = run.get("metrics", {})
            files = run.get("files", {}) or {}
            lines.append(
                f"**{run_id}** — {status}\n"
                f"- Started: `{timestamps.get('start', 'unknown')}`\n"
                f"- Ended: `{timestamps.get('end', 'unknown')}`\n"
                f"- Files processed: {metrics.get('total_files', len(files))}\n"
                f"- Successful: {metrics.get('successful_files', 'n/a')} | Failed: {metrics.get('failed_files', 'n/a')}"
            )
        return "\n\n".join(lines)

    def handle_add_voice(
        self,
        voice_name: str,
        voice_file: Any,
        narrator_name: str,
        genre_tags: str,
    ):
        result = self.voice_manager.add_voice(voice_name, voice_file, narrator_name, genre_tags)
        choices = self.voice_manager.list_dropdown()
        dropdown_update = gr.Dropdown.update(choices=choices, value=choices[0] if choices else None)
        gallery_html = self._build_voice_gallery_html()

        if not result.get("ok"):
            return result.get("message", "❌ Unable to add voice"), gallery_html, dropdown_update, dropdown_update

        preferred = result.get("metadata")
        selected_value = preferred.to_dropdown_label() if preferred else dropdown_update["value"]
        dropdown_update = gr.Dropdown.update(choices=choices, value=selected_value)
        message = result.get("message", "✅ Voice added")
        return message, gallery_html, dropdown_update, dropdown_update

    def handle_voice_details(self, voice_selection: str) -> str:
        voice = self.voice_manager.get_voice(voice_selection)
        if not voice:
            return "Select a voice to see details."
        profiles = ", ".join(voice.preferred_profiles)

        # Build extra info for built-in voices
        extra_info = []
        if voice.built_in:
            extra_info.append(f"**Engine:** {voice.engine.upper() if voice.engine else 'Unknown'}")
            if voice.gender:
                extra_info.append(f"**Gender:** {voice.gender.capitalize()}")
            if voice.accent:
                extra_info.append(f"**Accent:** {voice.accent}")
            extra_info.append("**Type:** Built-in (no reference audio needed)")
        else:
            extra_info.append("**Type:** Custom voice clone")
            if voice.local_path:
                extra_info.append(f"**Reference:** `{voice.local_path}`")

        extra_section = "\n".join(extra_info)

        return f"""
## 🎤 {voice.narrator_name}

**Voice ID:** {voice.voice_id}

{extra_section}

**Best for:** {profiles or 'General'}

**Description:**
{voice.description or 'No description provided.'}

**Notes:**
{voice.notes or 'No notes.'}
"""

    def handle_status_refresh(self, ui_state: UIState, file_id: str) -> str:
        try:
            return self._format_status(ui_state.pipeline_api, file_id)
        except Exception as exc:
            logger.warning("Failed to refresh status: %s", exc)
            return f"❌ Unable to refresh status: {exc}"

    def handle_phase4_refresh(self, ui_state: UIState, file_id: str, page: float, page_size: float) -> str:
        try:
            page_int = max(1, int(page))
            page_size_int = max(1, min(100, int(page_size)))
            summary = ui_state.pipeline_api.get_phase4_summary(file_id, page_int, page_size_int)
            if summary and page_int > summary.total_pages:
                page_int = summary.total_pages or 1
                summary = ui_state.pipeline_api.get_phase4_summary(file_id, page_int, page_size_int)
            return self._format_phase4_summary(summary)
        except Exception as exc:
            logger.warning("Failed to refresh phase 4 summary: %s", exc)
            return f"❌ Unable to refresh Phase 4 summary: {exc}"

    def handle_phase5_refresh(self, page: float, page_size: float) -> str:
        processed_dir = PROJECT_ROOT / "phase5_enhancement" / "processed"
        try:
            files = sorted(list(processed_dir.glob("*.mp3")) + list(processed_dir.glob("enhanced_*.wav")))
            if not files:
                return "No Phase 5 outputs found yet."

            page_int = max(1, int(page))
            page_size_int = max(1, min(100, int(page_size)))
            total_pages = max(1, (len(files) + page_size_int - 1) // page_size_int)
            if page_int > total_pages:
                page_int = total_pages

            start = (page_int - 1) * page_size_int
            subset = files[start : start + page_size_int]
            lines = []
            for fpath in subset:
                try:
                    size_mb = fpath.stat().st_size / (1024 * 1024)
                    lines.append(f"- {fpath.name} ({size_mb:.1f} MB)")
                except Exception:
                    lines.append(f"- {fpath.name}")

            header = f"### Phase 5 Outputs\nPage {page_int}/{total_pages} (showing {len(subset)} of {len(files)})"
            return f"{header}\n\n" + ("\n".join(lines) if lines else "- No files on this page.")
        except Exception as exc:
            logger.warning("Failed to refresh phase 5 outputs: %s", exc)
            return f"❌ Unable to read Phase 5 outputs: {exc}"

    def handle_log_refresh(self, ui_state: UIState, log_key: str) -> str:
        try:
            return ui_state.pipeline_api.tail_log(log_key)
        except Exception as exc:
            logger.warning("Failed to refresh log: %s", exc)
            return f"❌ Unable to read log: {exc}"

    def handle_save_settings(
        self,
        sample_rate: float,
        lufs_target: float,
        max_workers: float,
        enable_gpu: bool,
        input_dir: str,
        output_dir: str,
    ) -> str:
        self.settings = UISettings(
            sample_rate=int(sample_rate),
            lufs_target=int(lufs_target),
            max_workers=int(max_workers),
            enable_gpu=bool(enable_gpu),
            input_dir=input_dir,
            output_dir=output_dir,
        )
        saved = self.settings_manager.save(self.settings)
        return "✅ Settings saved successfully!" if saved else "❌ Failed to save settings."
    # ------------------------------------------------------------------ #
    # UI builder
    # ------------------------------------------------------------------ #
    def build_ui(self):
        app_theme = gr.themes.Soft(primary_hue="blue", secondary_hue="orange")
        voice_choices = self.voice_manager.list_dropdown()
        initial_state = self._create_ui_state()
        file_ids = initial_state.pipeline_api.get_file_ids()
        incomplete_detected, incomplete_msg = self._resume_message(initial_state.pipeline_api)

        # Create factory function to avoid deepcopy issues with threading objects
        def create_state():
            return UIState(pipeline_api=PipelineAPI(PROJECT_ROOT, log_files=LOG_FILES), worker=PipelineWorker())

        with gr.Blocks(theme=app_theme, css=CUSTOM_CSS, title="🎙️ Personal Audiobook Studio") as app:
            ui_state = gr.State(create_state)
            gr.HTML(
                """
                <div class="header">
                    <h1>🎙️ Personal Audiobook Studio</h1>
                    <p>Craft audiobooks with soul. Not production, but art.</p>
                </div>
                """
            )

            # STATUS TAB
            with gr.Tab("📊 Status"):
                gr.Markdown("## Live Pipeline Status")
                gr.Markdown(
                    "_Phase 5.5 corresponds to subtitle generation progress (SRT/VTT outputs)._",
                    elem_classes=["text-sm"],
                )
                with gr.Row():
                    status_file_dropdown = gr.Dropdown(
                        choices=file_ids,
                        value=file_ids[0] if file_ids else None,
                        label="Tracked File (from pipeline.json)",
                )
                    refresh_status_btn = gr.Button("🔄 Refresh", variant="secondary")

                status_markdown = gr.Markdown(
                    self._format_status(initial_state.pipeline_api, file_ids[0])
                    if file_ids
                    else "Select a file to view pipeline status."
                )
                status_file_dropdown.change(
                    self.handle_status_refresh, inputs=[ui_state, status_file_dropdown], outputs=status_markdown
                )
                refresh_status_btn.click(
                    self.handle_status_refresh, inputs=[ui_state, status_file_dropdown], outputs=status_markdown
                )

                with gr.Accordion("Phase 4 Summary (paged)", open=False):
                    with gr.Row():
                        phase4_page = gr.Slider(1, 200, value=1, step=1, label="Chunk page")
                        phase4_page_size = gr.Slider(5, 50, value=20, step=1, label="Rows per page")
                    phase4_summary_md = gr.Markdown("Select a file to view Phase 4 summary.")

                    status_file_dropdown.change(
                        self.handle_phase4_refresh,
                        inputs=[ui_state, status_file_dropdown, phase4_page, phase4_page_size],
                        outputs=phase4_summary_md,
                    )
                    phase4_page.change(
                        self.handle_phase4_refresh,
                        inputs=[ui_state, status_file_dropdown, phase4_page, phase4_page_size],
                        outputs=phase4_summary_md,
                    )
                    phase4_page_size.change(
                        self.handle_phase4_refresh,
                        inputs=[ui_state, status_file_dropdown, phase4_page, phase4_page_size],
                        outputs=phase4_summary_md,
                    )

                with gr.Accordion("Phase 5 Outputs (paged)", open=False):
                    with gr.Row():
                        phase5_page = gr.Slider(1, 200, value=1, step=1, label="Output page")
                        phase5_page_size = gr.Slider(5, 50, value=10, step=1, label="Rows per page")
                    phase5_summary_md = gr.Markdown(self.handle_phase5_refresh(1, 10))

                    phase5_page.change(
                        self.handle_phase5_refresh, inputs=[phase5_page, phase5_page_size], outputs=phase5_summary_md
                    )
                    phase5_page_size.change(
                        self.handle_phase5_refresh, inputs=[phase5_page, phase5_page_size], outputs=phase5_summary_md
                    )

                with gr.Accordion("Log tail (CPU-safe monitoring)", open=False):
                    with gr.Row():
                        log_dropdown = gr.Dropdown(
                            choices=list(LOG_FILES.keys()),
                            value=next(iter(LOG_FILES.keys())) if LOG_FILES else None,
                            label="Log file",
                        )
                        log_refresh = gr.Button("🔄 Refresh", variant="secondary")
                    log_viewer = gr.Textbox(label="Last 200 lines", lines=12, value="")

                    log_dropdown.change(self.handle_log_refresh, inputs=[ui_state, log_dropdown], outputs=log_viewer)
                    log_refresh.click(self.handle_log_refresh, inputs=[ui_state, log_dropdown], outputs=log_viewer)
            # SINGLE BOOK TAB
            with gr.Tab("📖 Single Book"):
                gr.Markdown("## Create a Single Audiobook")

                if incomplete_detected:
                    with gr.Accordion("🔄 Resume Previous Generation", open=True):
                        gr.Markdown(incomplete_msg)
                        gr.Markdown("**Tip:** Enable 'Resume from checkpoint' in Advanced Options below")

                with gr.Row():
                    with gr.Column(scale=2):
                        book_input = gr.File(
                            label="📚 Upload Book",
                            file_types=[".epub", ".pdf", ".txt", ".mobi"],
                            type="filepath",
                        )

                        with gr.Row():
                            voice_dropdown = gr.Dropdown(
                                choices=voice_choices,
                                label="🎤 Voice",
                                info="Select narrator voice for this book",
                            )

                            engine_dropdown = gr.Dropdown(
                                choices=list(ENGINE_MAP.keys()),
                                value="XTTS v2 (Expressive)",
                                label="🤖 TTS Engine",
                                info="Choose synthesis engine (XTTS=quality, Kokoro=speed)",
                            )

                        with gr.Row():
                            preset_dropdown = gr.Dropdown(
                                choices=self.presets,
                                value=self.presets[0] if self.presets else "audiobook_intimate",
                                label="🎚️ Mastering Preset",
                                info="Audio processing style",
                            )

                        with gr.Accordion("⚙️ Advanced Options", open=False):
                            with gr.Row():
                                enable_resume = gr.Checkbox(
                                    label="Enable Resume",
                                    value=True,
                                    info="Resume from checkpoint if interrupted",
                                )

                                max_retries = gr.Slider(
                                    minimum=0,
                                    maximum=5,
                                    value=2,
                                    step=1,
                                    label="Max Retries",
                                    info="Retry attempts per phase",
                                )

                            with gr.Row():
                                generate_subtitles = gr.Checkbox(
                                    label="Generate Subtitles",
                                    value=False,
                                    info="Create .srt and .vtt subtitle files",
                                )
                                concat_only = gr.Checkbox(
                                    label="Concat Only (reuse enhanced WAVs if present)",
                                    value=False,
                                    info="Skip re-enhancement when enhanced WAVs already exist",
                                )

                            gr.Markdown(
                                "Tip: When launching from CLI, use `--phase5-concat-only` to reuse enhanced WAVs without reprocessing.",
                                elem_classes=["text-sm"],
                            )

                            gr.Markdown("**Phases to Run:**")
                            phase_choices_list = self._phase_choice_list() or ["phase1: Phase 1 – Validation"]
                            phase_default_values = self._default_phase_choices() or phase_choices_list[:1]
                            phase_selector = gr.CheckboxGroup(
                                label="Select pipeline phases",
                                choices=phase_choices_list,
                                value=phase_default_values,
                            )
                            gr.Markdown(
                                "_Phase 5.5 – Subtitles toggles subtitle generation (SRT/VTT outputs)._", elem_classes=["text-sm"]
                            )

                        with gr.Row():
                            generate_btn = gr.Button("🎬 Generate Audiobook", variant="primary", size="lg", scale=2)
                            stop_btn = gr.Button("🛑 Stop", variant="stop", size="lg", visible=False, scale=1)

                    with gr.Column(scale=1):
                        voice_details = gr.Markdown("Select a voice to see details", label="Voice Information")

                with gr.Row():
                    audio_output = gr.Audio(label="🎧 Generated Audiobook")
                    status_output = gr.Markdown(label="Status")

                stop_status = gr.Markdown(visible=False)

                generate_click = generate_btn.click(
                    fn=self.handle_create_audiobook,
                    inputs=[
                        ui_state,
                        book_input,
                        voice_dropdown,
                        engine_dropdown,
                        preset_dropdown,
                        enable_resume,
                        max_retries,
                        generate_subtitles,
                        concat_only,
                        phase_selector,
                    ],
                    outputs=[audio_output, status_output, ui_state],
                )

                generate_btn.click(fn=self._show_stop_button, inputs=None, outputs=[stop_btn])
                generate_click.then(fn=self._hide_stop_button, inputs=None, outputs=[stop_btn])
                stop_btn.click(
                    fn=self.handle_cancel, inputs=[ui_state], outputs=[stop_status, ui_state], cancels=[generate_click]
                )
                stop_btn.click(fn=self._hide_stop_button, inputs=None, outputs=[stop_btn])

                voice_dropdown.change(fn=self.handle_voice_details, inputs=[voice_dropdown], outputs=[voice_details])
            # BATCH TAB
            with gr.Tab("📦 Batch Queue"):
                gr.Markdown("## Process Multiple Books")

                with gr.Row():
                    with gr.Column(scale=2):
                        batch_files = gr.File(
                            label="📚 Upload Books (multiple)",
                            file_types=[".epub", ".pdf", ".txt", ".mobi"],
                            file_count="multiple",
                            type="filepath",
                        )

                        with gr.Row():
                            batch_voice = gr.Dropdown(
                                choices=voice_choices,
                                label="🎤 Voice",
                                info="Select narrator voice for all books",
                            )

                            batch_engine = gr.Dropdown(
                                choices=list(ENGINE_MAP.keys()),
                                value="Kokoro (CPU-Friendly)",
                                label="🤖 TTS Engine",
                                info="Choose synthesis engine",
                            )

                        batch_preset = gr.Dropdown(
                            choices=self.presets,
                            value=self.presets[0] if self.presets else "audiobook_intimate",
                            label="🎛️ Mastering Preset",
                            info="Audio processing style",
                        )

                        with gr.Accordion("⚙️ Batch Options", open=False):
                            batch_enable_resume = gr.Checkbox(
                                label="Enable Resume",
                                value=True,
                                info="Resume from checkpoint if interrupted",
                            )
                            batch_max_retries = gr.Slider(
                                minimum=0,
                                maximum=5,
                                value=1,
                                step=1,
                                label="Max Retries",
                                info="Retry attempts per phase",
                            )
                            batch_generate_subtitles = gr.Checkbox(
                                label="Generate Subtitles",
                                value=False,
                                info="Create .srt and .vtt subtitle files",
                            )

                            gr.Markdown("**Phases to Run:**")
                            batch_phase_choices = self._phase_choice_list() or ["phase1: Phase 1 – Validation"]
                            batch_phase_defaults = self._default_phase_choices() or batch_phase_choices[:1]
                            batch_phase_selector = gr.CheckboxGroup(
                                label="Select pipeline phases",
                                choices=batch_phase_choices,
                                value=batch_phase_defaults,
                            )
                            gr.Markdown(
                                "_Selecting Phase 5.5 will automatically request subtitle generation._",
                                elem_classes=["text-sm"],
                            )

                    with gr.Column():
                        gr.Markdown("### Batch Controls")
                        batch_run_btn = gr.Button("🚀 Run Batch", variant="primary")
                        batch_status = gr.Markdown("Waiting to start...")

                        with gr.Accordion("📜 Batch History", open=False):
                            batch_history_md = gr.Markdown(self.handle_batch_history_refresh(initial_state))
                            refresh_history_btn = gr.Button("🔄 Refresh History", variant="secondary")
                            refresh_history_btn.click(
                                self.handle_batch_history_refresh,
                                inputs=[ui_state],
                                outputs=[batch_history_md],
                            )

                    batch_run_btn.click(
                        fn=self.handle_batch_audiobooks,
                        inputs=[
                            ui_state,
                            batch_files,
                            batch_voice,
                            batch_engine,
                            batch_preset,
                            batch_enable_resume,
                            batch_max_retries,
                            batch_generate_subtitles,
                            batch_phase_selector,
                        ],
                        outputs=[batch_status, ui_state],
                    )

            # VOICE TAB
            with gr.Tab("🎤 Voice Library"):
                gr.Markdown("## Manage Your Voice Collection")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Add New Voice")

                        new_voice_name = gr.Textbox(label="Voice ID", placeholder="e.g., morgan_freeman")
                        new_voice_file = gr.Audio(label="Voice Sample (10-30 seconds)", type="filepath", sources=["upload"])
                        new_narrator_name = gr.Textbox(label="Narrator Name", placeholder="e.g., Morgan Freeman")
                        new_genre_tags = gr.Textbox(
                            label="Genre Tags (comma-separated)",
                            placeholder="e.g., philosophy, documentary, narrative",
                        )
                        add_voice_btn = gr.Button("➕ Add Voice", variant="primary")
                        add_voice_status = gr.Markdown()

                    with gr.Column():
                        gr.Markdown("### Existing Voices")
                        voice_gallery = gr.HTML(self._build_voice_gallery_html())

                add_voice_btn.click(
                    fn=self.handle_add_voice,
                    inputs=[new_voice_name, new_voice_file, new_narrator_name, new_genre_tags],
                    outputs=[add_voice_status, voice_gallery, voice_dropdown, batch_voice],
                )

            # SETTINGS TAB
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("## Configuration")

                with gr.Accordion("Audio Quality", open=True):
                    sample_rate = gr.Slider(24000, 48000, value=self.settings.sample_rate, step=1000, label="Sample Rate (Hz)")
                    lufs_target = gr.Slider(-30, -10, value=self.settings.lufs_target, step=1, label="Target LUFS")

                with gr.Accordion("Performance"):
                    max_workers = gr.Slider(1, 16, value=self.settings.max_workers, step=1, label="Maximum Parallel Workers")
                    enable_gpu = gr.Checkbox(label="Use GPU (if available)", value=self.settings.enable_gpu)

                with gr.Accordion("Paths"):
                    input_dir = gr.Textbox(label="Input Directory", value=self.settings.input_dir or str(PROJECT_ROOT / "input"))
                    output_dir = gr.Textbox(
                        label="Output Directory",
                        value=self.settings.output_dir or str(PROJECT_ROOT / "phase5_enhancement" / "processed"),
                    )

                save_settings_btn = gr.Button("💾 Save Settings", variant="primary")
                settings_status = gr.Markdown()
                save_settings_btn.click(
                    fn=self.handle_save_settings,
                    inputs=[sample_rate, lufs_target, max_workers, enable_gpu, input_dir, output_dir],
                    outputs=[settings_status],
                )

            gr.HTML(
                """
                <div style="text-align: center; padding: 2rem; opacity: 0.7;">
                    <p>Made with ❤️ for the craft of audiobook creation</p>
                    <p><em>"Insanely great, because good enough isn't."</em></p>
                </div>
                """
            )

        return app

def cleanup_handler(app_instance):
    """Clean up resources on exit."""
    if app_instance is not None:
        try:
            logger.info("Shutting down studio...")
            app_instance.close()
            logger.info("Studio shutdown complete")
        except Exception as e:
            logger.error("Error during shutdown: %s", e)


def signal_handler(signum, frame, app_instance):
    """Handle Ctrl+C and other signals."""
    logger.info("Received shutdown signal, cleaning up...")
    cleanup_handler(app_instance)
    sys.exit(0)


def _first_available_port(preferred: int, *, attempts: int = 20) -> int:
    """
    Find the first available port starting at the preferred value.

    This prevents binding failures when the default Gradio port is already in use.
    """
    for offset in range(attempts):
        candidate = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", candidate))
                return candidate
            except OSError:
                continue
    raise OSError(f"Cannot find empty port in range: {preferred}-{preferred + attempts - 1}")


def main():
    """Launch the studio."""
    ui = StudioUI()
    app = ui.build_ui()

    atexit.register(lambda: cleanup_handler(app))
    signal.signal(signal.SIGINT, lambda signum, frame: signal_handler(signum, frame, app))
    signal.signal(signal.SIGTERM, lambda signum, frame: signal_handler(signum, frame, app))

    logger.info("🎙️ Starting Personal Audiobook Studio...")
    logger.info("Press Ctrl+C to stop the server")

    preferred_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    server_port = _first_available_port(preferred_port)

    try:
        app.launch(
            server_name="0.0.0.0",
            server_port=server_port,
            share=False,
            show_error=True,
            quiet=False,
            inbrowser=False,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error("Error running studio: %s", e)
        raise
    finally:
        cleanup_handler(app)


if __name__ == "__main__":
    main()




