# Policy Engine Observer & Advisor

`PolicyEngine` runs in **observe** mode for every orchestrated audiobook build. The engine passively records each phase boundary and writes structured JSON lines to:

```
.pipeline/policy_logs/YYYYMMDD.log
```

Every log entry includes:

| Field | Description |
| --- | --- |
| `timestamp` | UTC timestamp (ISO 8601) when the event was recorded |
| `phase` | Canonical phase label (`phase1` … `phase7`, `phase5.5`, etc.) |
| `file_id` | Active file identifier |
| `event` | `phase_start`, `phase_end`, `phase_retry`, or `phase_failure` |
| `status` | High-level state (`starting`, `success`, `retry`, `failed`) |
| `duration_ms` | Phase runtime in milliseconds (for end/failure events) |
| `metrics` | Phase metrics snapshot from `pipeline.json` when available |
| `errors` | Phase errors captured from the canonical state or orchestrator |
| `pipeline_json` | Absolute path to the pipeline state file |
| `learning_mode` | Currently `observe` |
| `system_load`, `cpu_percent`, `memory_percent` | Host telemetry pulled via `psutil` (if installed) |

The orchestrator produces start/end/failure snapshots for every phase, including Phase 5.5 (subtitles). Retries also generate their own `phase_retry` records with the attempt number embedded in the context. These logs are append-only, one JSON object per line (`.jsonl`), making them easy to ingest into external monitoring or policy-training pipelines.

## v2 Advisor Mode

The v2 **advisor** consumes the accumulated logs and produces non-binding recommendations for future runs. The analytics live in `policy_engine/advisor.py` and include:

- Rolling phase-duration averages (spotting oversized or undersized Phase 3 chunks)
- Chunk error frequency for Phase 3 anomaly detection
- Engine reliability metrics for Phase 4 (per TTS engine)
- Hallucination indicators scraped from Phase 4 error messages
- Enhancement failure rate for Phase 5

Recommendations are surfaced via:

| API | Purpose |
| --- | --- |
| `recommend_chunk_size(file_id)` | Suggests larger/smaller chunk sizes based on recent Phase 3 runtimes |
| `recommend_engine(file_id)` | Recommends the most reliable TTS engine |
| `recommend_retry_policy(phase)` | Adjusts retry budgets when failure rates drift |
| `recommend_voice_variant(file_id)` | Flags file IDs that repeatedly fail Phase 4 so alternate voices can be tested |

`PolicyEngine.advise(ctx)` uses these helpers and logs the suggestions (without enforcing them) so operators can review the proposed changes directly in the orchestrator output.

## CLI Reporting

Generate a high-level policy report at any time:

```bash
python -m policy_engine report
```

This command aggregates recent log files and writes `policy_reports/summary.md`, capturing phase durations, failure rates, and engine reliability snapshots for quick review.
