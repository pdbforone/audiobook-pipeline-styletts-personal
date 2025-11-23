from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

from prefect import flow, task

from phase6_orchestrator.orchestrator import run_pipeline
from pipeline_common.policy_engine import PolicyEngine


def _load_policy_config(config_path: Optional[Path]) -> Dict[str, Any]:
    if not config_path:
        return {}
    try:
        with config_path.open("rb") as handle:
            data = tomllib.load(handle) or {}
        return data.get("policy_engine") or data
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


@task(name="load-policy-engine")
def load_policy_engine(config_path: Optional[str] = None) -> PolicyEngine:
    """Instantiate the PolicyEngine using optional config data."""
    config_file = Path(config_path) if config_path else None
    config = _load_policy_config(config_file)
    logging_enabled = bool(config.get("logging", True))
    learning_mode = str(config.get("learning_mode", "observe"))
    return PolicyEngine(
        logging_enabled=logging_enabled, learning_mode=learning_mode
    )


@task(name="run-single-pipeline")
def run_single_pipeline(
    pipeline_path: str,
    policy_engine: Optional[PolicyEngine] = None,
    run_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a single pipeline run via the existing orchestrator."""
    kwargs = dict(run_kwargs or {})
    file_path = Path(pipeline_path)
    kwargs.setdefault("policy_engine", policy_engine)
    result = run_pipeline(file_path=file_path, **kwargs)
    return {
        "pipeline_path": str(file_path),
        "result": result,
    }


@flow(name="tts-audiobook-pipeline", persist_result=True)
def tts_pipeline_flow(
    pipeline_path: str,
    use_policy_engine: bool = True,
    policy_config_path: Optional[str] = None,
    run_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefect flow that wraps a single orchestrator invocation."""
    policy_engine = None
    if use_policy_engine:
        policy_engine = load_policy_engine.submit(policy_config_path).result()

    run_future = run_single_pipeline.submit(
        pipeline_path=pipeline_path,
        policy_engine=policy_engine,
        run_kwargs=run_kwargs or {},
    )
    return run_future.result()


@flow(name="tts-audiobook-batch", persist_result=True)
def tts_pipeline_batch_flow(
    pipeline_paths: List[str],
    use_policy_engine: bool = True,
    policy_config_path: Optional[str] = None,
    run_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefect flow that processes multiple pipelines sequentially."""
    policy_engine = None
    if use_policy_engine:
        policy_engine = load_policy_engine.submit(policy_config_path).result()

    summaries: List[Dict[str, Any]] = []
    for path in pipeline_paths:
        summary = run_single_pipeline.submit(
            pipeline_path=path,
            policy_engine=policy_engine,
            run_kwargs=run_kwargs or {},
        ).result()
        summaries.append(summary)

    return {"runs": summaries}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Prefect orchestration entrypoint"
    )
    parser.add_argument("pipeline", help="Path to the input book file")
    parser.add_argument(
        "--no-policy",
        action="store_true",
        help="Disable PolicyEngine for this invocation",
    )
    parser.add_argument(
        "--policy-config",
        type=str,
        default=None,
        help="Optional policy configuration TOML file",
    )
    parser.add_argument(
        "--phases",
        type=int,
        nargs="+",
        default=None,
        help="Optional list of phases to run (forwarded to run_pipeline)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume for this run",
    )

    args = parser.parse_args()
    result = tts_pipeline_flow(
        pipeline_path=args.pipeline,
        use_policy_engine=not args.no_policy,
        policy_config_path=args.policy_config,
        run_kwargs={
            "phases": args.phases,
            "no_resume": args.no_resume,
        },
    )
    print(result)
