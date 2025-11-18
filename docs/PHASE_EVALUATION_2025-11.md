# Phase Evaluation Report · November 2025

> **Scope:** Snapshot of every pipeline phase (1–7 plus 5.5) as used by the Personal Audiobook Studio for private listening. Each section lists the current role, observed strengths, friction points, and concrete improvements you can pursue next.

## Executive Summary

| Phase | Health | Top Priority | Why it Matters |
|-------|--------|--------------|----------------|
| 1. Validation & Repair | 🟡 **Steady** | Regression tests for repair helpers | Keeps fragile PDF fixes from regressing when dependencies change. |
| 2. Text Extraction | 🟡 **Steady** | OCR telemetry + EPUB tags | Better diagnostics and richer structure improve downstream chunking. |
| 3. Semantic Chunking | 🟡 **Steady** | UI previews + multilingual fixtures | Prevents silent errors and adds confidence for non-English texts. |
| 4. TTS Synthesis | 🟠 **At Risk** | Smoke tests + voice asset checks | Catches breaking refactors and missing samples before long runs. |
| 5. Audio Enhancement | 🟡 **Steady** | Adaptive presets + silence QA | Keeps private masters comfortable to listen to in every context. |
| 5.5 Subtitles | 🟡 **Optional** | Chunk retries + glossary | Saves time when personal titles need searchable transcripts. |
| 6. Orchestration | 🟠 **Advanced** | UI/CLI contract audit | Prevents drift between Studio toggles and CLI runtime. |
| 7. Batch Processing | 🟠 **Advanced** | Studio parity + cleanup policies | Enables experiments without polluting disk or guessing worker counts. |

> **Reading tip:** Skim the table above, then jump into the relevant phase section below for details on assets, strengths, and actionable fixes.

## How to Use This Document
1. **Pick a phase** you plan to touch (UI button, CLI run, or batch manifest) and skim its section below.
2. **Review the "What Works" bullets** to understand the guarantees already in place so you do not regress them accidentally.
3. **Treat "Needs Improvement" as the prioritized backlog**—each bullet specifies an owner, artifact, or test gap so you can turn it into an issue or work item quickly.
4. **Track follow-ups** back in `PROJECT_OVERVIEW.md` (Phase status table) or inside each phase-specific README when the improvement ships.

---

## Phase 1 – Validation & Repair
**Current role:** Ensures source PDFs/EPUBs are readable before extraction; feeds deduplicated metadata into `pipeline.json`.

### Key Assets
- `phase1-validation/src/repair.py` (repair helpers)
- `pipeline_common/validation.py` (shared validators used by UI + CLI)
- Studio UI status card (Phase 1 tab)

### What Works
- Multipass repair functions already catch most encryption and malformed cross-reference tables.
- Metadata merging de-dupes by SHA so rereads never overwrite good runs.
- CLI + Studio UI share the same entry point, so logs are consistent.

### Needs Improvement
1. **Automated regression coverage.**
   - **Focus:** Add pytest fixtures (`tests/phase1/test_repair.py`) with known-bad PDFs/EPUBs to guard the helper stack.
   - **Owner Artifact:** `phase1-validation/tests/` (new package) plus sample files under `fixtures/phase1/`.
   - **Proof:** CI badge + `pytest phase1-validation/tests -k repair` run recorded in `VALIDATION_TESTS.md`.
2. **Corrupt EPUB handling.**
   - **Focus:** Integrate `epubcheck` CLI (or Python wrapper) and a fallback `zipfile` path that extracts spine HTML when metadata is missing.
   - **Owner Artifact:** `phase1-validation/src/epub_flow.py` (new helper) with integration wiring in `pipeline_common/validation.py`.
   - **Proof:** Demo EPUB added to `docs/personal_listening_log.md` backlog plus log snippet showing graceful fallback.
3. **User feedback in UI.**
   - **Focus:** Map common failure codes to short remediation bullets ("Re-download the source," "Flatten with Ghostscript") so the Studio shows actionable advice instead of raw logs.
   - **Owner Artifact:** `ui/app.py` (Phase 1 panel) + `ui/components/alerts.py` (new helper for status text).
   - **Proof:** Screenshot in the personal wiki + acceptance test where Gradio displays the checklist on mock failure.

---

