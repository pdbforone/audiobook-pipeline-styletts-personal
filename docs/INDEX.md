# Documentation Index

This document provides a categorized index of all major documentation files in the Personal Audiobook Studio project. Use this as a central hub to navigate the project's architecture, guides, and historical context.

---

## 🚀 Getting Started

These documents provide the fastest path to setting up and using the application.

- **[README.md](../README.md)**: The main entry point for the project. Provides a high-level overview and links to other key documents.
- **[QUICKSTART.md](../QUICKSTART.md)**: A 10-minute guide to generating your first audiobook using the Gradio UI.
- **[SETUP_GUIDE.md](../SETUP_GUIDE.md)**: Detailed, authoritative instructions for setting up the complete development environment.
- **[ENVIRONMENTS.md](../ENVIRONMENTS.md)**: An essential guide explaining the project's multi-environment setup (Poetry, Conda).

---

## 🏛️ Project & Architecture

High-level documents explaining the project's vision, design, and evolution.

- **[PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md)**: The canonical blueprint of the project, detailing its business origins, current personal-use focus, system architecture, and production workflow. **Recommended first read.**
- **[AUTONOMOUS_PIPELINE_ROADMAP.md](../AUTONOMOUS_PIPELINE_ROADMAP.md)**: The living document tracking the project's evolution, latest features, and future plans.
- **[ARCHITECTURE_DECISION.md](../ARCHITECTURE_DECISION.md)**: Documents key architectural decisions and their rationale.
- **[PIPELINE_JSON_SCHEMA.md](../PIPELINE_JSON_SCHEMA.md)**: An overview of the `pipeline.json` state file, which points to the canonical `schema.json` for data integrity.

---

## 📖 User Guides

Guides for using specific features of the pipeline and UI.

- **[MASTER_GUIDE.md](../MASTER_GUIDE.md)**: A comprehensive guide to using the pipeline.
- **[VOICE_SELECTION_GUIDE.md](../phase4_tts/VOICE_SELECTION_GUIDE.md)**: How to select and use different TTS voices.
- **[VOICE_OVERRIDE_GUIDE.md](../VOICE_OVERRIDE_GUIDE.md)**: How to override the default voice for specific chunks or files.
- **[KARAOKE_SUBTITLES_GUIDE.md](../KARAOKE_SUBTITLES_GUIDE.md)**: A guide to generating and using karaoke-style subtitles.
- **[UI_IMPROVEMENTS.md](../UI_IMPROVEMENTS.md)**: Details on the features and design of the Gradio UI.
- **[VIDEO_GENERATOR_README.md](../VIDEO_GENERATOR_README.md)**: Instructions for the video generator tool.

---

## 🛠️ Developer & Phase-Specific Guides

Technical documentation for developers working on the pipeline.

- **[PHASE_DOCS.md](../PHASE_DOCS.md)**: General documentation about the different phases of the pipeline.
- **`phase4_tts/`**:
  - **[README.md](../phase4_tts/README.md)**: README for the TTS Synthesis phase.
  - **[PHASE4_VALIDATION_GUIDE.md](../phase4_tts/PHASE4_VALIDATION_GUIDE.md)**: Deep dive into the validation steps within Phase 4.
- **`phase5_enhancement/`**:
  - **[PHASE5_GUIDE.md](../PHASE5_GUIDE.md)**: Guide to the audio enhancement and mastering phase.
- **`phase6_orchestrator/`**:
  - **[README.md](../phase6_orchestrator/README.md)**: README for the Orchestrator.
  - **[TROUBLESHOOTING.md](../phase6_orchestrator/TROUBLESHOOTING.md)**: Specific troubleshooting steps for the orchestrator.
- **`agents/`**:
  - **[ASR_LLAMA_INTEGRATION.md](../ASR_LLAMA_INTEGRATION.md)**: Explains how ASR validation and LLM-based text rewriting work together.

---

## 💡 Proposals, Planning & Analysis

Documents related to project planning, feature proposals, and analysis of issues.

- **[DESIGN_FIRST_REFACTOR_PLAN.md](../DESIGN_FIRST_REFACTOR_PLAN.md)**: The plan for a design-first refactoring initiative.
- **[POLICY_ENGINE.md](../POLICY_ENGINE.md)**: Documentation for the policy engine that guides autonomous decisions.
- **[RESILIENCE_FEATURES.md](../RESILIENCE_FEATURES.md)**: A summary of features designed to make the pipeline more resilient.
- **[PHASE4_PARALLEL_PROCESSING.md](../PHASE4_PARALLEL_PROCESSING.md)**: Analysis and planning for parallel processing in Phase 4.
- **[LEGACY_DIRECTORIES_ANALYSIS.md](../LEGACY_DIRECTORIES_ANALYSIS.md)**: Analysis of legacy directories and a plan for cleanup.

---

## 🔧 Troubleshooting & Fixes

Historical documents detailing bugs, their fixes, and diagnostic reports. These are valuable for understanding the system's history and avoiding regressions.

- **[PHASE3_RESUME_BUG.md](../PHASE3_RESUME_BUG.md)**: Analysis of a bug related to resuming Phase 3.
- **[CHUNK_ORDER_BUG_FIX.md](../phase6_orchestrator/CHUNK_ORDER_BUG_FIX.md)**: Explanation of a fix for a chunk ordering bug.
- **[VOICE_OVERRIDE_BUG_FIX.md](../VOICE_OVERRIDE_BUG_FIX.md)**: Details on a fix for a bug in the voice override system.
- **[XTTS_DIAGNOSTIC_REPORT.md](../phase4_tts/XTTS_DIAGNOSTIC_REPORT.md)**: A diagnostic report for the XTTS engine.

---
This index is not exhaustive but covers the most critical documents for understanding and contributing to the project.
