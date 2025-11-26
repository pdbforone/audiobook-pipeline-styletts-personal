from phaseT_consistency import schema_registry


def test_schemas_return_dicts():
    names = [
        "phase1_validation",
        "phase2_extraction",
        "phase3_chunking",
        "phase4_tts",
        "phase5_enhancement",
        "phase6_summary",
        "policy_overrides",
        "autonomy_signals",
        "self_eval",
        "research_patterns",
        "retro_report",
        "benchmark_history",
    ]
    for name in names:
        assert isinstance(schema_registry.get_expected_schema(name), dict)
