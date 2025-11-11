from pathlib import Path

from phase4_tts_styletts.tts import BritishFormalNarrator


def test_voice_synthesis(tmp_path: Path):
    narrator = BritishFormalNarrator(reference_audio="")
    out_path = tmp_path / "test_output.wav"

    narrator.synth(
        "Philosophy begins in wonder, and ends in understanding.",
        out_path,
    )

    assert out_path.exists()
    assert out_path.stat().st_size > 0
