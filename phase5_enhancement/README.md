# Phase 5 – Enhancement & Mastering

Post-TTS processing: denoise, trim, normalize, and master narration-ready audio.

## Key docs
- `PHASE5_GUIDE.md`, `SPRINT1_AUDIO_MASTERING.md`

## Features
- Denoise options: RNNoise (opt-in), DeepFilterNet, noisereduce.
- VAD-driven trimming: Silero VAD (`enable_silero_vad`, `silero_vad_threshold`, `trim_silence_with_vad`).
- Loudness/limiting: target -18 to -16 LUFS, soft-knee limiter.
- Crossfade controls (Phase 5 concatenation): defaults 50 ms crossfade with silence guard.
- Optional broadband compression + limiter (pydub) after denoise, before LUFS normalize (defaults on; threshold -24 dBFS, ratio 4:1, ceiling -1 dBFS).

## Config toggles (typical)
- `enable_rnnoise`: false by default to avoid over-softening.
- `enable_silero_vad`: true by default; tune threshold.
- `enable_compression`: on by default for gentle dynamic control (threshold/ratio/ceiling tunable).
- `crossfade_max_sec`, `crossfade_silence_guard_sec`, `crossfade_enable_silence_guard`.

## Outputs
- Enhanced WAVs under `phase5_enhancement/processed/` and final audiobook; metadata appended to `pipeline.json` (speech ratios, durations, seam warnings when available).
