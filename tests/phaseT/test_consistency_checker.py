from phaseT_consistency import consistency_checker, schema_registry


def test_consistency_checker_minimal():
    run_output = {
        "phase1": {"status": "success", "run_id": "r1"},
        "phase2": {"files": [], "run_id": "r1"},
        "phase3": {"chunks": [], "run_id": "r1"},
        "phase4": {"tts_outputs": [], "run_id": "r1"},
        "phase5": {"enhanced_outputs": [], "run_id": "r1"},
        "phase6": {"summary": {}, "run_id": "r1"},
    }
    result = consistency_checker.check_consistency(run_output, schema_registry)
    assert "schema_results" in result
    assert "cross_phase" in result
