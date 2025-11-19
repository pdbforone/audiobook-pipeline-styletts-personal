# Phase Documentation Map

Quick reference for per-phase docs and key entrypoints across the pipeline.

## Phase 1 – Validation
- Doc: `phase1-validation/README.md`
- Script: `phase1-validation/src/phase1_validation/validation.py`
- Purpose: validate/repair inputs (PDF/EPUB/DOCX/TXT), classify PDFs, hash reuse, update `pipeline.json`.

## Phase 2 – Extraction
- Doc: `phase2-extraction/README.md`
- Script: `phase2-extraction/src/phase2_extraction/extraction.py`
- Purpose: multi-pass text extraction (pypdf/pdfplumber/PyMuPDF), quality scoring, optional TTS normalization, reuse via source hash, writes extracted text + `pipeline.json`.

## Phase 3 – Structure & Chunking
- Doc: `phase3-chunking/README.md`
- Docs also: `STRUCTURE_ENHANCEMENT_README.md`, `PHASE3_CHUNKING_FIXES.md`, `PHASE3_4_ANALYSIS.md`
- Purpose: detect structure, split into TTS-sized chunks; integrates spaCy/pySBD sentence detection.

## Phase 4 – TTS
- Doc: `phase4_tts/README.md`
- Docs also: `PHASE4_VALIDATION_GUIDE.md`, `VOICE_SELECTION_GUIDE.md`, `DROID_VOICE_GUIDE.md`, `VOICE_*` guides; config in `phase4_tts/config.yaml`.
- Script: `phase4_tts/src/main_multi_engine.py`
- Purpose: XTTS/Kokoro engines with auto-engine, latency fallback, CPU guardrails (worker cap, optional psutil-based downscale).

## Phase 5 – Enhancement
- Doc: `phase5_enhancement/README.md`
- Docs also: `PHASE5_GUIDE.md`, `SPRINT1_AUDIO_MASTERING.md`, `phase5_enhancement` configs.
- Purpose: denoise/normalize/master, optional Silero VAD trimming, RNNoise/DeepFilterNet/noisereduce support.

## Phase 5.5 – Subtitles (optional)
- Docs: `PHASE_5.5_SUBTITLES_PLAN.md`, `SUBTITLE_PUBLISHING_STATUS.md`
- Purpose: forced alignment (aeneas) when requested.

## Phase 6 – Orchestration
- Doc: `phase6_orchestrator/README.md`
- Docs also: `STRUCTURE_ENHANCEMENT_README.md` (orchestration notes)
- Purpose: coordinate phases, manage notifications, pass configs/paths.

## Phase 7 – Batch
- Doc: `phase7_batch/README.md`
- Docs also: `PHASE_6.5_PUBLISHING_PLAN.md`, `phase7_batch` scripts.
- Purpose: batch mode wrapper, single-worker safety in batch context.

## Cross-cutting
- Pipeline schema: `PIPELINE_JSON_SCHEMA.md`, `PROJECT_OVERVIEW.md`.
- Voice docs: `VOICE_SELECTION_GUIDE.md`, `VOICE_OVERRIDE_GUIDE.md` (under `phase4_tts`).
- UI: `ui/app.py` (Gradio) with Status tab, paged summaries, log tail.
