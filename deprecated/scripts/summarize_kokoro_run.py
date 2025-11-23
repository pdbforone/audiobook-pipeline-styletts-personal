"""
Summarize the most recent Kokoro run into a single JSON + console report.

Usage:
    python scripts/summarize_kokoro_run.py \
        --pipeline-json pipeline.json \
        --phase4-dir phase4_tts_styletts/audio_chunks \
        --phase5-dir phase5_enhancement/processed
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize Kokoro run artifacts."
    )
    parser.add_argument("--pipeline-json", default="pipeline.json")
    parser.add_argument(
        "--phase4-dir", default="phase4_tts_styletts/audio_chunks"
    )
    parser.add_argument("--phase5-dir", default="phase5_enhancement/processed")
    parser.add_argument("--output", default="run_summary.json")
    parser.add_argument(
        "--qa",
        action="store_true",
        help="Run optional QA checks (RMS/peak, WER sample)",
    )
    parser.add_argument(
        "--wer-model",
        default="tiny.en",
        help="Whisper/Faster-Whisper model size",
    )
    parser.add_argument(
        "--wer-sample-index",
        type=int,
        default=0,
        help="Chunk index to use for WER sample",
    )
    return parser.parse_args()


def load_pipeline(pipeline_path: Path) -> Dict:
    if not pipeline_path.exists():
        raise FileNotFoundError(f"pipeline.json not found at {pipeline_path}")
    with pipeline_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_phase_statuses(data: Dict) -> Dict[str, Dict]:
    summary = {}
    for idx in range(1, 6):
        phase_key = f"phase{idx}"
        phase_data = data.get(phase_key, {})
        summary[phase_key] = {
            "status": phase_data.get("status", "pending"),
            "metadata": {
                k: v
                for k, v in phase_data.items()
                if k not in {"files", "status"}
            },
        }
    return summary


def load_kokoro_meta(phase4_dir: Path) -> Optional[Dict]:
    meta_path = phase4_dir / "kokoro_run_meta.json"
    if not meta_path.exists():
        return None
    with meta_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def locate_audiobook(phase5_dir: Path) -> Optional[str]:
    if not phase5_dir.exists():
        return None
    mp3s = sorted(
        phase5_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return str(mp3s[0]) if mp3s else None


def compute_audio_stats(files: List[Dict]) -> List[Dict]:
    stats = []
    for entry in files:
        path = Path(entry["path"])
        if not path.exists():
            stats.append({"path": str(path), "error": "missing"})
            continue
        audio, _ = sf.read(path)
        if audio.size == 0:
            stats.append({"path": str(path), "error": "empty"})
            continue
        rms = float(np.sqrt(np.mean(audio**2)) + 1e-12)
        peak = float(np.max(np.abs(audio)) + 1e-12)
        stats.append(
            {
                "path": str(path),
                "rms_db": 20 * math.log10(rms),
                "peak_db": 20 * math.log10(peak),
            }
        )
    return stats


def run_wer_sample(
    pipeline_data: Dict,
    chunk_index: int,
    phase4_dir: Path,
    model_name: str,
) -> Optional[Dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {"error": "faster_whisper not installed"}

    try:
        from jiwer import wer
    except ImportError:
        return {"error": "jiwer not installed"}

    phase3_files = pipeline_data.get("phase3", {}).get("files", {})
    if not phase3_files:
        return {"error": "No phase3 data found"}

    file_id, details = next(iter(phase3_files.items()))
    chunk_paths: List[str] = details.get("chunk_paths", [])
    if not chunk_paths:
        return {"error": "No chunk paths for phase3"}

    idx = max(0, min(chunk_index, len(chunk_paths) - 1))
    reference_text = Path(chunk_paths[idx]).read_text(encoding="utf-8").strip()

    chunk_name = Path(chunk_paths[idx]).stem  # e.g., chunk_001
    candidate_audio = (
        phase4_dir / f"{file_id}_chunk_{chunk_name.split('_')[-1]}.wav"
    )
    if not candidate_audio.exists():
        return {"error": f"Audio chunk missing: {candidate_audio}"}

    model = WhisperModel(model_name, device="cpu")
    segments, _ = model.transcribe(str(candidate_audio), beam_size=5)
    transcription = " ".join(seg.text.strip() for seg in segments).strip()

    score = float(wer(reference_text.lower(), transcription.lower()))
    return {
        "file_id": file_id,
        "chunk_index": idx,
        "reference_text": reference_text,
        "transcription": transcription,
        "wer": score,
    }


def main() -> None:
    args = parse_args()
    repo_root = Path(".").resolve()
    pipeline_path = (repo_root / args.pipeline_json).resolve()
    phase4_dir = (repo_root / args.phase4_dir).resolve()
    phase5_dir = (repo_root / args.phase5_dir).resolve()

    pipeline_data = load_pipeline(pipeline_path)
    phase_statuses = extract_phase_statuses(pipeline_data)
    kokoro_meta = load_kokoro_meta(phase4_dir)
    audiobook_path = locate_audiobook(phase5_dir)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_json": str(pipeline_path),
        "phase_statuses": phase_statuses,
        "kokoro": kokoro_meta or {"error": "kokoro_run_meta.json not found"},
        "audiobook_path": audiobook_path,
    }

    output_path = (repo_root / args.output).resolve()
    if kokoro_meta and "files" in kokoro_meta:
        summary["audio_stats"] = compute_audio_stats(kokoro_meta["files"])

    if args.qa:
        summary["qa"] = run_wer_sample(
            pipeline_data,
            args.wer_sample_index,
            phase4_dir,
            args.wer_model,
        )

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print(f"Run summary written to {output_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
