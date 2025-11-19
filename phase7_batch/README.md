# Phase 7 – Batch Runner

Wraps per-book orchestration for batch processing. Designed to be conservative on CPU-only hardware.

## Behavior
- Processes books serially or with minimal concurrency; Phase 4 workers remain capped (typically 1 in batch mode) to avoid thermal throttling.
- Respects per-book reuse (hash checks) when earlier phases succeeded unless overridden.
- Triggers notifications/logging per book and aggregates a batch summary.

## Key files
- Scripts in `phase7_batch/` and root batch helpers (e.g., `BATCH_SUMMARY.md` for reporting).
- For phase schemas see `PIPELINE_JSON_SCHEMA.md`.

## Tips
- Use `--cpu_safe` in downstream phases during batch to protect the Ryzen 5 5500U.
- Keep batch sizes modest if temps climb; monitor with existing log tailing in the UI.
