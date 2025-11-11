import numpy as np
import soundfile as sf
from phase4_tts_styletts import tts


class DummyModel:
    def __init__(self):
        self._style = np.zeros((1, 256), dtype=np.float32)

    def compute_style(self, _):
        return self._style

    def inference(self, **_kwargs):
        return np.linspace(-0.5, 0.5, 2400, dtype=np.float32)


def test_synth_writes_audio(tmp_path, monkeypatch):
    ref_path = tmp_path / "ref.wav"
    sf.write(ref_path, np.ones(2400, dtype=np.float32) * 0.01, 24000)

    monkeypatch.setattr(tts, "_load_styletts2", lambda model: DummyModel())

    narrator = tts.BritishFormalNarrator(reference_audio=ref_path)
    out_file = tmp_path / "speech.wav"
    narrator.synth("Hello world", out_file)

    audio, sr = sf.read(out_file)
    assert sr == 24000
    assert audio.size > 0
