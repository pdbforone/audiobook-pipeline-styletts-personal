"""
Phase E - Benchmark Harness (opt-in)

Runs small text samples through available TTS engines (XTTS, Kokoro) and records:
- Wall time, audio duration, and real-time factor (RTF)
- Quality scores via phase4_tts/src/quality_scorer.py (if dependencies installed)
- Peak memory (psutil optional)
- Failure patterns (exceptions captured)

Results are written to:
  .pipeline/benchmark_history/YYYYMMDD.json

Configuration (opt-in):
  benchmark:
    enable: false
    test_texts:
      - "Short generic English test passage..."
      - "Another test passage for benchmarking..."

This file is safe to import and will not run the benchmark unless called explicitly.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import psutil
except ImportError:
    psutil = None

try:
    from phase4_tts.engines.engine_manager import EngineManager
except Exception as exc:  # noqa: BLE001
    raise ImportError(f"EngineManager unavailable: {exc}") from exc

try:
    from phase4_tts.engines.xtts_engine import XTTSEngine
    from phase4_tts.engines.kokoro_engine import KokoroEngine
except Exception as exc:  # noqa: BLE001
    raise ImportError(f"TTS engines unavailable: {exc}") from exc

try:
    from phase4_tts.src.quality_scorer import AudioQualityScorer
except Exception:
    AudioQualityScorer = None  # type: ignore

logger = logging.getLogger(__name__)

HISTORY_DIR = Path(".pipeline") / "benchmark_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SampleResult:
    text: str
    wall_time_sec: Optional[float]
    audio_duration_sec: Optional[float]
    rtf: Optional[float]
    quality: Optional[Dict[str, object]]
    error: Optional[str] = None


@dataclass
class EngineBenchmark:
    engine: str
    results: List[SampleResult]
    peak_mem_mb: Optional[float]
    started_at: str
    finished_at: str


class BenchmarkRunner:
    """Opt-in benchmark runner for XTTS/Kokoro."""

    def __init__(
        self,
        engines: Sequence[str] = ("xtts", "kokoro"),
        device: str = "cpu",
        history_dir: Path = HISTORY_DIR,
    ):
        self.engines = list(engines)
        self.device = device
        self.history_dir = Path(history_dir)
        self.manager = self._build_manager(device)
        self.quality_scorer = AudioQualityScorer() if AudioQualityScorer else None

    def _build_manager(self, device: str) -> EngineManager:
        """Register only XTTS and Kokoro (project-approved engines)."""
        manager = EngineManager(device=device)
        manager.register_engine("xtts", XTTSEngine)
        manager.register_engine("kokoro", KokoroEngine)
        manager.set_default_engine("xtts")
        return manager

    def _measure_peak_mem(self) -> Optional[float]:
        if not psutil:
            return None
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            return mem_info.peak_wset / (1024 * 1024) if hasattr(mem_info, "peak_wset") else mem_info.rss / (1024 * 1024)
        except Exception:
            return None

    def _write_history(self, payload: Dict[str, object]) -> Path:
        ts = datetime.utcnow().strftime("%Y%m%d")
        path = self.history_dir / f"{ts}.json"
        path.write_text(json.dumps(payload, indent=2))
        return path

    def _synthesize(
        self,
        engine_name: str,
        text: str,
    ) -> Tuple[Optional[np.ndarray], Optional[int], Optional[float], Optional[str]]:
        """Run synthesis and return audio array, sample rate, wall time, error."""
        audio = None
        sample_rate = None
        wall = None
        error = None
        try:
            start = time.perf_counter()
            audio, selected = self.manager.synthesize(
                text=text,
                reference_audio=None,
                engine=engine_name,
                language="en",
                fallback=False,
                return_engine=True,
            )
            wall = time.perf_counter() - start
            sr = self.manager.get_engine(selected).get_sample_rate()
            sample_rate = sr
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return audio, sample_rate, wall, error

    def _score_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
        text: str,
    ) -> Optional[Dict[str, object]]:
        """Score audio using AudioQualityScorer if available."""
        if not self.quality_scorer:
            return None
        try:
            tmp_path = Path(".pipeline") / "benchmark_tmp.wav"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            import soundfile as sf

            sf.write(tmp_path, audio, sample_rate)
            score = self.quality_scorer.score(tmp_path, expected_chars=len(text))
            try:
                tmp_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass
            return score.to_dict()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Quality scoring failed: %s", exc)
            return None

    def run_all_engines(
        self,
        test_texts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute benchmarks for the configured engines."""
        texts = test_texts or [
            "Short generic English test passage used for timing and quality checks.",
            "Another test passage for benchmarking the audiobook pipeline end-to-end.",
            "A slightly longer passage to approximate real audiobook phrasing and pacing.",
        ]

        engines_payload: Dict[str, Any] = {}

        for engine in self.engines:
            started = datetime.utcnow().isoformat() + "Z"
            samples: List[SampleResult] = []
            for text in texts:
                audio, sample_rate, wall, error = self._synthesize(engine, text)
                audio_dur = None
                rtf = None
                quality = None
                if audio is not None and sample_rate:
                    audio_dur = len(audio) / sample_rate
                    if wall and audio_dur:
                        rtf = wall / audio_dur
                    quality = self._score_audio(audio, sample_rate, text)
                samples.append(
                    SampleResult(
                        text=text,
                        wall_time_sec=wall,
                        audio_duration_sec=audio_dur,
                        rtf=rtf,
                        quality=quality,
                        error=error,
                    )
                )
            finished = datetime.utcnow().isoformat() + "Z"
            engines_payload[engine] = {
                "started_at": started,
                "finished_at": finished,
                "peak_mem_mb": self._measure_peak_mem(),
                "samples": [asdict(s) for s in samples],
            }

        recommendations = self._build_recommendations(engines_payload)

        payload = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "device": self.device,
            "engines": engines_payload,
            "recommendations": recommendations,
        }
        self._write_history(payload)
        return payload

    def _build_recommendations(self, engines_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Derive simple recommendations from collected data."""
        recs: Dict[str, Any] = {"chunk_size": {}, "engine_defaults": {}}

        # Choose engine with best median RTF
        best_engine = None
        best_rtf = None
        for name, data in engines_payload.items():
            rtf_values = [
                s.get("rtf")
                for s in data.get("samples", [])
                if isinstance(s, dict) and s.get("rtf") is not None
            ]
            if not rtf_values:
                continue
            median_rtf = sorted(rtf_values)[len(rtf_values) // 2]
            if best_rtf is None or median_rtf < best_rtf:
                best_rtf = median_rtf
                best_engine = name
            engines_payload[name]["median_rtf"] = median_rtf

        if best_engine:
            recs["engine_defaults"] = {
                "preferred": best_engine,
                "reason": "fastest median RTF from benchmark",
                "median_rtf": best_rtf,
            }

        # Chunk size heuristic based on fastest engine RTF
        if best_rtf is not None:
            if best_rtf > 2.5:
                recs["chunk_size"] = {"action": "reduce", "delta_percent": -10}
            elif best_rtf < 1.0:
                recs["chunk_size"] = {"action": "increase", "delta_percent": 10}
            else:
                recs["chunk_size"] = {"action": "maintain", "delta_percent": 0}

        return recs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runner = BenchmarkRunner()
    payload = runner.run_all_engines()
    logger.info("Benchmark complete. Saved results to %s", (HISTORY_DIR / f"{datetime.utcnow().strftime('%Y%m%d')}.json"))
