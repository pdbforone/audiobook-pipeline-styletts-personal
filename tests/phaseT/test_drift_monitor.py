from phaseT_consistency import drift_monitor


def test_drift_monitor_keys(tmp_path):
    result = drift_monitor.detect_system_drift(tmp_path)
    assert {"drift_detected", "severity", "signals", "supporting_evidence"} <= set(result.keys())
