# Environment Layout

This repository now uses a split-environment strategy:

- **Phase 1–5 stacks:** keep their historical, isolated environments. Do **not**
  modify their virtual environments or interpreter versions unless a dedicated
  task explicitly calls for it.
- **Shared/interactive layers (pipeline_common/, phase6_orchestrator/,
  phase7_batch/, ui/):** standardised on Windows Python **3.11**
  (`C:\Program Files\Python311\python.exe`). Each of these directories has its
  own `.venv` plus an `init_venv.ps1` bootstrapper that:
    - recreates the virtual environment with Python 3.11
    - installs dependencies (editable mode for local sources)
    - prints a success message on completion

## Component Summary

| Component              | Python Version     | Bootstrapper            | Notes |
|------------------------|--------------------|-------------------------|-------|
| `pipeline_common/`     | 3.11 (local `.venv`) | `pipeline_common\init_venv.ps1` | Provides schema + PipelineState utilities shared across the stack. |
| `phase6_orchestrator/` | 3.11 (local `.venv`) | `phase6_orchestrator\init_venv.ps1` | Poetry-managed; coordinates single-file orchestration on the same interpreter as UI + Phase 7. |
| `phase7_batch/`        | 3.11 (local `.venv`) | `phase7_batch\init_venv.ps1` | Installs runtime + dev deps (`trio`, `psutil`, `PyYAML`, `rich`, pytest stack). Tests run via `PYTHONPATH=phase7_batch/src pytest phase7_batch/tests -q`. |
| `ui/`                  | 3.11 (local `.venv`) | `ui\init_venv.ps1` | Gradio UI, depends on `pipeline_common` (installed locally) and orchestrator APIs. |

All new shared code should target these Python 3.11 environments. Do not reuse
the legacy interpreters from Phases 1–5 for shared modules or tooling.
