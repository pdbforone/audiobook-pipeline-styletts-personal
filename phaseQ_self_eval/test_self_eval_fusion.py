from phaseQ_self_eval import cross_phase_fusion


def test_fuse_phase_outputs_schema():
    fused = cross_phase_fusion.fuse_phase_outputs({})
    assert "signals" in fused and "summary" in fused
    signals = fused["signals"]
    assert set(signals.keys()) == {"phase_success", "consistency", "llm_quality", "chunk_flow"}
    for v in signals.values():
        assert 0.0 <= v <= 1.0

