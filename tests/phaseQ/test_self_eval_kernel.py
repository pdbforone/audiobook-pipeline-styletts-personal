from __future__ import annotations

from autonomy.self_eval_kernel import SelfEvalKernel


def test_self_eval_kernel_rate_and_explain():
    kernel = SelfEvalKernel()
    sei = kernel.build_input(run_summary={"speed_score": 0.9}, evaluator_summary={"audio_quality": 0.95})
    result = kernel.rate_run(sei, run_id="test_run")
    payload = kernel.to_json(result)
    assert 0.0 <= result.overall_rating <= 1.0
    assert payload["verdict"] in {"ok", "needs_attention", "critical"}
    assert "explanation" in payload
