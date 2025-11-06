# Phase 4 Validation - Quick Reference Card

## Installation (One-Time Setup)

```bash
cd phase4_tts
poetry add librosa numpy openai-whisper
```

## Basic Usage

```bash
# With validation (recommended)
poetry run python src/main.py \
  --file_id "The_Meditations" \
  --json_path "../pipeline.json"

# Skip validation (not recommended)
poetry run python src/main.py \
  --file_id "The_Meditations" \
  --json_path "../pipeline.json" \
  --skip_validation
```

## What It Does

✅ **Tier 1** (every chunk, ~2s): Duration, silence, amplitude, error patterns  
✅ **Tier 2** (sampled, ~60s): Whisper transcription + WER

**Overhead**: ~1.5 hours on 2.25-day runtime (2.8%)

## Expected Output

```
✅ Tier 1 validation passed
✅ Tier 2 validation passed (WER: 3.2%)
Chunk: ✅ SUCCESS, MOS: 4.12
```

## Configuration Quick Tweaks

**Speed Optimization** (`validation_config.yaml`):
```yaml
tier2:
  whisper_model: "tiny"         # Faster
  whisper_sample_rate: 0.02     # 2% sample
```

**Quality Optimization** (`validation_config.yaml`):
```yaml
tier2:
  whisper_model: "small"        # More accurate
  whisper_sample_rate: 0.10     # 10% sample
  max_wer: 0.05                 # Stricter
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Whisper not installed" | `poetry add openai-whisper` |
| Too many duration failures | Increase `duration_tolerance_sec: 10.0` |
| Tier 2 too slow | Use `whisper_model: "tiny"` or reduce `whisper_sample_rate` |
| False WER positives | Increase `max_wer: 0.15` or use larger model |

## Check Results

```bash
# View failed chunks
jq '.phase4.files.The_Meditations | to_entries[] | select(.value.metrics.validation.validation_passed == false)' pipeline.json

# Count failures
jq '[.phase4.files.The_Meditations | to_entries[] | select(.value.metrics.validation.tier1.passed == false)] | length' pipeline.json
```

## Re-synthesize Failed Chunk

```bash
poetry run python src/main.py \
  --file_id "The_Meditations" \
  --chunk_id 50 \
  --json_path "../pipeline.json"
```

---

**Full Documentation**: See `PHASE4_VALIDATION_GUIDE.md`
