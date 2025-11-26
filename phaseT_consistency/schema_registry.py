"""Schema registry for Phase T (lightweight, read-only)."""

from __future__ import annotations

from typing import Dict


_SCHEMAS: Dict[str, Dict] = {
    "phase1_validation": {"required": ["status"], "allowed": ["status", "run_id", "files"]},
    "phase2_extraction": {"required": ["files"], "allowed": ["run_id", "files", "metadata"]},
    "phase3_chunking": {"required": ["chunks"], "allowed": ["run_id", "chunks", "files"]},
    "phase4_tts": {"required": ["tts_outputs"], "allowed": ["run_id", "tts_outputs", "engine_used"]},
    "phase5_enhancement": {"required": ["enhanced_outputs"], "allowed": ["run_id", "enhanced_outputs"]},
    "phase6_summary": {"required": ["summary"], "allowed": ["summary", "run_id"]},
    "policy_overrides": {"required": [], "allowed": ["overrides", "run_id"]},
    "autonomy_signals": {"required": [], "allowed": ["signals", "mode", "run_id"]},
    "self_eval": {"required": ["dimensions", "overall_rating"], "allowed": ["dimensions", "overall_rating", "run_id", "signals"]},
    "research_patterns": {"required": [], "allowed": ["patterns", "metadata", "run_id"]},
    "retro_report": {"required": ["regressions", "root_causes"], "allowed": ["regressions", "root_causes", "runs_analyzed", "run_id"]},
    "benchmark_history": {"required": [], "allowed": ["results", "run_id"]},
}


def get_expected_schema(name: str) -> Dict:
    """Return the expected schema dict for a given name."""
    return _SCHEMAS.get(name, {})
