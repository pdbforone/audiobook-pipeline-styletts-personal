"""
Generate a short XTTS demo for every locally available voice.

Outputs one WAV per voice under the specified output directory.
Built-in XTTS voices use the `speaker` parameter; custom clones use `speaker_wav`
from the voice_references.json config. Only local (no URL) references are used.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import soundfile as sf
from TTS.api import TTS

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_references.json"
DEFAULT_TEXT = (
    "This is a short narration snippet for voice evaluation. "
    "The goal is to check pronunciation, pacing, and warmth."
)

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> Dict:
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_voices(config: Dict) -> Tuple[List[str], Dict[str, Path]]:
    """Return (xtts_speakers, clone_map[voice_id -> reference_path])."""
    built_in = config.get("built_in_voices", {}).get("xtts", {}) or {}
    xtts_speakers = sorted(built_in.keys())

    clones = {}
    for voice_id, entry in (config.get("voice_references", {}) or {}).items():
        local_path = entry.get("local_path")
        if not local_path:
            continue
        ref_path = (ROOT / local_path).resolve()
        if ref_path.exists():
            clones[voice_id] = ref_path
        else:
            logger.warning(
                "Skipping %s (missing reference: %s)", voice_id, ref_path
            )

    return xtts_speakers, clones


def synthesize_with_xtts(
    model: TTS,
    text: str,
    speaker: str | None = None,
    speaker_wav: Path | None = None,
) -> np.ndarray:
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


def synthesize_with_multi_speaker(
    model: TTS, text: str, speaker: str
) -> np.ndarray:
    wav = model.tts(text=text, speaker=speaker, language="en")
    audio = np.array(wav, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=0)
    peak = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
    if peak > 0:
        audio = audio / peak * 0.95
    return audio


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate XTTS demos for all voices"
    )
    parser.add_argument(
        "--text-file",
        type=Path,
        help="Path to text file to read. Defaults to built-in sample text.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "voice_tests" / "output",
        help="Directory to write WAV files (default: voice_tests/output)",
    )
    parser.add_argument(
        "--multi-speaker-model",
        default="tts_models/en/vctk/vits",
        help="Coqui model with built-in multi-speaker support for named voices.",
    )
    parser.add_argument(
        "--max-speakers",
        type=int,
        default=12,
        help="Limit number of built-in speakers synthesized (avoid 100+ VCTK speakers).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    text = DEFAULT_TEXT
    if args.text_file and args.text_file.exists():
        text = (
            args.text_file.read_text(encoding="utf-8").strip() or DEFAULT_TEXT
        )

    config = load_config(CONFIG_PATH)
    xtts_speakers, clones = collect_voices(config)

    logger.info("XTTS built-in voices (config labels): %s", xtts_speakers)
    logger.info("Custom clones (local refs): %s", list(clones.keys()))

    args.out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading XTTS model once for clone synthesis...")
    model = TTS(
        model_name="tts_models/multilingual/multi-dataset/xtts_v2",
        progress_bar=False,
        gpu=False,
    )

    # Built-in voices
    # Built-in names (using a true multi-speaker model)
    try:
        ms_model = TTS(
            model_name=args.multi_speaker_model,
            progress_bar=False,
            gpu=False,
        )
        ms_speakers = list(ms_model.speakers or [])
        if args.max_speakers and len(ms_speakers) > args.max_speakers:
            ms_speakers = ms_speakers[: args.max_speakers]
        logger.info(
            "Multi-speaker model %s speakers (capped to %d): %s",
            args.multi_speaker_model,
            len(ms_speakers),
            ms_speakers,
        )
        for speaker in ms_speakers:
            try:
                audio = synthesize_with_multi_speaker(
                    ms_model, text, speaker=speaker
                )
                out_path = args.out_dir / f"builtin_{speaker}.wav"
                sf.write(
                    out_path, audio, ms_model.synthesizer.output_sample_rate
                )
                logger.info("Wrote %s", out_path)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed built-in speaker %s: %s", speaker, exc)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Failed to load multi-speaker model %s: %s",
            args.multi_speaker_model,
            exc,
        )

    # Custom clones (XTTS cloning)
    for voice_id, ref_path in clones.items():
        try:
            audio = synthesize_with_xtts(model, text, speaker_wav=ref_path)
            out_path = args.out_dir / f"clone_{voice_id}.wav"
            sf.write(out_path, audio, 24000)
            logger.info("Wrote %s", out_path)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed clone %s: %s", voice_id, exc)

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
