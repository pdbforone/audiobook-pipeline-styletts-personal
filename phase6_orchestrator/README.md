# Phase 6 – Orchestration

Coordinates phase execution and notification flow. Drives per-phase CLIs, handles paths/configs, and manages status updates into `pipeline.json`.

## Role
- Sequence phases (1→5) for single-book runs.
- Passes common flags (cpu_safe/auto_engine where applicable), JSON paths, and file IDs.
- Hooks notifications (astromech beeps) and logging.

## Key files
- Package: `phase6_orchestrator/` (see orchestrator modules in this folder).
- Schema reference: `PIPELINE_JSON_SCHEMA.md`
- Status helpers: `check_pipeline_phases.py`, `check_pipeline_status.py` (root utilities).

## Notes
- Batch mode (Phase 7) still forces single-worker TTS; Phase 6 should avoid over-provisioning to prevent thermal throttling on Ryzen 5 5500U.
- Integrate CPU/RAM guard decisions upstream when using `--cpu_safe` in Phase 4.
