# Phase 4 – TTS (XTTS / Kokoro multi-engine)

Multi-engine TTS with CPU guardrails, auto-engine selection, latency fallback, and telemetry into `pipeline.json`.

## Key entrypoints
- CLI: `src/main_multi_engine.py` (backward-compatible `src/main.py` delegates here)
- Config: `config.yaml` (RT thresholds, engine estimates, g2p flags, audio dir)
- Guides: `PHASE4_VALIDATION_GUIDE.md`, `VOICE_SELECTION_GUIDE.md`, `DROID_VOICE_GUIDE.md`, `VOICE_*` docs

## Defaults (Ryzen 5 5500U)
- Worker cap: 3 (capped regardless of request).
- Auto-engine: heuristic chooses Kokoro if XTTS throughput would be much slower.
- Latency fallback: switch to Kokoro when RT factor exceeds threshold (default 4.0; tighter under `--cpu_safe`).
- CPU guard (optional): `--cpu_guard` (auto with `--cpu_safe`) uses psutil to downscale workers on sustained high CPU; never below 1.
- Chunk resume: `--resume` skips existing wavs.

## Telemetry
- Per-chunk: `rt_factor`, `audio_duration`, `engine_used`, `latency_fallback_used`.
- Aggregates: `avg_rt_factor`, `rt_p50/p90/p99`, `fallback_rate`, `duration_sec`.

## CLI examples
```
python src/main_multi_engine.py --file_id MyBook --json_path ../pipeline.json --workers 3
python src/main_multi_engine.py --file_id MyBook --json_path ../pipeline.json --cpu_safe --auto_engine
python src/main_multi_engine.py --file_id MyBook --json_path ../pipeline.json --resume --disable_fallback
# Prefer Kokoro for throughput
python src/main_multi_engine.py --file_id MyBook --json_path ../pipeline.json --prefer_kokoro
# Profiles (safe | balanced | max_quality)
python src/main_multi_engine.py --file_id MyBook --json_path ../pipeline.json --profile safe
```

## Voice assets
- Stored under `voice_references/`; see guides for selection/override.
