from pathlib import Path

import numpy as np
import soundfile as sf

from phase4_tts_styletts.tts import BritishFormalNarrator

GOLDEN_TEXT = "The rain fell softly on the city, and every window glowed with quiet light."
GOLDEN_PATH = Path(__file__).with_name("data").joinpath("golden_sample.wav")
RMS_THRESHOLD = 0.02  # acceptable RMS deviation


def test_kokoro_matches_golden(tmp_path):
    assert GOLDEN_PATH.exists(), "Golden sample audio missing"

    narrator = BritishFormalNarrator(reference_audio="")
    candidate_path = tmp_path / "candidate.wav"
    narrator.synth(GOLDEN_TEXT, candidate_path)

    golden_audio, sr = sf.read(GOLDEN_PATH)
    candidate_audio, sr2 = sf.read(candidate_path)
    assert sr == sr2 == 24000
    assert golden_audio.size > 0 and candidate_audio.size > 0

    L = min(len(golden_audio), len(candidate_audio))
    diff = golden_audio[:L] - candidate_audio[:L]
    rms = float(np.sqrt(np.mean(diff**2)))
    assert rms <= RMS_THRESHOLD, f"Kokoro output drifted (RMS diff {rms:.4f} > {RMS_THRESHOLD})"
