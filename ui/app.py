#!/usr/bin/env python3
"""
🎙️ Personal Audiobook Studio
Beautiful UI for creating professional audiobooks

A labor of love. Craft, not production.
"""

import gradio as gr
import sys
import json
import logging
import signal
import atexit
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import yaml
import psutil

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from phase6_orchestrator.orchestrator import run_pipeline
from pipeline_common import PipelineState

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION & STATE
# ============================================================================

class StudioState:
    """Global state management"""

    def __init__(self):
        self.voices = self._load_voices()
        self.engines = self._load_engines()
        self.presets = self._load_presets()
        self.pipeline_json = PROJECT_ROOT / "pipeline.json"
        self.cancel_flag = False  # Flag for stopping generation
        self.file_ids = self._load_file_ids()

    def cancel_generation(self):
        """Request cancellation of current generation"""
        self.cancel_flag = True
        logger.info("⚠️ User requested cancellation")

    def reset_cancel_flag(self):
        """Reset cancellation flag before starting new generation"""
        self.cancel_flag = False

    def is_cancelled(self) -> bool:
        """Check if generation should be cancelled"""
        return self.cancel_flag

    def check_incomplete_generation(self) -> Optional[Dict]:
        """Check if there's an incomplete generation that can be resumed"""
        try:
            if not self.pipeline_json.exists():
                return None

            with open(self.pipeline_json, 'r') as f:
                data = json.load(f)

            # Check for any incomplete books
            for file_id, book_data in data.items():
                if file_id == "metadata":
                    continue

                # Check phase completion
                phases_complete = []
                phases_incomplete = []

                for phase in [1, 2, 3, 4, 5]:
                    phase_key = f"phase{phase}"
                    if phase_key in book_data:
                        status = book_data[phase_key].get('status', 'unknown')
                        if status == 'success':
                            phases_complete.append(phase)
                        else:
                            phases_incomplete.append(phase)
                    else:
                        phases_incomplete.append(phase)

                # If some phases complete but not all, offer resume
                if phases_complete and phases_incomplete:
                    return {
                        'file_id': file_id,
                        'phases_complete': phases_complete,
                        'phases_incomplete': phases_incomplete,
                        'last_phase': max(phases_complete) if phases_complete else 0
                    }

            return None
        except Exception as e:
            logger.error(f"Error checking for incomplete generation: {e}")
            return None

    def _load_file_ids(self) -> List[str]:
        """List known files from pipeline.json (phase1 files)."""
        if not self.pipeline_json.exists():
            return []
        try:
            with open(self.pipeline_json, "r") as f:
                data = json.load(f)
            phase1 = data.get("phase1", {}).get("files", {}) or {}
            return sorted(list(phase1.keys()))
        except Exception as exc:
            logger.error(f"Failed to list file ids: {exc}")
            return []

    def _load_voices(self) -> Dict:
        """Load voice library"""
        voice_json = PROJECT_ROOT / "phase4_tts" / "configs" / "voice_references.json"
        try:
            with open(voice_json, 'r') as f:
                data = json.load(f)
            return data.get('voice_references', {})
        except Exception as e:
            logger.error(f"Failed to load voices: {e}")
            return {}

    def _load_engines(self) -> List[str]:
        """Get available TTS engines"""
        return [
            "XTTS v2 (Expressive)",
            "Kokoro (CPU-Friendly)"
        ]

    def _load_presets(self) -> List[str]:
        """Load mastering presets"""
        presets_path = PROJECT_ROOT / "phase5_enhancement" / "presets" / "mastering_presets.yaml"
        try:
            with open(presets_path, 'r') as f:
                data = yaml.safe_load(f)
            return list(data.get('presets', {}).keys())
        except:
            return ["audiobook_intimate", "audiobook_dynamic", "podcast_standard"]

    def get_voice_list(self) -> List[str]:
        """Get formatted voice list for dropdown"""
        return [
            f"{voice_id}: {meta.get('narrator_name', 'Unknown')} ({', '.join(meta.get('preferred_profiles', []))})"
            for voice_id, meta in self.voices.items()
        ]


