# codex_memory.md - Long-Term Memory for TTS Pipeline Agent

## Project Scope
- Personal-use, CPU-only audiobook TTS pipeline.
- Target hardware: AMD Ryzen 5 5500U (6c/12t @ 2.1 GHz), 16 GB RAM (~12 GB usable), integrated Radeon Graphics (not for ML inference), Windows 11 x64, 466 GB SSD.

## License Context
- Non-commercial, research-only, and academic models are allowed.
- Agent must warn but not restrict non-commercial tools.
- Provide commercial-safe alternatives only when relevant.

## Agent Personality & Design Philosophy
- Thinks like a craftsman, designer-engineer, and research scientist.
- Produces elegant, minimal, inevitable solutions.
- Uses architecture-first thinking ("Plan Like Da Vinci").
- Treats tests and documentation as part of the craft.
- Always iterates toward clarity and simplicity.

## Agent Modes
- Analysis Mode: deep understanding of pipeline stages.
- Research Mode: automatic search + double verification.
- Improvement Mode: minimal -> moderate -> major upgrades.
- Auto-Pilot Mode: continuous optimization when enabled.

## Internal Agents
- Pipeline Architect
- TTS Model Specialist
- Audio Engineer
- QA/WER/MOS Analyst
- Research Agent

## Pipeline Focus
- Chunking & segmentation
- Text normalization
- TTS inference (CPU-only models)
- Denoising & mastering
- Concatenation (gapless, crossfade)
- Accuracy metrics (WER, MOS proxies, similarity)
- Chapter/section detection
- Workflow automation

## Permanent Rules
- No GPU assumptions.
- No hallucinated tools/models.
- Every claim must be verified via research.
- Solutions must integrate smoothly with the whole pipeline.
- All code must be modular, clean, maintainable, well-named.
- Respect CPU performance limits.
- Always provide alternatives, fallbacks, and tradeoffs.

## Current Pipeline Reality (Nov 2025)
- Repo: `C:\Users\myson\Pipeline\audiobook-pipeline-personal\audiobook-pipeline-styletts-personal`; state file `pipeline.json` in root with backups under `.pipeline/backups/`.
- UI: `ui/app.py` (Gradio); phases still runnable via per-phase CLIs; Phase 4 has engine runner and env setup scripts.
- TTS engines: XTTS v2 (primary) and Kokoro-onnx (CPU fallback) under `phase4_tts/engines/`; F5-TTS references in some docs are historical.
- Phase 2/3 structure-aware flow: structure detector lives in `phase2-extraction/src/phase2_extraction/structure_detector.py`; chunking uses `phase3-chunking/src/phase3_chunking/structure_chunking.py` with ~5k word caps.
- Phase 5 mastering presets and subtitle tooling live in `phase5_enhancement/`; Phase 5.5 (subtitles) is optional.
- Voice assets reside in `phase4_tts/voice_references/`; engine envs are per-engine via `phase4_tts/.engine_envs/`.
- Recent upgrades (Nov 2025):
  - Phase 3 sentence detection: spaCy primary with pySBD fallback for abbreviation/bullet-heavy text. Dependency: `pysbd`.
  - Phase 4 text prep: optional g2p_en number/abbrev normalization toggled in `config.yaml` (`enable_g2p`, `normalize_numbers`, `custom_pronunciations`). Dependency: `g2p-en`. Piper intentionally excluded until a vetted adult audiobook voice is available.
  - Phase 5 enhancement: added optional RNNoise denoise and Silero VAD speech coverage/trim toggles (`enable_rnnoise`, `enable_silero_vad`, `silero_vad_threshold`, `trim_silence_with_vad`). Dependencies: `rnnoise`, `silero-vad` (+ torch/torchaudio). DeepFilterNet and noisereduce remain supported. Metadata now records speech ratios.
  - Phase 5.5 subtitles: optional aeneas forced alignment when reference text is provided (`--use-aeneas` / `use_aeneas_alignment`).
  - Phase 4 runtime guard: optional CPU usage-based downscale (`--cpu_guard`, auto-enabled by `--cpu_safe`) using psutil; reduces workers on sustained high CPU, never below 1; warns and skips if psutil missing.
  - Phase docs: Phase 1 (`phase1-validation/README.md`), Phase 2 (`phase2-extraction/README.md`), Phase 3 (`phase3-chunking/README.md`), Phase 4 (`phase4_tts/README.md`), Phase 5 (`phase5_enhancement/README.md`), Phase 6 (`phase6_orchestrator/README.md`), Phase 7 (`phase7_batch/README.md`), and consolidated map `PHASE_DOCS.md` (phase entrypoints and doc pointers).
  - Phase 4: added `--prefer_kokoro` flag to default to Kokoro for throughput when engine was xtts.
  - Phase 5: RNNoise now enabled by default; optional pydub-based compression+limiter added (threshold -24 dBFS, ratio 4:1, ceiling -1 dBFS) applied after denoise and before LUFS normalize.

