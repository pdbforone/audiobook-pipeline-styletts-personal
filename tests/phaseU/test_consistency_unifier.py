from phaseU_integrity import consistency_unifier


def test_consistency_unifier_schema():
    signals = {"run_id": "r1", "signals": {}}
    integrity = {"integrity_rating": 0.4, "issues": ["stability_low"]}
    out = consistency_unifier.unify(signals, integrity)
    assert out["run_id"] == "r1"
    assert "summary" in out
    assert "signals" in out
    assert "integrity" in out
    assert "integrity_rating" in out["summary"]
