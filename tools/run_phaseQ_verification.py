import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phaseQ_self_eval.self_eval_kernel import evaluate_run, score_dimensions, generate_overall_rating
from phaseQ_self_eval.cross_phase_fusion import fuse_phase_outputs
from phaseQ_self_eval.rating_explainer import explain_rating
from phaseQ_self_eval.self_eval_reporter import write_self_eval_report


def main() -> None:
    dummy_run = {"phase1": "success"}
    dims = score_dimensions(dummy_run)
    overall = generate_overall_rating(dims)
    fused = fuse_phase_outputs({"phase_outputs": dummy_run})
    explanation = explain_rating(dims, overall)
    path = write_self_eval_report("phaseQ_synthetic_run", {"dimensions": dims, "overall_rating": overall}, overall, fused, explanation)
    print("PHASE Q VERIFICATION COMPLETE")
    print("Report written:", path)


if __name__ == "__main__":
    main()
