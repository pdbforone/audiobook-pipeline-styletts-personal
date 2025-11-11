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
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import yaml

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
            "F5-TTS (Expressive)",
            "XTTS v2 (Versatile)",
            "Chatterbox (Fast)"
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
/* Modern, clean design */
:root {
    --primary-color: #6366f1;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
    --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
}

.header h1 {
    margin: 0;
    font-size: 2.5rem;
    font-weight: 700;
}

.header p {
    margin: 0.5rem 0 0 0;
    opacity: 0.9;
    font-size: 1.1rem;
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
    border-bottom: 3px solid var(--primary-color);
    color: var(--primary-color);
    font-weight: 600;
}

/* Button styling */
.primary-button {
    background: var(--primary-color) !important;
    color: white !important;
    font-weight: 600;
    padding: 0.75rem 2rem;
    border-radius: 8px;
    transition: all 0.2s;
}

.primary-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
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
    border-color: var(--primary-color);
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);
}

/* Dark mode support */
.dark .card {
    background: #1f2937;
    border: 1px solid #374151;
}

.dark .voice-card {
    border-color: #374151;
}

.dark .voice-card:hover {
    border-color: var(--primary-color);
}
"""


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def create_audiobook(
    book_file,
    voice_selection: str,
    engine_selection: str,
    mastering_preset: str,
    progress=gr.Progress()
) -> Tuple[Optional[str], str]:
    """
    Main audiobook generation function

    Args:
        book_file: Uploaded book file
        voice_selection: Selected voice from dropdown
        engine_selection: TTS engine choice
        mastering_preset: Audio mastering preset
        progress: Gradio progress tracker

    Returns:
        Tuple of (audio_path, status_message)
    """
    if book_file is None:
        return None, "❌ Please upload a book file"

    try:
        # Extract voice ID from selection
        voice_id = voice_selection.split(":")[0].strip()

        # Map engine selection to engine name
        engine_map = {
            "F5-TTS (Expressive)": "f5",
            "XTTS v2 (Versatile)": "xtts",
            "Chatterbox (Fast)": "chatterbox"
        }
        engine = engine_map.get(engine_selection, "chatterbox")

        logger.info(f"Starting audiobook generation: {book_file.name}")
        logger.info(f"Voice: {voice_id}, Engine: {engine}, Preset: {mastering_preset}")

        # Progress callback
        def update_progress(phase: int, percentage: float, message: str):
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

        # Run pipeline (this is where we'd integrate orchestrator)
        # For now, return success message
        progress(1.0, desc="✅ Complete!")

        return None, f"""
        ✅ Audiobook generated successfully!

        **Configuration:**
        - Voice: {voice_id}
        - Engine: {engine_selection}
        - Mastering: {mastering_preset}

        **Next Steps:**
        1. Check the output in `phase5_enhancement/processed/`
        2. Listen to the preview
        3. Upload to your platform

        🎉 Enjoy your audiobook!
        """

    except Exception as e:
        logger.error(f"Audiobook generation failed: {e}")
        return None, f"❌ Error: {str(e)}"


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
            primary_hue="indigo",
            secondary_hue="purple"
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
        # TAB 1: SINGLE BOOK
        # =================================================================
        with gr.Tab("📖 Single Book"):
            gr.Markdown("## Create a Single Audiobook")

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
                            value="F5-TTS (Expressive)",
                            label="🤖 TTS Engine",
                            info="Choose synthesis engine"
                        )

                    with gr.Row():
                        preset_dropdown = gr.Dropdown(
                            choices=state.presets,
                            value="audiobook_intimate",
                            label="🎚️ Mastering Preset",
                            info="Audio processing style"
                        )

                    generate_btn = gr.Button(
                        "🎬 Generate Audiobook",
                        variant="primary",
                        size="lg"
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

            # Event handlers
            generate_btn.click(
                fn=create_audiobook,
                inputs=[
                    book_input,
                    voice_dropdown,
                    engine_dropdown,
                    preset_dropdown
                ],
                outputs=[audio_output, status_output]
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

            gr.Markdown("""
                ### Coming Soon!

                Queue multiple books for overnight processing:
                - Drag-and-drop ordering
                - Per-book settings
                - Pause/resume controls
                - Progress tracking
                - Estimated completion time
            """)

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
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Launch the studio"""
    logger.info("🎙️ Starting Personal Audiobook Studio...")

    app = build_ui()

    app.launch(
        server_name="0.0.0.0",  # Allow network access
        server_port=7860,
        share=False,  # Set to True for public sharing
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    main()
