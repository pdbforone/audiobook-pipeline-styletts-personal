"""
Create philosophy paragraph samples for all selectable XTTS voices.

This script loads `configs/voice_references.json`, finds built-in XTTS
speakers and any locally-available custom clones, and synthesizes a short
paragraph of philosophy for each voice. Output WAVs are written to
`phase4_tts/voice_tests/philosophy_samples/` by default.

Usage:
  python create_xtts_philosophy_samples.py --out-dir ../voice_tests/philosophy_samples

Note: This uses Coqui TTS models (same approach as other tools). If you
don't have the `TTS` package or the models downloaded, the script will
attempt to load them and may perform downloads on first run.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import soundfile as sf
from TTS.api import TTS

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_references.json"
DEFAULT_TEXT = (
    "Philosophy seeks to understand the most fundamental aspects of reality, "
    "the nature of knowledge, and the principles that guide human life. "
    "A clear, careful voice can make complex arguments feel accessible, "
    "revealing the structure and implications of ideas."
)


def load_config(config_path: Path) -> Dict:
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_xtts_voices(config: Dict) -> List[str]:
    built_in = config.get("built_in_voices", {}).get("xtts", {}) or {}
    return sorted(built_in.keys())


def collect_local_clones(config: Dict) -> Dict[str, Path]:
    clones = {}
    for voice_id, entry in (config.get("voice_references", {}) or {}).items():
        local_path = entry.get("local_path")
        if not local_path:
            continue
        ref_path = (ROOT / local_path).resolve()
        if ref_path.exists():
            clones[voice_id] = ref_path
        else:
            logging.warning("Skipping clone '%s' (missing reference: %s)", voice_id, ref_path)
    return clones


def synthesize_with_xtts(model: TTS, text: str, speaker: str | None = None, speaker_wav: Path | None = None):
    wav = model.tts(
        text=text,
        language="en",
        speaker=speaker if speaker_wav is None else None,
        speaker_wav=str(speaker_wav) if speaker_wav is not None else None,
    )
    audio = np.array(wav, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=0)
    peak = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
    if peak > 0:
        audio = audio / peak * 0.95
    return audio


def main() -> int:
    parser = argparse.ArgumentParser(description="Create philosophy samples for XTTS voices")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "voice_tests" / "philosophy_samples")
    parser.add_argument("--text-file", type=Path, help="Optional text file to use instead of default paragraph")
    parser.add_argument("--max-builtins", type=int, default=0, help="Limit number of built-in speakers to synthesize (0 = all)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    text = DEFAULT_TEXT
    if args.text_file and args.text_file.exists():
        text = args.text_file.read_text(encoding="utf-8").strip() or DEFAULT_TEXT

    config = load_config(CONFIG_PATH)
    builtins = collect_xtts_voices(config)
    clones = collect_local_clones(config)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Loading XTTS base model for cloning synthesis...")
    try:
        model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False, gpu=False)
    except Exception as exc:
        logging.error("Failed to load XTTS model: %s", exc)
        return 2

    # If there are many built-ins, optionally cap them
    builtin_targets = builtins if args.max_builtins <= 0 else builtins[: args.max_builtins]

    # For built-in speakers we attempt to use a multi-speaker vits model that exposes named speakers
    # Fallback: try to synthesize using XTTS 'speaker' param directly
    try:
        ms_model = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False, gpu=False)
        ms_speakers = list(ms_model.speakers or [])
        logging.info("Multi-speaker model loaded with %d speakers (cap %d)", len(ms_speakers), len(builtin_targets))
    except Exception:
        ms_model = None
        ms_speakers = []
        logging.warning("Multi-speaker model not available; falling back to XTTS speaker param for built-ins.")

    # Built-in voices
    if ms_model and ms_speakers:
        # Try to match config names to available ms_speakers when reasonable, otherwise synthesize a subset
        for name in builtin_targets:
            # Attempt to find a speaker with matching substring (case-insensitive)
            match = None
            for s in ms_speakers:
                if name.lower().split()[0] in s.lower() or s.lower() in name.lower():
                    match = s
                    break
            target = match or (ms_speakers[0] if ms_speakers else None)
            try:
                audio = synthesize_with_xtts(ms_model, text, speaker=target)
                out_path = args.out_dir / f"builtin_{name.replace(' ', '_')}.wav"
                sf.write(out_path, audio, ms_model.synthesizer.output_sample_rate)
                logging.info("Wrote built-in sample %s (ms_speaker=%s)", out_path, target)
            except Exception as exc:
                logging.error("Failed built-in %s via multi-speaker model: %s", name, exc)
    else:
        # Use XTTS model speaker arg directly
        for name in builtin_targets:
            try:
                audio = synthesize_with_xtts(model, text, speaker=name)
                out_path = args.out_dir / f"builtin_{name.replace(' ', '_')}.wav"
                sf.write(out_path, audio, 24000)
                logging.info("Wrote built-in sample %s", out_path)
            except Exception as exc:
                logging.error("Failed built-in %s with XTTS model: %s", name, exc)

    # Custom clones (local references)
    for voice_id, ref_path in clones.items():
        try:
            audio = synthesize_with_xtts(model, text, speaker_wav=ref_path)
            out_path = args.out_dir / f"clone_{voice_id}.wav"
            sf.write(out_path, audio, 24000)
            logging.info("Wrote clone sample %s", out_path)
        except Exception as exc:
            logging.error("Failed clone %s: %s", voice_id, exc)

    logging.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
