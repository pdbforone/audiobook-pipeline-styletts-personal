# Policy Engine Observer & Advisor (v3)

`PolicyEngine` now runs with the **v3 telemetry stack**. Every orchestrated audiobook build emits structured JSON lines to:

```
.pipeline/policy_logs/YYYYMMDD.log
```

Each entry contains the historical v2 payload plus:

| Field | Description |
| --- | --- |
| `policy_version` | Version of the logger (`3.0` for this release) |
| `run_id` | Stable identifier for the current orchestrator invocation |
| `sequence` | Monotonic counter so downstream analytics can reconstruct ordering |
| `system_load`, `cpu_percent`, `memory_percent` | Host telemetry (best effort via `psutil`) |

This stream is append-only JSONL, so it can be tailed, parsed, or shipped to offline analysis without extra transforms.

## Enhanced Telemetry

The analytics layer (`policy_engine/advisor.py`) ingests all log files and produces a rolling telemetry snapshot whenever `PolicyAdvisor.advise(ctx)` executes. The snapshot captures:

- **Phase duration analysis** – averages, p50, p95, min/max, and recent rolling windows per phase, plus bottleneck detection.
- **Real-time factor (RTF) statistics** – global and per-engine averages, p90/p99, and rolling windows to catch regressions.
- **Engine fallback rates** – overall and per-engine latency fallback usage with chunk counts.
- **Hallucination counters** – lifetime totals and the most recent flagged events for Phase 4.
- **Existing health metrics** – chunk error rates, enhancement failure rates, and engine reliability are still tracked.

The telemetry lives under `advice["telemetry"]` so the orchestrator, dashboard, or external tools can display it without rescanning the logs.

## Soft Suggestions

`PolicyEngine.advise(ctx)` remains non-blocking: it never mutates the pipeline. The return payload now includes:

- Legacy recommendation keys (`chunk_size`, `engine`, `retry_policy`, `voice_variant`) for drop-in compatibility.
- A normalized `suggestions` list where every suggestion or heuristic alert includes a `type`, `confidence`, and `payload`.

Example entry:

```json
{
  "type": "rt_factor_alert",
  "phase": "phase4",
  "confidence": 0.40,
  "payload": {
    "message": "Recent average RT factor 4.20x exceeds 4.0x target.",
    "rt_factor": 4.2
  }
}
```

These “soft suggestions” surface context such as rolling phase3 runtimes, fallback spikes, or hallucination bursts so humans (or the forthcoming tuning automation) can decide whether to act.

## CLI Reporting

Generate a snapshot report at any time:

```bash
python -m policy_engine report
```

The report (written to `policy_reports/summary.md` by default) now includes:

- Phase duration summaries and failure rates
- Engine reliability
- Real-time factor statistics
- Engine fallback usage
- Hallucination counters

This keeps a human-readable audit trail alongside the raw JSONL logs.

## Human-Approved Tuning CLI

Use the tuning CLI to capture policy suggestions that a human has reviewed:

```bash
python -m orchestrator.tuning_cli tune --pipeline pipeline.json
```

The CLI inspects the latest policy telemetry, presents each proposed override (chunk sizing, engine preference, retry policy, etc.), and writes any approved changes to:

```
.pipeline/tuning_overrides.json
```

These overrides are treated as a source-of-truth for later Adaptive/Self-Driving modes—only entries recorded in this file are considered “human approved.”

## Adaptive Mode (Ephemeral Overrides)

When `PolicyEngine` runs in adaptive mode, it automatically ingests `.pipeline/tuning_overrides.json`, merges the human-approved entries with the latest telemetry, and applies the resulting overrides **only for the current run**. Key behaviors:

- Phase 3 chunk sizes are scaled via a temporary config file, capped at ±20% from the baseline.
- Phase 4 can switch engines or voices when the stored confidence is ≥ 0.70 and at least three successful runs have elapsed since the last voice change.
- Retry budgets are applied per phase according to the override file.
- A minimum real-time factor target of 1.0 is enforced for any throughput overrides.

After each run, the engine writes a `runtime_state` entry back into `tuning_overrides.json` (last run metadata, voice-change cooldown counters, etc.) so future runs can respect the safety limits while staying fully offline and non-destructive.

## Self-Driving Mode (Reinforcement Heuristics)

Self-driving mode extends Adaptive Mode with a deterministic reinforcement loop:

- `PolicyAdvisor` emits per-run rewards, rolling skill weights, and safety signals (derived from RTF, fallback rates, hallucination counters, and run outcomes).
- `PolicyEngine` consumes these signals to auto-adjust `.pipeline/tuning_overrides.json`: gently nudge Phase 3 chunk deltas, promote higher-reliability engines, or revert overrides when the reward drops.
- Chunk deltas move in ≤2% steps per run and stay inside the ±20% safety envelope; engine switches still require ≥0.70 confidence; voice overrides are cleared whenever hallucinations resurface.

All logic remains local and deterministic—the controller only edits the overrides file, keeping phase code untouched while continuously nudging the pipeline toward healthier telemetry.

## Dashboard & Weekly Reporter

- Launch the optional **Gradio dashboard** with `python -m dashboard.gradio_app`. It displays the current policy metrics, reuseable charts from `dashboard_output/charts/`, overrides, and raw log excerpts. The UI is read-only and has no effect on pipeline execution.
- Generate an offline weekly snapshot with `python -m dashboard.report`. The command emits `policy_reports/weekly.md` and companion charts under `policy_reports/charts/`, using Matplotlib only.

Both tools rely exclusively on the existing policy logs and override file, so they can run without network access or live pipeline executions.

## G6 Verification Mode

G6 verification is a lightweight confidence pass that replays three “micro-books” through **Phases 1‑4 only** while the self-driving controller is enabled. Each run should:

- Reset `.pipeline/tuning_overrides.json` to a neutral state (`chunk_size`, `engine_prefs`, `voice_stability`) before the first pass, then allow the controller to repopulate `history`, `overrides`, and `runtime_state` organically.
- Produce a monotonic override trajectory—`chunk_size.delta_percent` typically nudges a few tenths of a percent per run, voice streak increments with every clean pass, and engine preferences remain stable unless latency spikes appear.
- Maintain RTF near the controller’s steady-state (≈2.8× for XTTS on CPU). Improvements are welcome, but regression triggers an advisory line in the policy telemetry.
- Emit advisory suggestions after every run (e.g., chunk-size heuristics, retry policy hints). Verification scripts should capture these lines to prove the advisor remained active.
- Leave the pipeline state schema-valid: `PipelineState` must read/write cleanly, policy logs accumulate under `.pipeline/policy_logs/`, and each mini-book produces Phase 4 audio artifacts.

Running `python phase_g6_verify.py` (or `make g6-verify`) performs the entire procedure, records unified diffs under `g6_verify_diffs/`, and prints the RTF/override trajectories so humans can confirm the self-tuning loop is still healthy without touching Phase 5.
