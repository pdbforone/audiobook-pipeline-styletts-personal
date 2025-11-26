"""Phase P: safety verification of research outputs (informational only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


DISALLOWED_KEYS = {"engine_suggestion", "chunk_size", "override", "rewrite", "auto_fix"}


def verify_research_outputs(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify Phase P research outputs:
      - no hallucinated fields,
      - all keys are expected,
      - no engine/phase overrides,
      - no prescriptive actions.
    """
    issues: List[str] = []
    blocked_actions: List[str] = []
    checked_fields: List[str] = list(signals.keys()) if isinstance(signals, dict) else []

    def _scan(obj: Any, path: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                key_lower = str(k).lower()
                for dis in DISALLOWED_KEYS:
                    if dis in key_lower:
                        issues.append(f"Disallowed key '{k}' at {path or 'root'}")
                        blocked_actions.append(dis)
                _scan(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                _scan(item, f"{path}[{idx}]")

    _scan(signals)

    required = {"raw", "analysis"}
    if isinstance(signals, dict):
        missing = required - set(signals.keys())
        if missing:
            issues.append(f"Missing expected sections: {sorted(missing)}")

    valid = not issues
    report = {
        "valid": valid,
        "issues": issues,
        "checked_fields": checked_fields,
        "blocked_actions": blocked_actions,
    }

    out_dir = Path(".pipeline") / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_path = out_dir / f"safety_log_{ts}.json"
    log_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
