# Running the Pipeline with Prefect

The repository now exposes Prefect-based flows that wrap the existing Phase 6 orchestrator and PolicyEngine without requiring Prefect Cloud.

## Requirements

- Local Prefect installation (see `.prefect/config.toml` for the local profile).
- No Prefect server/agent is required; flows run in-process.

## CLI Usage

Single run:

```bash
python -m orchestration.prefect_cli run --pipeline input/test_short.txt
```

Disable the PolicyEngine if desired:

```bash
python -m orchestration.prefect_cli run --pipeline input/test_short.txt --no-policy
```

Batch run:

```bash
python -m orchestration.prefect_cli batch --pipelines input/book1.pdf input/book2.pdf
```

Results are printed to stdout as dictionaries matching the Prefect flow returns. No Prefect Cloud account or server startup is needed; everything runs locally.
