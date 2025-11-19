
#!/usr/bin/env python3
"""
🎙️ Personal Audiobook Studio

Refactored Gradio UI with safe state management, background workers,
and a clear API boundary to the orchestrator pipeline.
"""

from __future__ import annotations

import atexit
import logging
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ui.models import FileSystemProgress, IncompleteWork, Phase4Summary, UISettings  # noqa: E402
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

class StudioUI:
    """Main UI orchestrator with explicit state injection."""

    def __init__(self) -> None:
        self.voice_manager = VoiceManager(VOICE_CONFIG_PATH, CUSTOM_VOICE_DIR)
        self.settings_manager = SettingsManager(SETTINGS_PATH, PROJECT_ROOT)
        self.settings: UISettings = self.settings_manager.load()
        self.pipeline_api = PipelineAPI(PROJECT_ROOT, log_files=LOG_FILES)
        self.worker = PipelineWorker()
        self.presets = self._load_presets()

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _show_stop_button():
        return gr.update(visible=True)

    @staticmethod
    def _hide_stop_button():
        return gr.update(visible=False)

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

    def _format_status(self, file_id: Optional[str]) -> str:
        status = self.pipeline_api.get_status(file_id)
        if not status:
            return "Select a file to view pipeline status."

        phase_lines = [f"- Phase {p.phase}: **{p.status}**" for p in status.phases]
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

    def _resume_message(self) -> Tuple[bool, str]:
        incomplete = self.pipeline_api.check_incomplete_work()
        if not incomplete:
            return False, ""

        complete = ", ".join(map(str, incomplete.phases_complete))
        pending = ", ".join(map(str, incomplete.phases_incomplete))
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
    def handle_cancel(self) -> str:
        self.pipeline_api.request_cancel()
        self.worker.cancel()
        return "⚠️ **Cancellation requested.** The pipeline will stop after the current step."
    async def handle_create_audiobook(
        self,
        book_file: str,
        voice_selection: str,
        engine_selection: str,
        mastering_preset: str,
        enable_resume: bool,
        max_retries: float,
        generate_subtitles: bool,
        concat_only: bool,
        phase1: bool,
        phase2: bool,
        phase3: bool,
        phase4: bool,
        phase5: bool,
        progress=gr.Progress(track_tqdm=True),
    ) -> Tuple[Optional[str], str]:
        if not book_file:
            return None, "❌ Please upload a book file."

        if self.worker.is_running:
            return None, "⚠️ Another pipeline run is already in progress."

        voice_meta = self.voice_manager.get_voice(voice_selection)
        if not voice_meta:
            return None, "❌ Please select a voice."

        phases = [p for p, enabled in zip([1, 2, 3, 4, 5], [phase1, phase2, phase3, phase4, phase5]) if enabled]
        if not phases:
            return None, "❌ Please select at least one phase to run."

        engine = ENGINE_MAP.get(engine_selection, "xtts")
        file_path = Path(book_file)
        retries = int(max_retries)
        no_resume = not bool(enable_resume)

        async def runner(cancel_event, update_progress):
            def progress_hook(value: float, desc: Optional[str] = None):
                update_progress(value, desc)
                try:
                    progress(value, desc=desc)
                except Exception:
                    logger.debug("Progress update failed", exc_info=True)

            self.pipeline_api.reset_cancel()
            result = await self.pipeline_api.run_pipeline_async(
                file_path=file_path,
                voice_id=voice_meta.voice_id,
                tts_engine=engine,
                mastering_preset=mastering_preset,
                phases=phases,
                enable_subtitles=bool(generate_subtitles),
                max_retries=retries,
                no_resume=no_resume,
                concat_only=bool(concat_only),
                progress_callback=progress_hook,
                cancel_event=cancel_event,
            )
            return result

        try:
            result = await self.worker.start(runner)
        except RuntimeError as exc:
            return None, f"⚠️ {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Audiobook generation failed")
            return None, f"❌ Error: {exc}"

        if not result.get("success"):
            error = result.get("error", "Unknown error")
            if error == "cancelled":
                return None, "⚠️ **Generation cancelled.** Partial progress was saved."
            return None, f"❌ Error: {error}"

        audiobook_path = result.get("audiobook_path", "phase5_enhancement/processed/")
        options_list = []
        if no_resume:
            options_list.append("Fresh run (no resume)")
        if retries != 2:
            options_list.append(f"Max retries: {retries}")
        if generate_subtitles:
            options_list.append("Subtitles generated")
        if phases != [1, 2, 3, 4, 5]:
            options_list.append(f"Phases: {', '.join(map(str, phases))}")
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
"""
    async def handle_batch_audiobooks(
        self,
        book_files: List[str],
        voice_selection: str,
        engine_selection: str,
        mastering_preset: str,
        enable_resume: bool,
        max_retries: float,
        generate_subtitles: bool,
        phase1: bool,
        phase2: bool,
        phase3: bool,
        phase4: bool,
        phase5: bool,
        progress=gr.Progress(track_tqdm=True),
    ) -> str:
        if not book_files:
            return "❌ Please upload one or more book files."
        if self.worker.is_running:
            return "⚠️ Another pipeline run is already in progress."

        voice_meta = self.voice_manager.get_voice(voice_selection)
        if not voice_meta:
            return "❌ Please select a voice."

        phases = [p for p, enabled in zip([1, 2, 3, 4, 5], [phase1, phase2, phase3, phase4, phase5]) if enabled]
        if not phases:
            return "❌ Please select at least one phase to run."

        engine = ENGINE_MAP.get(engine_selection, "xtts")
        retries = int(max_retries)
        no_resume = not bool(enable_resume)

        async def runner(cancel_event, update_progress):
            results = []
            total = len(book_files)
            for idx, book in enumerate(book_files, start=1):
                if cancel_event.is_set():
                    results.append(f"- ❌ Cancelled before processing `{Path(book).name}`")
                    break

                file_path = Path(book)
                progress((idx - 1) / total, desc=f"Batch {idx}/{total}: {file_path.name}")
                update_progress((idx - 1) / total, f"Starting {file_path.name}")

                inner_progress = gr.Progress(track_tqdm=True)

                def progress_hook(value: float, desc: Optional[str] = None):
                    update_progress(value, desc)
                    try:
                        inner_progress(value, desc=desc)
                    except Exception:
                        logger.debug("Batch progress update failed", exc_info=True)

                res = await self.pipeline_api.run_pipeline_async(
                    file_path=file_path,
                    voice_id=voice_meta.voice_id,
                    tts_engine=engine,
                    mastering_preset=mastering_preset,
                    phases=phases,
                    enable_subtitles=bool(generate_subtitles),
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

            progress(1.0, desc="Batch complete")
            return "\n".join(results)

        try:
            return await self.worker.start(runner)
        except RuntimeError as exc:
            return f"⚠️ {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Batch processing failed")
            return f"❌ Error: {exc}"

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
        return f"""