## Phase 2 – Text Extraction
**Current role:** Converts vetted sources into normalized text with light cleaning and OCR assist.

### Key Assets
- `phase2-extraction/src/extract_pdf.py`
- `phase2-extraction/src/extract_epub.py`
- Extraction telemetry appended to `pipeline.json`

### What Works
- Multipass extractor (PyPDF, pdfplumber, PyMuPDF) prevents vendor lock-in.
- Yield and language metrics write back to `pipeline.json`, giving us an audit trail for low-quality scans.
- Normalization trims weird whitespace and smart quotes, reducing downstream chunking work.

### Needs Improvement
1. **OCR routing telemetry.**
   - **Focus:** Capture DPI, `psm`, `oem`, and retry counts when pytesseract engages; persist under `pipeline.json > phases > extraction > ocr`.
   - **Owner Artifact:** `phase2-extraction/src/ocr.py` plus schema update in `PIPELINE_JSON_SCHEMA.md`.
   - **Proof:** Sample log snippet + unit test that asserts telemetry keys exist when OCR flag is true.
2. **EPUB structural tags.**
   - **Focus:** Preserve `<h1>–<h3>` + `<em>` markers through normalization so Phase 3 chunker can treat them as strong hints.
   - **Owner Artifact:** `phase2-extraction/src/extract_epub.py` + `phase3-chunking/src/hints.py` for consumption.
   - **Proof:** Golden-file test comparing old/new normalized output for a Project Gutenberg EPUB.
3. **Performance on large PDFs.**
   - **Focus:** Stream pages chapter-by-chapter by leveraging PyMuPDF iterators instead of loading the full document into RAM.
   - **Owner Artifact:** `phase2-extraction/src/extract_pdf.py` plus CLI flag `--pages-per-batch`.
   - **Proof:** Benchmark recorded in `docs/perf_notes.md` showing at least 30% reduction in wall-clock time for 500-page PDFs.

---

## Phase 3 – Semantic Chunking
**Current role:** Splits normalized text into TTS-friendly pieces with readability and predicted-duration metadata.

### Key Assets
- `phase3-chunking/src/chunk_builder.py`
- `phase3-chunking/src/metadata.py`
- Studio UI chunk summary table

### What Works
- Configurable thresholds already solved the classical-text coherence issue (see `PHASE3_4_ANALYSIS.md`).
- Chunk metadata (Flesch, predicted duration) is reliable enough for downstream QC and scheduling.
- Pipeline merge logic uses file locks, preventing JSON corruption.

### Needs Improvement
1. **Real-time previews in the UI.**
   - **Focus:** Surface the first 2–3 chunks plus readability stats inside the Studio as soon as Phase 3 completes.
   - **Owner Artifact:** `ui/app.py` chunking tab + new API in `pipeline_common/chunk_preview.py`.
   - **Proof:** Screenshot stored in `docs/ui_gallery.md` + manual QA checklist entry.
2. **Narration hinting.**
   - **Focus:** Tag each chunk with optional hints (dialogue, quote, narrator) using punctuation heuristics or spaCy NER to guide Phase 4 voice/style presets.
   - **Owner Artifact:** `phase3-chunking/src/metadata.py` with new field; consumer logic in `phase4_tts/src/studio_state.py`.
   - **Proof:** Unit test verifying hints for dialogue-heavy sample + documentation update in `VOICE_SELECTION_GUIDE.md`.
3. **Coverage tests for multilingual titles.**
   - **Focus:** Build fixtures for Romance + logographic scripts and assert sentence boundaries stay intact.
   - **Owner Artifact:** `phase3-chunking/tests/fixtures/` + `tests/test_multilingual_chunking.py`.
   - **Proof:** CI run plus note in `VALIDATION_TESTS.md` referencing new coverage.

---

## Phase 4 – TTS Synthesis
**Current role:** Generates chunk audio via XTTS/Kokoro with two-tier validation.

### Key Assets
- `phase4_tts/src/studio_state.py` (Gradio integration + pipeline sync)
- `phase4_tts/src/tts_worker.py` (core synthesis loop)
- `phase4_tts/DROID_VOICE_GUIDE.md` (experimental FX documentation)

