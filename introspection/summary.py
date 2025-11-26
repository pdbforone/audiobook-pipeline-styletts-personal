"""
Introspection summary builder (Phase I, opt-in).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def build_introspection_summary(
    clusters: Dict[str, Any] | None,
    narrative: Dict[str, Any] | None,
    critique: Dict[str, Any] | None,
    run_id: str,
) -> Dict[str, Any]:
    """
    Assembles a consolidated introspection bundle:
    {
       "run_id": run_id,
       "clusters": clusters,
       "narrative": narrative,
       "critique": critique,
       "timestamp": ...
    }
    """
    return {
        "run_id": run_id,
        "clusters": clusters or {},
        "narrative": narrative or {},
        "critique": critique or {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
