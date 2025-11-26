from phaseU_integrity import integrity_kernel


def test_integrity_kernel_schema():
    out = integrity_kernel.evaluate_integrity({}, {}, {}, {}, {}, {}, {}, {})
    assert "integrity_rating" in out
    assert "dimensions" in out
    dims = out["dimensions"]
    assert set(dims.keys()) == {
        "readiness",
        "stability",
        "drift",
        "self_eval",
        "retrospection",
        "review",
        "audit",
    }
    assert "issues" in out
    assert "notes" in out