## 🎤 {voice.narrator_name}

**Voice ID:** {voice.voice_id}

**Best for:** {profiles or 'General'}

**Description:**
{voice.description or 'No description provided.'}

**Notes:**
{voice.notes or 'No notes.'}
"""

    def handle_status_refresh(self, file_id: str) -> str:
        try:
            return self._format_status(file_id)
        except Exception as exc:
            logger.warning("Failed to refresh status: %s", exc)
            return f"❌ Unable to refresh status: {exc}"

    def handle_phase4_refresh(self, file_id: str, page: float, page_size: float) -> str:
        try:
            summary = self.pipeline_api.get_phase4_summary(file_id, int(page), int(page_size))
            return self._format_phase4_summary(summary)
        except Exception as exc:
            logger.warning("Failed to refresh phase 4 summary: %s", exc)
            return f"❌ Unable to refresh Phase 4 summary: {exc}"

    def handle_log_refresh(self, log_key: str) -> str:
        try:
            return self.pipeline_api.tail_log(log_key)
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
        file_ids = self.pipeline_api.get_file_ids()
        incomplete_detected, incomplete_msg = self._resume_message()

        with gr.Blocks(theme=app_theme, css=CUSTOM_CSS, title="🎙️ Personal Audiobook Studio") as app:
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
                with gr.Row():
                    status_file_dropdown = gr.Dropdown(
                        choices=file_ids,
                        value=file_ids[0] if file_ids else None,
                        label="Tracked File (from pipeline.json)",
                    )
                    refresh_status_btn = gr.Button("🔄 Refresh", variant="secondary")

                status_markdown = gr.Markdown(
                    self._format_status(file_ids[0]) if file_ids else "Select a file to view pipeline status."
                )
                status_file_dropdown.change(self.handle_status_refresh, inputs=status_file_dropdown, outputs=status_markdown)
                refresh_status_btn.click(self.handle_status_refresh, inputs=status_file_dropdown, outputs=status_markdown)

                with gr.Accordion("Phase 4 Summary (paged)", open=False):
                    with gr.Row():
                        phase4_page = gr.Slider(1, 200, value=1, step=1, label="Chunk page")
                        phase4_page_size = gr.Slider(5, 50, value=20, step=1, label="Rows per page")
                    phase4_summary_md = gr.Markdown("Select a file to view Phase 4 summary.")

                    status_file_dropdown.change(
                        self.handle_phase4_refresh,
                        inputs=[status_file_dropdown, phase4_page, phase4_page_size],
                        outputs=phase4_summary_md,
                    )
                    phase4_page.change(
                        self.handle_phase4_refresh,
                        inputs=[status_file_dropdown, phase4_page, phase4_page_size],
                        outputs=phase4_summary_md,
                    )
                    phase4_page_size.change(
                        self.handle_phase4_refresh,
                        inputs=[status_file_dropdown, phase4_page, phase4_page_size],
                        outputs=phase4_summary_md,
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

                    log_dropdown.change(self.handle_log_refresh, inputs=log_dropdown, outputs=log_viewer)
                    log_refresh.click(self.handle_log_refresh, inputs=log_dropdown, outputs=log_viewer)
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
                            with gr.Row():
                                phase1_check = gr.Checkbox(label="Phase 1: Validation", value=True)
                                phase2_check = gr.Checkbox(label="Phase 2: Extraction", value=True)
                                phase3_check = gr.Checkbox(label="Phase 3: Chunking", value=True)

                            with gr.Row():
                                phase4_check = gr.Checkbox(label="Phase 4: TTS", value=True)
                                phase5_check = gr.Checkbox(label="Phase 5: Enhancement", value=True)

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
                        book_input,
                        voice_dropdown,
                        engine_dropdown,
                        preset_dropdown,
                        enable_resume,
                        max_retries,
                        generate_subtitles,
                        concat_only,
                        phase1_check,
                        phase2_check,
                        phase3_check,
                        phase4_check,
                        phase5_check,
                    ],
                    outputs=[audio_output, status_output],
                )

                generate_btn.click(fn=self._show_stop_button, inputs=None, outputs=[stop_btn])
                generate_click.then(fn=self._hide_stop_button, inputs=None, outputs=[stop_btn])
                stop_btn.click(fn=self.handle_cancel, inputs=None, outputs=[stop_status], cancels=[generate_click])
                stop_btn.click(fn=self._show_stop_button, inputs=None, outputs=[stop_status])

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
                            with gr.Row():
                                b_phase1 = gr.Checkbox(label="Phase 1: Validation", value=True)
                                b_phase2 = gr.Checkbox(label="Phase 2: Extraction", value=True)
                                b_phase3 = gr.Checkbox(label="Phase 3: Chunking", value=True)
                            with gr.Row():
                                b_phase4 = gr.Checkbox(label="Phase 4: TTS", value=True)
                                b_phase5 = gr.Checkbox(label="Phase 5: Enhancement", value=True)

                    with gr.Column():
                        gr.Markdown("### Batch Controls")
                        batch_run_btn = gr.Button("🚀 Run Batch", variant="primary")
                        batch_status = gr.Markdown("Waiting to start...")

                batch_run_btn.click(
                    fn=self.handle_batch_audiobooks,
                    inputs=[
                        batch_files,
                        batch_voice,
                        batch_engine,
                        batch_preset,
                        batch_enable_resume,
                        batch_max_retries,
                        batch_generate_subtitles,
                        b_phase1,
                        b_phase2,
                        b_phase3,
                        b_phase4,
                        b_phase5,
                    ],
                    outputs=[batch_status],
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


def main():
    """Launch the studio."""
    ui = StudioUI()
    app = ui.build_ui()

    atexit.register(lambda: cleanup_handler(app))
    signal.signal(signal.SIGINT, lambda signum, frame: signal_handler(signum, frame, app))
    signal.signal(signal.SIGTERM, lambda signum, frame: signal_handler(signum, frame, app))

    logger.info("🎙️ Starting Personal Audiobook Studio...")
    logger.info("Press Ctrl+C to stop the server")

    try:
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
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