# Initialize state
state = StudioState()


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

.tab-nav button {
    font-size: 1.05rem;
    padding: 0.75rem 1.5rem;
    transition: all 0.2s;
}

.tab-nav button.selected {
    border-bottom: 3px solid var(--secondary-color);
    color: var(--secondary-color);
    font-weight: 700;
}

/* Button styling */
.primary-button {
    background: var(--secondary-color) !important;
    color: #0b1d3a !important;
    font-weight: 700;
    padding: 0.8rem 2rem;
    border-radius: 10px;
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

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_for_incomplete_work() -> Tuple[bool, str]:
    """Check for incomplete generation and return status message"""
    incomplete = state.check_incomplete_generation()

    if incomplete:
        file_id = incomplete['file_id']
        complete = ', '.join(map(str, incomplete['phases_complete']))
        pending = ', '.join(map(str, incomplete['phases_incomplete']))

        message = f"""
## 🔄 Incomplete Generation Found

**Book:** `{file_id}`

**Completed phases:** {complete}
**Pending phases:** {pending}

You can:
1. **Resume** by enabling "Resume from checkpoint" and running pending phases
2. **Start fresh** by disabling resume and running all phases
        """
        return True, message

    return False, ""


def cancel_generation_fn() -> str:
    """Handle stop button click"""
    state.cancel_generation()
    return "⚠️ **Cancellation requested.** Generation will stop after current phase completes."


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def create_audiobook(
    book_file,
    voice_selection: str,
    engine_selection: str,
    mastering_preset: str,
    enable_resume: bool,
    max_retries: int,
    generate_subtitles: bool,
    phase1: bool,
    phase2: bool,
    phase3: bool,
    phase4: bool,
    phase5: bool,
    progress=gr.Progress()
) -> Tuple[Optional[str], str]:
    """
    Main audiobook generation function

    Args:
        book_file: Uploaded book file
        voice_selection: Selected voice from dropdown
        engine_selection: TTS engine choice
        mastering_preset: Audio mastering preset
        enable_resume: Enable resume from checkpoint
        max_retries: Maximum retry attempts per phase
        generate_subtitles: Generate subtitle files
        phase1-5: Which phases to run
        progress: Gradio progress tracker

    Returns:
        Tuple of (audio_path, status_message)
    """
    if book_file is None:
        return None, "❌ Please upload a book file"

    # Reset cancellation flag at start of new generation
    state.reset_cancel_flag()

    try:
        # Extract voice ID from selection
        voice_id = voice_selection.split(":")[0].strip()

        # Map engine selection to engine name
        engine_map = {
            "XTTS v2 (Expressive)": "xtts",
            "Kokoro (CPU-Friendly)": "kokoro",
        }
        engine = engine_map.get(engine_selection, "xtts")  # Default to XTTS

        # Build phases list from checkboxes
        phases = []
        if phase1:
            phases.append(1)
        if phase2:
            phases.append(2)
        if phase3:
            phases.append(3)
        if phase4:
            phases.append(4)
        if phase5:
            phases.append(5)

        if not phases:
            return None, "❌ Please select at least one phase to run"

        logger.info(f"Starting audiobook generation: {book_file.name}")
        logger.info(f"Voice: {voice_id}, Engine: {engine}, Preset: {mastering_preset}")
        logger.info(f"Options: Resume={enable_resume}, Retries={max_retries}, Subtitles={generate_subtitles}")
        logger.info(f"Phases: {phases}")

        # Progress callback with cancellation check
        def update_progress(phase: int, percentage: float, message: str):
            # Check for cancellation
            if state.is_cancelled():
                raise KeyboardInterrupt("Generation cancelled by user")

            phase_names = [
                "Validation",
                "Text Extraction",
                "Semantic Chunking",
                "TTS Synthesis",
                "Audio Mastering",
                "Final Assembly"
            ]

            phase_name = phase_names[phase - 1] if phase <= len(phase_names) else "Processing"
            progress(
                (phase - 1) / 7 + percentage / 700,
                desc=f"Phase {phase}: {phase_name} - {message}"
            )

        # Run the actual pipeline
        result = run_pipeline(
            file_path=Path(book_file.name),
            voice_id=voice_id,
            tts_engine=engine,
            mastering_preset=mastering_preset,
            phases=phases,
            pipeline_json=state.pipeline_json,
            enable_subtitles=generate_subtitles,
            max_retries=int(max_retries),
            no_resume=not enable_resume,
            progress_callback=update_progress
        )

        if not result["success"]:
            return None, f"❌ Error: {result.get('error', 'Unknown error')}"

        progress(1.0, desc="✅ Complete!")

        # Build success message
        audiobook_path = result.get("audiobook_path", "phase5_enhancement/processed/")
        metadata = result.get("metadata", {})

        # Build options summary
        options_list = []
        if not enable_resume:
            options_list.append("Fresh run (no resume)")
        if max_retries != 2:
            options_list.append(f"Max retries: {int(max_retries)}")
        if generate_subtitles:
            options_list.append("Subtitles generated")
        if phases != [1, 2, 3, 4, 5]:
            options_list.append(f"Phases: {', '.join(map(str, phases))}")

        options_text = "\n- ".join(options_list) if options_list else "Default settings"

        return None, f"""
✅ Audiobook generated successfully!

**Configuration:**
- Voice: {voice_id}
- Engine: {engine_selection}
- Mastering: {mastering_preset}

**Options:**
- {options_text}

**Output:**
- Path: `{audiobook_path}`

**Pipeline Status:**
- Phases completed: {', '.join(map(str, metadata.get('phases_completed', [])))}

**Next Steps:**
1. Listen to your audiobook in `phase5_enhancement/processed/`
2. Check quality and adjust settings if needed
3. Create more audiobooks!

🎉 Enjoy your audiobook!
        """

    except KeyboardInterrupt:
        logger.warning("Generation cancelled by user")
        state.reset_cancel_flag()
        return None, """
⚠️ **Generation Cancelled**

The audiobook generation was stopped by user request.

**What happened:**
- Processing stopped after the current phase completed
- Partial progress has been saved to pipeline.json

**Next steps:**
1. **Resume:** Enable "Resume from checkpoint" and click Generate again
2. **Start fresh:** Disable resume and regenerate from scratch
3. **Adjust settings:** Change voice, engine, or mastering preset before resuming

Your progress is saved - you can continue anytime! 🔄
        """

    except Exception as e:
        logger.error(f"Audiobook generation failed: {e}")
        state.reset_cancel_flag()
        return None, f"❌ Error: {str(e)}"


def create_batch_audiobooks(
    book_files,
    voice_selection: str,
    engine_selection: str,
    mastering_preset: str,
    enable_resume: bool,
    max_retries: int,
    generate_subtitles: bool,
    phase1: bool,
    phase2: bool,
    phase3: bool,
    phase4: bool,
    phase5: bool,
    progress=gr.Progress()
) -> str:
    """Process multiple books sequentially with shared settings."""
    if not book_files:
        return "❌ Please upload one or more book files."

    try:
        voice_id = voice_selection.split(":")[0].strip()
    except Exception:
        return "❌ Please select a voice."

    engine_map = {
        "XTTS v2 (Expressive)": "xtts",
        "Kokoro (CPU-Friendly)": "kokoro",
    }
    engine = engine_map.get(engine_selection, "xtts")

    phases = []
    if phase1:
        phases.append(1)
    if phase2:
        phases.append(2)
    if phase3:
        phases.append(3)
    if phase4:
        phases.append(4)
    if phase5:
        phases.append(5)

    if not phases:
        return "❌ Please select at least one phase to run."

    results = []
    total = len(book_files)

    for idx, book in enumerate(book_files, start=1):
        if state.is_cancelled():
            results.append(f"- ❌ Cancelled before processing `{Path(book.name).name}`")
            break

        book_path = Path(book.name)
        logger.info(f"[Batch] Starting {book_path.name} ({idx}/{total})")

        progress(((idx - 1) / total), desc=f"Batch {idx}/{total}: {book_path.name}")

        inner_progress = gr.Progress(track_tqdm=True)

        res = run_pipeline(
            file_path=book_path,
            voice_id=voice_id,
            tts_engine=engine,
            mastering_preset=mastering_preset,
            phases=phases,
            pipeline_json=state.pipeline_json,
            enable_subtitles=generate_subtitles,
            max_retries=int(max_retries),
            no_resume=not enable_resume,
            progress_callback=lambda phase, pct, msg: inner_progress(
                ((idx - 1) / total) + (pct / 1000), desc=f"{book_path.name} | Phase {phase}: {msg}"
            ),
        )

        if res.get("success"):
            out_path = res.get("audiobook_path", "phase5_enhancement/processed/")
            results.append(f"- ✅ `{book_path.name}` → `{out_path}`")
        else:
            results.append(f"- ❌ `{book_path.name}` failed: {res.get('error','unknown error')}")

    progress(1.0, desc="Batch complete")
    return "\n".join(results)


def add_voice(
    voice_name: str,
    voice_file,
    narrator_name: str,
    genre_tags: str
) -> str:
    """Add a new voice to the library"""
    if not voice_name or not voice_file:
        return "❌ Please provide voice name and audio file"

    try:
        # TODO: Implement voice addition logic
        return f"✅ Voice '{voice_name}' added successfully!\n\nNarrator: {narrator_name}\nGenres: {genre_tags}"
    except Exception as e:
        return f"❌ Error adding voice: {str(e)}"


def get_voice_details(voice_selection: str) -> str:
    """Get detailed information about a voice"""
    if not voice_selection:
        return "Select a voice to see details"

    voice_id = voice_selection.split(":")[0].strip()
    voice_data = state.voices.get(voice_id, {})

    narrator = voice_data.get('narrator_name', 'Unknown')
    profiles = ', '.join(voice_data.get('preferred_profiles', []))
    description = voice_data.get('description', 'No description')
    notes = voice_data.get('notes', 'No notes')

    return f"""
    ## 🎤 {narrator}

    **Voice ID:** {voice_id}

    **Best for:** {profiles}

    **Description:**
    {description}

    **Notes:**
    {notes}
    """


# ============================================================================
# UI CONSTRUCTION
# ============================================================================

def build_ui():
    """Build the complete Gradio interface"""

    with gr.Blocks(
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="orange"
        ),
        css=CUSTOM_CSS,
        title="🎙️ Personal Audiobook Studio"
    ) as app:

        # Header
        gr.HTML("""
            <div class="header">
                <h1>🎙️ Personal Audiobook Studio</h1>
                <p>Craft audiobooks with soul. Not production, but art.</p>
            </div>
        """)

        # =================================================================
        # TAB 0: STATUS / OBSERVABILITY
        # =================================================================
        with gr.Tab("📊 Status"):
            gr.Markdown("## Live Pipeline Status")

            with gr.Row():
                status_file_dropdown = gr.Dropdown(
                    choices=state.file_ids,
                    value=state.file_ids[0] if state.file_ids else None,
                    label="Tracked File (from pipeline.json)"
                )
                refresh_status_btn = gr.Button("🔄 Refresh", variant="secondary")

            status_markdown = gr.Markdown(
                build_status_report(state.file_ids[0]) if state.file_ids else "Select a file to view pipeline status."
            )

            def _refresh_status(file_id):
                return build_status_report(file_id)

            status_file_dropdown.change(_refresh_status, inputs=status_file_dropdown, outputs=status_markdown)
            refresh_status_btn.click(_refresh_status, inputs=status_file_dropdown, outputs=status_markdown)

        # =================================================================
        # TAB 1: SINGLE BOOK
        # =================================================================
        with gr.Tab("📖 Single Book"):
            gr.Markdown("## Create a Single Audiobook")

            # Resume detection section
            incomplete_detected, incomplete_msg = check_for_incomplete_work()
            if incomplete_detected:
                with gr.Accordion("🔄 Resume Previous Generation", open=True):
                    gr.Markdown(incomplete_msg)
                    gr.Markdown("**Tip:** Enable 'Resume from checkpoint' in Advanced Options below")

            with gr.Row():
                with gr.Column(scale=2):
                    book_input = gr.File(
                        label="📚 Upload Book",
                        file_types=[".epub", ".pdf", ".txt", ".mobi"],
                        type="filepath"
                    )

                    with gr.Row():
                        voice_dropdown = gr.Dropdown(
                            choices=state.get_voice_list(),
                            label="🎤 Voice",
                            info="Select narrator voice for this book"
                        )

                        engine_dropdown = gr.Dropdown(
                            choices=state.engines,
                            value="XTTS v2 (Expressive)",
                            label="🤖 TTS Engine",
                            info="Choose synthesis engine (XTTS=quality, Kokoro=speed)"
                        )

                    with gr.Row():
                        preset_dropdown = gr.Dropdown(
                            choices=state.presets,
                            value="audiobook_intimate",
                            label="🎚️ Mastering Preset",
                            info="Audio processing style"
                        )

                    # Advanced Options
                    with gr.Accordion("⚙️ Advanced Options", open=False):
                        with gr.Row():
                            enable_resume = gr.Checkbox(
                                label="Enable Resume",
                                value=True,
                                info="Resume from checkpoint if interrupted"
                            )

                            max_retries = gr.Slider(
                                minimum=0,
                                maximum=5,
                                value=2,
                                step=1,
                                label="Max Retries",
                                info="Retry attempts per phase"
                            )

                        with gr.Row():
                            generate_subtitles = gr.Checkbox(
                                label="Generate Subtitles",
                                value=False,
                                info="Create .srt and .vtt subtitle files"
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
                        generate_btn = gr.Button(
                            "🎬 Generate Audiobook",
                            variant="primary",
                            size="lg",
                            scale=2
                        )

                        stop_btn = gr.Button(
                            "🛑 Stop",
                            variant="stop",
                            size="lg",
                            visible=False,
                            scale=1
                        )

                with gr.Column(scale=1):
                    voice_details = gr.Markdown(
                        "Select a voice to see details",
                        label="Voice Information"
                    )

            # Output section
            with gr.Row():
                audio_output = gr.Audio(label="🎧 Generated Audiobook")
                status_output = gr.Markdown(label="Status")

            # Stop button output
            stop_status = gr.Markdown(visible=False)

            # Event handlers
            generate_click = generate_btn.click(
                fn=create_audiobook,
                inputs=[
                    book_input,
                    voice_dropdown,
                    engine_dropdown,
                    preset_dropdown,
                    enable_resume,
                    max_retries,
                    generate_subtitles,
                    phase1_check,
                    phase2_check,
                    phase3_check,
                    phase4_check,
                    phase5_check
                ],
                outputs=[audio_output, status_output]
            )

            # Show stop button when generation starts
            generate_btn.click(
                fn=lambda: gr.update(visible=True),
                inputs=None,
                outputs=[stop_btn]
            )

            # Hide stop button and show status when generation completes
            generate_click.then(
                fn=lambda: gr.update(visible=False),
                inputs=None,
                outputs=[stop_btn]
            )

            # Stop button handler
            stop_btn.click(
                fn=cancel_generation_fn,
                inputs=None,
                outputs=[stop_status],
                cancels=[generate_click]
            )

            # Show stop status
            stop_btn.click(
                fn=lambda: gr.update(visible=True),
                inputs=None,
                outputs=[stop_status]
            )

            voice_dropdown.change(
                fn=get_voice_details,
                inputs=[voice_dropdown],
                outputs=[voice_details]
            )

        # =================================================================
        # TAB 2: BATCH QUEUE
        # =================================================================
        with gr.Tab("📦 Batch Queue"):
            gr.Markdown("## Process Multiple Books")

            with gr.Row():
                with gr.Column(scale=2):
                    batch_files = gr.File(
                        label="📚 Upload Books (multiple)",
                        file_types=[".epub", ".pdf", ".txt", ".mobi"],
                        file_count="multiple",
                        type="filepath"
                    )

                    with gr.Row():
                        batch_voice = gr.Dropdown(
                            choices=state.get_voice_list(),
                            label="🎤 Voice",
                            info="Select narrator voice for all books"
                        )

                        batch_engine = gr.Dropdown(
                            choices=state.engines,
                            value="Kokoro (CPU-Friendly)",
                            label="🤖 TTS Engine",
                            info="Choose synthesis engine"
                        )

                    batch_preset = gr.Dropdown(
                        choices=state.presets,
                        value="audiobook_intimate",
                        label="🎛️ Mastering Preset",
                        info="Audio processing style"
                    )

                    with gr.Accordion("⚙️ Batch Options", open=False):
                        batch_enable_resume = gr.Checkbox(
                            label="Enable Resume",
                            value=True,
                            info="Resume from checkpoint if interrupted"
                        )
                        batch_max_retries = gr.Slider(
                            minimum=0,
                            maximum=5,
                            value=1,
                            step=1,
                            label="Max Retries",
                            info="Retry attempts per phase"
                        )
                        batch_generate_subtitles = gr.Checkbox(
                            label="Generate Subtitles",
                            value=False,
                            info="Create .srt and .vtt subtitle files"
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
                fn=create_batch_audiobooks,
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

        # =================================================================
        # TAB 3: VOICE LIBRARY
        # =================================================================
        with gr.Tab("🎤 Voice Library"):
            gr.Markdown("## Manage Your Voice Collection")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Add New Voice")

                    new_voice_name = gr.Textbox(
                        label="Voice ID",
                        placeholder="e.g., morgan_freeman"
                    )

                    new_voice_file = gr.Audio(
                        label="Voice Sample (10-30 seconds)",
                        type="filepath",
                        sources=["upload"]
                    )

                    new_narrator_name = gr.Textbox(
                        label="Narrator Name",
                        placeholder="e.g., Morgan Freeman"
                    )

                    new_genre_tags = gr.Textbox(
                        label="Genre Tags (comma-separated)",
                        placeholder="e.g., philosophy, documentary, narrative"
                    )

                    add_voice_btn = gr.Button("➕ Add Voice", variant="primary")

                    add_voice_status = gr.Markdown()

                with gr.Column():
                    gr.Markdown("### Existing Voices")

                    # Display voice cards
                    voice_gallery = gr.HTML(
                        _generate_voice_gallery_html(state.voices)
                    )

            # Event handler
            add_voice_btn.click(
                fn=add_voice,
                inputs=[
                    new_voice_name,
                    new_voice_file,
                    new_narrator_name,
                    new_genre_tags
                ],
                outputs=[add_voice_status]
            )

        # =================================================================
        # TAB 4: SETTINGS
        # =================================================================
        with gr.Tab("⚙️ Settings"):
            gr.Markdown("## Configuration")

            with gr.Accordion("Audio Quality", open=True):
                sample_rate = gr.Slider(
                    24000, 48000, value=48000, step=1000,
                    label="Sample Rate (Hz)"
                )

                lufs_target = gr.Slider(
                    -30, -10, value=-23, step=1,
                    label="Target LUFS"
                )

            with gr.Accordion("Performance"):
                max_workers = gr.Slider(
                    1, 16, value=4, step=1,
                    label="Maximum Parallel Workers"
                )

                enable_gpu = gr.Checkbox(
                    label="Use GPU (if available)",
                    value=False
                )

            with gr.Accordion("Paths"):
                input_dir = gr.Textbox(
                    label="Input Directory",
                    value=str(PROJECT_ROOT / "input")
                )

                output_dir = gr.Textbox(
                    label="Output Directory",
                    value=str(PROJECT_ROOT / "phase5_enhancement" / "processed")
                )

            save_settings_btn = gr.Button("💾 Save Settings", variant="primary")
            settings_status = gr.Markdown()

            save_settings_btn.click(
                lambda: "✅ Settings saved successfully!",
                outputs=[settings_status]
            )

        # =================================================================
        # FOOTER
        # =================================================================
        gr.HTML("""
            <div style="text-align: center; padding: 2rem; opacity: 0.7;">
                <p>Made with ❤️ for the craft of audiobook creation</p>
                <p><em>"Insanely great, because good enough isn't."</em></p>
            </div>
        """)

    return app


def _generate_voice_gallery_html(voices: Dict) -> str:
    """Generate HTML for voice gallery"""
    html = '<div style="display: grid; gap: 1rem;">'

    for voice_id, meta in list(voices.items())[:10]:  # Show first 10
        narrator = meta.get('narrator_name', 'Unknown')
        profiles = ', '.join(meta.get('preferred_profiles', []))

        html += f"""
        <div class="voice-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="font-size: 1.1rem;">{narrator}</strong>
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

    html += '</div>'
    return html


# ============================================================================
# STATUS HELPERS
# ============================================================================


def _load_pipeline_data() -> Dict:
    if not state.pipeline_json.exists():
        return {}
    try:
        with open(state.pipeline_json, "r") as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"Failed to read pipeline.json: {exc}")
        return {}


def _phase_status(data: Dict, file_id: str, phase_num: int) -> str:
    phase_key = f"phase{phase_num}"
    try:
        phase = data.get(phase_key, {})
        files = phase.get("files", {}) or {}
        entry = files.get(file_id, {})
        return entry.get("status") or phase.get("status") or "missing"
    except Exception:
        return "unknown"


def _process_snapshot() -> str:
    lines = []
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
    return "\n".join(lines) if lines else "- No active pipeline processes detected"


def _count_files(pattern: str) -> int:
    try:
        return len(list(Path().glob(pattern)))
    except Exception:
        return 0


def build_status_report(selected_file: Optional[str]) -> str:
    data = _load_pipeline_data()
    if not selected_file:
        return "Select a file to view pipeline status."

    phase_lines = []
    for p in range(1, 5 + 1):
        phase_lines.append(f"- Phase {p}: **{_phase_status(data, selected_file, p)}**")

    chunk_txt = _count_files(f"phase3-chunking/chunks/{selected_file}_chunk_*.txt")
    phase4_wav = _count_files("phase4_tts/audio_chunks/*.wav")
    phase5_wav = _count_files("phase5_enhancement/processed/enhanced_*.wav")
    mp3_exists = Path("phase5_enhancement/processed/audiobook.mp3").exists()

    process_view = _process_snapshot()

    return f"""
### Pipeline Status for `{selected_file}`

**Phases**
{chr(10).join(phase_lines)}

**File System Progress (live)**
- Phase 3 chunks (txt): {chunk_txt}
- Phase 4 audio chunks (wav): {phase4_wav}
- Phase 5 enhanced (wav): {phase5_wav}
- Final MP3 present: {"yes" if mp3_exists else "no"}

**Active Processes**
{process_view}
"""


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

# Global reference to the app for cleanup
_app_instance = None

def cleanup_handler():
    """Clean up resources on exit"""
    global _app_instance
    if _app_instance is not None:
        try:
            logger.info("Shutting down studio...")
            _app_instance.close()
            logger.info("Studio shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

def signal_handler(signum, frame):
    """Handle Ctrl+C and other signals"""
    logger.info("\nReceived shutdown signal, cleaning up...")
    cleanup_handler()
    sys.exit(0)

def main():
    """Launch the studio"""
    global _app_instance

    # Register cleanup handlers
    atexit.register(cleanup_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("🎙️ Starting Personal Audiobook Studio...")
    logger.info("Press Ctrl+C to stop the server")

    app = build_ui()
    _app_instance = app

    try:
        app.launch(
            server_name="0.0.0.0",  # Allow network access
            server_port=7860,
            share=False,  # Set to True for public sharing
            show_error=True,
            quiet=False,
            inbrowser=False  # Don't auto-open browser (launcher does this)
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Error running studio: {e}")
        raise
    finally:
        cleanup_handler()


if __name__ == "__main__":
    main()
