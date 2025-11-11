from pathlib import Path

from phase4_tts_styletts.tts import BritishFormalNarrator


def test_voice_synthesis():
    out_path = Path(__file__).with_name("test_output.wav")
    if out_path.exists():
        out_path.unlink()

    narrator = BritishFormalNarrator(reference_audio="")
    narrator.synth("Philosophy begins in wonder, and ends in understanding.", out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 0
