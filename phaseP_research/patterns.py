"""Phase P: pattern extraction (lightweight, opt-in)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from collections import Counter


def extract_patterns(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts normalized evidence and returns a structured pattern summary.
    """
    phases = evidence.get("phases", {}) if isinstance(evidence, dict) else {}
    errors = evidence.get("errors", []) if isinstance(evidence, dict) else []
    chunks = evidence.get("chunks", []) if isinstance(evidence, dict) else []

    phase_failures = {k: v.get("status") for k, v in phases.items() if isinstance(v, dict)}
    engine_stats: Dict[str, int] = {}
    chunk_stats = {
        "count": len(chunks),
    }
    rtf_correlations: Dict[str, Any] = {}

    error_counts = Counter([str(e) for e in errors])

    patterns = {
        "timestamp": datetime.utcnow().isoformat(),
        "patterns": {
            "phase_failures": phase_failures,
            "engine_stats": engine_stats,
            "chunk_stats": chunk_stats,
            "rtf_correlations": rtf_correlations,
            "errors": dict(error_counts),
        },
        "notes": "Observational patterns only; no prescriptive actions.",
    }

    out_dir = Path(".pipeline") / "research" / "patterns"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(patterns, indent=2), encoding="utf-8")
    return patterns
