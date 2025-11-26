"""Phase P: evidence ingestion (read-only, opt-in)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

try:
    from pipeline_common import PipelineState  # type: ignore
except Exception:  # pragma: no cover - import guard
    PipelineState = None  # type: ignore


def _safe_read_state(run_state: Any) -> Dict[str, Any]:
    if PipelineState and isinstance(run_state, PipelineState):
        try:
            return run_state.read(validate=False)
        except Exception:
            return {}
    if isinstance(run_state, dict):
        return run_state
    return {}


def collect_evidence(run_state: Any, logs: List[Path]) -> Dict[str, Any]:
    """
    Collect normalized evidence from run state and log paths.
    """
    state = _safe_read_state(run_state)
    ts = datetime.utcnow().isoformat()
    evidence = {
        "timestamp": ts,
        "phases": {},
        "logs": [],
        "chunks": [],
        "errors": [],
        "meta": {},
    }

    for phase_key, data in state.items():
        if not phase_key.startswith("phase"):
            continue
        if isinstance(data, dict):
            evidence["phases"][phase_key] = {
                "status": data.get("status"),
                "metrics": data.get("metrics"),
                "timestamps": data.get("timestamps"),
            }
            if "errors" in data and isinstance(data["errors"], list):
                evidence["errors"].extend([str(e) for e in data["errors"]])
            files = data.get("files", {})
            if isinstance(files, dict):
                for _, fdata in files.items():
                    if isinstance(fdata, dict):
                        if fdata.get("chunk_paths"):
                            evidence["chunks"].extend(fdata.get("chunk_paths") or [])

    for log_path in logs:
        evidence["logs"].append(str(log_path))

    out_dir = Path(".pipeline") / "research" / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    return evidence
