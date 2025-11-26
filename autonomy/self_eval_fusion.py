"""Phase Q: fuse cross-phase signals for self-evaluation (read-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, Any

from autonomy.self_eval_kernel import SelfEvalKernel, SelfEvalInput

try:
    from pipeline_common.state_manager import PipelineState  # type: ignore
except Exception:  # noqa: BLE001
    PipelineState = None  # type: ignore


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def fuse_signals_for_self_eval(
    run_state: "PipelineState",
    run_id: str,
    base_dir: Optional[Path] = None,
) -> SelfEvalInput:
    base_dir = base_dir or Path(".pipeline")
    run_summary = _load_json(base_dir / "verification_pipeline.json") or {}
    evaluator_summary = _load_json(base_dir / "policy_runtime" / "evaluator" / f"{run_id}.json") or {}
    diagnostics_summary = _load_json(base_dir / "diagnostics" / f"{run_id}.json") or {}

    memory_dir = base_dir / "memory"
    stability_dir = base_dir / "stability_profiles"
    rewards_dir = base_dir / "rewards"
    autonomy_dir = base_dir / "autonomy_journal"
    metadata_dir = base_dir / "metadata"

    def _latest_json(directory: Path) -> Dict[str, Any]:
        if not directory.exists():
            return {}
        candidates = sorted(
            directory.glob(f"{run_id}.json")
        )
        if not candidates:
            candidates = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return {}
        return _load_json(candidates[0]) or {}

    memory_profile = _latest_json(memory_dir)
    stability_profile = _latest_json(stability_dir)

    reward_summary = {}
    if rewards_dir.exists():
        for p in rewards_dir.glob("*.json"):
            data = _load_json(p) or {}
            if run_id in json.dumps(data):
                reward_summary.setdefault("entries", []).append(data)

    autonomy_journal = _load_json(autonomy_dir / f"{run_id}.json") or {}
    metadata_summary = _load_json(metadata_dir / f"{run_id}.json") or {}

    kernel = SelfEvalKernel()
    return kernel.build_input(
        run_summary=run_summary,
        evaluator_summary=evaluator_summary,
        diagnostics_summary=diagnostics_summary,
        memory_profile=memory_profile,
        stability_profile=stability_profile,
        reward_summary=reward_summary,
        autonomy_journal=autonomy_journal,
        metadata_summary=metadata_summary,
    )