### What Works
- Retry wrapper handles flaky model loads and propagates validation metrics.
- Voice catalog now includes personal + experimental FX references with documentation (`phase4_tts/DROID_VOICE_GUIDE.md`).
- Pipeline entries capture MOS proxies, durations, and validation results for every chunk.

### Needs Improvement
1. **Automated tests.**
   - **Focus:** Add lightweight smoke tests that synthesize 1–2 CC0 sentences with Kokoro so refactors cannot silently break inference.
   - **Owner Artifact:** `phase4_tts/tests/test_smoke.py` using `pytest` + `pytest -m smoke` target wired into CI.
   - **Proof:** Audio sample hashed in fixtures + CI log snippet stored in `VALIDATION_TESTS.md`.
2. **Voice asset health check.**
   - **Focus:** Write a preflight (`scripts/check_voice_assets.py`) that ensures every voice in `voice_references.json` has a sample file, correct LUFS, and matching transcription snippet.
   - **Owner Artifact:** `phase4_tts/voice_references.json`, `scripts/check_voice_assets.py`, UI hook to run before jobs start.
   - **Proof:** CLI output example + Studio toast screenshot showing a failed check with actionable steps.
3. **UI error surfacing.**
   - **Focus:** When Whisper tier 2 validation fails, list chunk IDs, transcript diff, and provide an inline "Re-synthesize" button per chunk.
   - **Owner Artifact:** `ui/app.py` (Phase 4 tab) + `phase4_tts/src/validation.py`.
   - **Proof:** QA script that intentionally corrupts a chunk to trigger the workflow + GIF in `docs/ui_gallery.md`.

---

## Phase 5 – Audio Enhancement
**Current role:** Cleans, masters, and concatenates per-chunk WAVs into polished MP3 chapters.

### Key Assets
- `phase5_enhancement/src/mastering.py`
- Preset YAML files under `phase5_enhancement/config/`
- `phase5_enhancement/scripts/render_album.py`

### What Works
- Comprehensive helper stack (noise reduction, LUFS normalization, metadata embedding) already mirrors pro mastering.
- Resource monitor prevents RAM thrash on large concatenations.
- Subtitle-friendly exports live beside mastered audio for easy sync.

### Needs Improvement
1. **Adaptive presets.**
   - **Focus:** Introduce preset bundles (dialogue, lecture, ASMR) surfaced in the UI with a tooltip explaining target LUFS, EQ, and dynamics.
   - **Owner Artifact:** `phase5_enhancement/config/presets/` + `ui/app.py` drop-down.
   - **Proof:** Listening notes captured in `docs/personal_listening_log.md` referencing each preset.
2. **Silence trimming QA.**
   - **Focus:** When silence removal cuts segments, log timestamps/durations to `artifacts/audio/qc/silence_log.json` so reviewers know where pacing changed.
   - **Owner Artifact:** `phase5_enhancement/src/silence.py` + new `--emit-qc-log` flag.
   - **Proof:** Sample log + test verifying entries when synthetic audio includes known pauses.
3. **Mobile-friendly exports.**
   - **Focus:** Provide AAC/Opus exports with preserved metadata and optional 48 kbps target for long lectures.
   - **Owner Artifact:** `phase5_enhancement/scripts/render_album.py` + CLI flag `--mobile-preset`.
   - **Proof:** Size comparison table stored in `docs/perf_notes.md`.

---

## Phase 5.5 – Subtitles (Optional)
**Current role:** Generates Whisper transcripts + VTT/SRT for personal reference.

### Key Assets
- `phase5_enhancement/src/subtitles.py`
- Whisper config files in `phase5_enhancement/config/subtitles.yml`
- UI toggle + runtime estimator

### What Works
- Leverages CPU-only `faster-whisper`, so it stays aligned with the private rig constraints.
- Writes WER + drift metrics back to `pipeline.json` for QC.
- Integrates with FFmpeg helper for MP4 renders.

### Needs Improvement
1. **Chunk-level retry logic.**
   - **Focus:** Implement per-chunk retries with capped attempts so a single failure doesn’t abort the run.
   - **Owner Artifact:** `phase5_enhancement/src/subtitles.py` + queue helper in `pipeline_common/retry.py`.
   - **Proof:** Unit test simulating a transient Whisper failure that succeeds on retry.