## Operational Heuristics (Dec 2025)
- Preferred XTTS v2 CPU chunk length 12–18 s using sentence/semantic boundaries; split long sentences at semicolons/emdashes. Current tuning: min_chunk_words=30, max_chunk_words=75; char limits min=420, soft=780, hard=950, emergency=1250; duration model 2700 chars/min & 210 wpm; max_duration 20 s (soft target 18 s).
- Concatenation: default 50 ms crossfade (clamped to ≤100 ms) with silence guard—skip crossfade when leading silence ≥200 ms to avoid word swallow. CLI/config overrides: `crossfade_max_sec`, `crossfade_silence_guard_sec`, `crossfade_enable_silence_guard` exposed in Phase 5; seam pop detector warns on discontinuities.
- CPU guard: cap TTS workers to <=3 on Ryzen 5 5500U to prevent throttling; monitor wall-clock RT per chunk.
- Kokoro-onnx CPU fallback: ~1.2–1.5x RT for ≤10 s chunks; switch when XTTS RT per chunk exceeds ~4x or risks OOM. Phase4 config now exposes enable_latency_fallback + slow_rt_threshold (default 4.0).
- Latency monitor: log wall vs audio duration; if RT >4x and Kokoro available, attempt single Kokoro re-render and keep if faster (configurable).
- Auto engine heuristic: Phase 4 `--auto_engine` estimates total audio (chars_per_minute=2700, rt_xtts≈3.2, rt_kokoro≈1.3) and selects Kokoro when XTTS walltime is >30% slower.
- Defaults: enable Silero VAD-driven trim; keep RNNoise opt-in to avoid over-softening narration.
- Mastering (narration): target -18 to -16 LUFS with soft-knee limiter; avoid stacking heavy denoise + limiter unless noisy input demands it.
- Notification assets: Droid beeps generated locally at `assets/notifications/droid_success.wav` and `assets/notifications/droid_alert.wav` for UI/alerts (pure numpy/soundfile, CPU-safe).
- Astromech notifications: `pipeline_common.astromech_notify` with Phase 3/4/5 CLI flag `--play_notification` to trigger success/alert beeps (winsound/sounddevice fallback).
- Phase 4 telemetry: pipeline.json stores per-chunk `rt_factor`, `audio_seconds`, `latency_fallback_used`; file-level aggregates now include `avg_rt_factor`, `rt_p50`, `rt_p90`, `rt_p99`, `fallback_rate`, `latency_fallback_chunks`, and `advisory` (advisories require successful chunks).
- Phase 4 budget + safeguards: `--cpu_safe` keeps workers≤3, forces latency fallback, tightens RT threshold (~3.5), enables auto-engine. `--rt_budget_hours` estimates wall time; warns on overruns, can bias to Kokoro in cpu_safe, and warns if even best-case RT exceeds budget. Adaptive worker scaling (cpu_safe) reduces workers after two slow chunks. Chunk softening remains TODO to avoid chunk ID drift.

## UI Updates (Jan 2026)
- Gradio Status tab now includes paged Phase 4 chunk summary (avoids loading full pipeline.json) and log-tail viewer (xtts_chunk.log, orchestrator.log, phase5 enhancement log).
- Voice add flow consolidated: `_normalize_voice_id` + `_resolve_audio_source`, validates audio type, writes `voice_references.json` with narrator/tags/notes, refreshes dropdowns.
- Helpers in `ui/app.py`: `_tail_log` for safe last-N-lines; `build_phase4_summary` for paged summaries handling mixed dict/list chunk entries.

## Documentation Reality Checks
- `README_EXCELLENCE.md` and `PROJECT_OVERVIEW.md` reflect the current CPU-only, XTTS + Kokoro setup and personal-use scope.
- `STRUCTURE_ENHANCEMENT_README.md` now documents the correct personal repo paths for Phase 2/3 tests.
- `MASTER_GUIDE.md` references video tooling in `audiobook-pipeline-chatterbox`; keep contextual but note it is a sibling repo, not this pipeline.
