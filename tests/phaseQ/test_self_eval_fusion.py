from __future__ import annotations

from pathlib import Path

from autonomy.self_eval_fusion import fuse_signals_for_self_eval


class DummyState:
    def read(self, validate: bool = False):
        return {}


def test_fuse_signals_missing_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base_dir = Path(".pipeline")
    base_dir.mkdir()
    fused = fuse_signals_for_self_eval(DummyState(), "run123", base_dir=base_dir)
    assert fused.run_summary == {}
    assert fused.reward_summary == {}
