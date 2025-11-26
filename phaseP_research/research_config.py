from dataclasses import dataclass


@dataclass
class ResearchConfig:
    enable_research: bool = False
    collect_phase_metrics: bool = False
    collect_failure_patterns: bool = False
    collect_engine_stats: bool = False
    collect_chunk_stats: bool = False
    collect_memory_signals: bool = False
    collect_policy_signals: bool = False
