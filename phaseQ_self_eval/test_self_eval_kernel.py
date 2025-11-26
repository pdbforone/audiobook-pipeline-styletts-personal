import os
from pathlib import Path

from phaseQ_self_eval import self_eval_kernel


def test_self_eval_kernel_outputs_schema(tmp_path, monkeypatch):
    # ensure outputs include expected keys and rating within bounds
    metrics = {"metrics": {"coherence": 0.8, "alignment": 0.7, "stability": 0.9, "efficiency": 0.6}}
    result = self_eval_kernel.evaluate_run(metrics)
    assert "dimensions" in result and "overall_rating" in result and "notes" in result
    dims = result["dimensions"]
    assert set(dims.keys()) == {"coherence", "alignment", "stability", "efficiency"}
    assert 0.0 <= result["overall_rating"] <= 1.0

