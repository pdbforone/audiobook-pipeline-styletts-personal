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

## Documentation Reality Checks
- `README_EXCELLENCE.md` and `PROJECT_OVERVIEW.md` reflect the current CPU-only, XTTS + Kokoro setup and personal-use scope.
- `STRUCTURE_ENHANCEMENT_README.md` now documents the correct personal repo paths for Phase 2/3 tests.
- `MASTER_GUIDE.md` references video tooling in `audiobook-pipeline-chatterbox`; keep contextual but note it is a sibling repo, not this pipeline.
