"""Stubbed Chatterbox TTS class for local testing."""

class _StubModel:
    def __init__(self, device: str = "cpu", sample_rate: int = 24000):
        self.device = device
        self.sr = sample_rate

    def generate(self, *args, **kwargs):
        raise RuntimeError("ChatterboxTTS stub generate called in test context")


class ChatterboxTTS:
    """Minimal stub replicating the real API entry point."""

    @classmethod
    def from_pretrained(cls, device: str = "cpu") -> _StubModel:
        return _StubModel(device=device)