2. **Glossary support.**
   - **Focus:** Accept a per-title glossary (JSON/CSV) that hints proper nouns to Whisper via the token bias API.
   - **Owner Artifact:** `phase5_enhancement/config/glossary/` + UI file uploader.
   - **Proof:** Before/after WER comparison stored in `docs/personal_listening_log.md` entry.
3. **UI toggles.**
   - **Focus:** Estimate runtime + disk impact when the subtitle toggle is flipped, using historical averages from `pipeline.json`.
   - **Owner Artifact:** `ui/app.py` (Phase 5.5 section) + helper `pipeline_common/subtitle_estimator.py`.
   - **Proof:** Screenshot showing the estimates + manual QA note.

---

## Phase 6 – Orchestration (Advanced)
**Current role:** CLI orchestrator that sequences Phases 1–5 with resume support—mostly superseded by the Studio UI but still valuable for debugging.

### Key Assets
- `phase6_orchestrator/src/main.py`
- CLI flags documented in `phase6_orchestrator/README.md`
- UI integration hooks inside `ui/app.py`

### What Works
- Rich-based dashboards offer clear visibility when running headless.
- Retry + dependency bootstrapping automatically handles Poetry vs Conda boundaries.
- Coverage tests confirm no content skips between phases.

### Needs Improvement
1. **UI integration audit.**
   - **Focus:** Document and codify which CLI flags the Gradio UI toggles so we can detect drift as soon as a new flag ships.
   - **Owner Artifact:** `phase6_orchestrator/README.md` (mapping table) + automated assertion in `ui/tests/test_phase6_contract.py`.
   - **Proof:** Failing test when UI and CLI options diverge.
2. **Manifest-aware single runs.**
   - **Focus:** Accept a manifest row (CSV/JSON) and run it through Phase 6 without invoking the full Phase 7 batch path.
   - **Owner Artifact:** `phase6_orchestrator/src/main.py` + CLI flag `--manifest-row <id>`.
   - **Proof:** Example command + log excerpt stored in `docs/PHASE_EVALUATION_2025-11.md` appendix.
3. **Telemetry export.**
   - **Focus:** Emit structured JSON logs summarizing duration, retries, and failures for ingestion into the personal listening log.
   - **Owner Artifact:** `phase6_orchestrator/src/telemetry.py` + `docs/personal_listening_log.md` instructions.
   - **Proof:** Sample telemetry blob checked into `artifacts/samples/phase6_telemetry.json`.

---

## Phase 7 – Batch Processing (Advanced)
**Current role:** Concurrent executor for manifest-driven runs when experimenting with multiple titles.

### Key Assets
- `phase7_batch/src/main.py`
- `manifests/*.csv`
- Batch QC scripts under `phase7_batch/scripts/`

### What Works
- Resource throttling keeps CPU usage within user-defined budgets.
- Rich summaries and `BatchMetadata` capture success/failure per file.
- Environment verification stops runs early when a phase virtualenv is missing.

### Needs Improvement
1. **Studio parity.**
   - **Focus:** Provide at least a dry-run manifest upload + status view inside the Studio so power users do not have to drop to CLI immediately.
   - **Owner Artifact:** `ui/app.py` (advanced tab) + `phase7_batch/api.py` (new helper for manifest validation).
   - **Proof:** Screenshot of the new panel + user notes after a trial dry-run.
2. **Artifact cleanup policies.**
   - **Focus:** Implement automatic pruning of temporary WAVs/intermediate files when a manifest row finishes successfully.
   - **Owner Artifact:** `phase7_batch/src/cleanup.py` with hooks in the worker pool.
   - **Proof:** Disk-usage metrics before/after recorded in `docs/perf_notes.md`.
3. **Parallelism advisor.**
   - **Focus:** Detect CPU cores + disk throughput, then recommend a worker count or auto-tune when `--workers` is omitted.
   - **Owner Artifact:** `phase7_batch/src/config.py` + `scripts/probe_system.py`.
   - **Proof:** CLI output sample + manual validation on desktop + laptop configs.

---

## Next Steps
1. Pick one or two high-impact improvements from the sections above.
2. Translate them into actionable issues/tasks (include file paths and success criteria).
3. Update the relevant README/guide when you complete an improvement so future evaluations show progress.
4. Re-run this evaluation quarterly to keep the private-study pipeline healthy.
