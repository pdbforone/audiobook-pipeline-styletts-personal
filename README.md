# Personal Audiobook Studio

**Craft audiobooks with soul. Not production, but art.**

This project is an autonomous, self-healing pipeline for converting text into high-quality audiobooks for personal use. It leverages a suite of local AI agents and multiple TTS engines to automate the entire process, from text extraction and semantic chunking to voice synthesis and audio mastering.

Originally designed as a lean commercial publishing pipeline, the system is now optimized for private study and enjoyment, with a focus on creative control and audio excellence.

---

## 🚀 Getting Started

There are two main ways to use the pipeline:

1.  **The Studio UI (Recommended)**: A user-friendly Gradio interface for creating audiobooks one at a time. This is the easiest way to get started.
    *   **Quick Start Guide:** [QUICKSTART.md](./QUICKSTART.md)

2.  **CLI / Batch Processing (Advanced)**: For power users, manifest-based batch processing, and integration into larger workflows.
    *   **Setup Guide:** [SETUP_GUIDE.md](./SETUP_GUIDE.md)

---

## 📖 Project Documentation

This project is extensively documented. Use these guides to understand the architecture, development environment, and various features.

| Document                                   | Purpose                                                                                           |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| **[PROJECT_OVERVIEW.md]**                  | **Start here.** A high-level blueprint of the project's vision, architecture, and production workflow. |
| **[AUTONOMOUS_PIPELINE_ROADMAP.md]**         | The living document tracking the project's evolution, latest features, and future plans.          |
| **[SETUP_GUIDE.md]**                       | Detailed instructions for setting up the development environment for all phases.                  |
| **[QUICKSTART.md]**                        | A 10-minute guide to generating your first audiobook using the Gradio UI.                         |
| **[ENVIRONMENTS.md]**                      | An explanation of the project's multi-environment setup (Poetry, Conda).                          |
| **[PIPELINE_JSON_SCHEMA.md]**                | An overview of the `pipeline.json` state file, which points to the canonical `schema.json`.       |
| **[VOICE_OVERRIDE_GUIDE.md]**                | A guide to using different voices for narration and characters.                                   |

---

## ✨ Core Features

*   **Multi-Engine TTS**: Dynamically uses the best TTS engine for the job (`XTTS` for expressive quality, `Kokoro` for speed) with automatic fallbacks.
*   **AI-Powered Agents**: A suite of specialized LLM agents for tasks like semantic chunking, text validation, voice selection, and error analysis.
*   **Self-Healing & Resilience**: The pipeline can detect its own failures, analyze the root cause, and attempt to self-repair (e.g., by rewriting problematic text or switching engines).
*   **Schema-Enforced State**: A strict JSON schema and Pydantic models ensure the integrity of `pipeline.json`, the single source of truth for all pipeline operations.
*   **Gradio UI**: A modern, easy-to-use web interface for managing the entire audiobook creation process.

## 🛠 Architecture Overview

The pipeline is composed of several isolated phases, orchestrated by the UI or a CLI runner. Each phase operates on data from the previous phase and writes its results back to the central `pipeline.json` state file.

1.  **Phase 1: Validation**: Verifies input file integrity.
2.  **Phase 2: Extraction**: Extracts clean text from various formats (PDF, ePub, etc.).
3.  **Phase 3: Chunking**: Splits text into semantically coherent chunks for TTS.
4.  **Phase 4: Synthesis**: Converts text chunks into audio using the selected TTS engine.
5.  **Phase 5: Enhancement**: Masters the audio (normalization, noise reduction, etc.).
6.  **Phase 5.5 (Optional)**: Generates subtitles.

For a deeper dive, see the architecture section in the [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md).

[PROJECT_OVERVIEW.md]: ./PROJECT_OVERVIEW.md
[AUTONOMOUS_PIPELINE_ROADMAP.md]: ./AUTONOMOUS_PIPELINE_ROADMAP.md
[SETUP_GUIDE.md]: ./SETUP_GUIDE.md
[QUICKSTART.md]: ./QUICKSTART.md
[ENVIRONMENTS.md]: ./ENVIRONMENTS.md
[PIPELINE_JSON_SCHEMA.md]: ./PIPELINE_JSON_SCHEMA.md
[VOICE_OVERRIDE_GUIDE.md]: ./VOICE_OVERRIDE_GUIDE.md
