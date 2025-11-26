from phaseU_integrity import signal_hub


def test_signal_hub_schema(tmp_path):
    base = tmp_path
    out = signal_hub.collect_signals("run123", base_dir=base)
    assert out["run_id"] == "run123"
    assert "signals" in out
    signals = out["signals"]
    expected = {
        "readiness",
        "stability",
        "drift",
        "self_eval",
        "retrospection",
        "review",
        "audit",
        "planner",
        "policy_kernel",
        "engine_capabilities",
    }
    assert expected.issubset(signals.keys())
