#!/usr/bin/env python3
"""
One-off utility to concatenate Phase 5 enhanced chunk WAVs into a single WAV
and optionally encode an MP3. This mirrors Phase 5's internal concat/merge
logic but is safe to run manually. It does not modify pipeline.json.

Usage (PowerShell example):
  cd <repo-root>\phase5_enhancement
  python tools\concat_enhanced_chunks.py --input-dir processed --output-wav processed\merged.wav --encode-mp3 --mp3-bitrate 128k

Notes:
- This script invokes `ffmpeg` from PATH. Do not run it unless ffmpeg is
  installed and available in your environment. Prefer running inside the
  Phase 4/5 venv or Poetry environment used by the project.
- The script writes diagnostics logs to `phase5_enhancement/logs/` on ffmpeg
  failure; it will not overwrite existing logs.
"""

from __future__ import annotations

import argparse
import logging
import os
import tempfile
import shutil
import subprocess
from pathlib import Path
import datetime
import soundfile as sf

LOG = logging.getLogger("concat_enhanced_chunks")


def extract_chunk_number_from_filename(filepath: str) -> int:
    import re

    filename = Path(filepath).name
    match = re.search(r"_chunk_(\d+)", filename)
    if match:
        return int(match.group(1))
    match = re.search(r"chunk_(\d+)", filename)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)", filename)
    if match:
        return int(match.group(1))
    return 0


def run_ffmpeg(cmd: list[str], desc: str, logs_dir: Path) -> None:
    """Run ffmpeg and raise RuntimeError with diagnostics on failure."""
    LOG.debug("Running ffmpeg: %s", " ".join(cmd))
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        pid = os.getpid()
        safe_desc = desc.replace(" ", "_").replace("/", "_")
        log_name = f"ffmpeg_failure_{safe_desc}_{timestamp}_{pid}.log"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / log_name
        stderr_lines = (result.stderr or "").splitlines()
        stderr_preview = "\n".join(stderr_lines[:200])
        try:
            with open(log_path, "w", encoding="utf-8") as fh:
                fh.write(f"FFmpeg command: {' '.join(cmd)}\n")
                fh.write(f"Exit code: {result.returncode}\n")
                fh.write("\n--- STDERR (first 200 lines) ---\n")
                fh.write(stderr_preview + "\n")
                if len(stderr_lines) > 200:
                    fh.write(
                        f"\n... (stderr truncated, total lines={len(stderr_lines)})\n"
                    )
        except Exception as e:
            LOG.warning("Failed to write ffmpeg log: %s", e)
        LOG.error(
            "FFmpeg %s failed (exit %s). See %s",
            desc,
            result.returncode,
            str(log_path),
        )
        LOG.error("FFmpeg stderr (preview): %s", stderr_preview[:3000])
        raise RuntimeError(
            f"FFmpeg {desc} failed (exit {result.returncode}). See {log_path}\n{stderr_preview[:3000]}"
        )


def find_enhanced_wavs(input_dir: Path) -> list[Path]:
    files = list(input_dir.glob("enhanced_*.wav"))
    if not files:
        # Try generic WAVs
        files = list(input_dir.glob("*.wav"))
    files = [p for p in files if p.is_file()]
    # If numeric extraction fails for many files, fall back to lexicographic
    nums = [extract_chunk_number_from_filename(str(p)) for p in files]
    if any(n > 0 for n in nums):
        files_sorted = sorted(
            files, key=lambda p: extract_chunk_number_from_filename(str(p))
        )
    else:
        files_sorted = sorted(files, key=lambda p: p.name)
    return files_sorted


def build_and_concat_batches(
    wavs: list[Path],
    out_wav: Path,
    sample_rate: int = 24000,
    crossfade_sec: float = 0.05,
    batch_size: int = 120,
    temp_root: Path | None = None,
    keep_temp: bool = False,
) -> Path:
    if temp_root is None:
        temp_root = Path(tempfile.mkdtemp(prefix="phase5_batches_"))
    else:
        temp_root = Path(temp_root)
        temp_root.mkdir(parents=True, exist_ok=True)

    logs_dir = Path(__file__).resolve().parents[1] / "logs"

    # Detect preferred audio subtype from first wav if possible
    preferred_subtype = "pcm_s16le"
    try:
        info = sf.info(str(wavs[0]))
        subtype = (info.subtype or "").lower()
        if "24" in subtype:
            preferred_subtype = "pcm_s24le"
        else:
            preferred_subtype = "pcm_s16le"
    except Exception:
        preferred_subtype = "pcm_s16le"

    batch_files = []
    try:
        # Create batch WAVs via concat demuxer
        for idx in range(0, len(wavs), batch_size):
            batch = wavs[idx : idx + batch_size]
            batch_list = temp_root / f"batch_{idx//batch_size:04d}.txt"
            batch_wav = temp_root / f"batch_{idx//batch_size:04d}.wav"
            batch_list.write_text(
                "\n".join(f"file '{p.resolve().as_posix()}'" for p in batch),
                encoding="utf-8",
            )
            # Re-encode batch pieces to a consistent format to avoid concat
            # failures when input WAVs vary in sample-format/bit-depth.
            cmd = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "warning",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(batch_list),
                "-ar",
                str(sample_rate),
                "-ac",
                "1",
                "-c:a",
                preferred_subtype,
                str(batch_wav),
            ]
            run_ffmpeg(cmd, f"batch concat {batch_wav.name}", logs_dir)
            batch_files.append(batch_wav)

        if not batch_files:
            raise RuntimeError("No batch files produced; no input WAVs")

        # Iteratively merge batches with acrossfade
        current = batch_files[0]
        for merge_idx, next_batch in enumerate(batch_files[1:], start=1):
            merged_out = temp_root / f"merged_{merge_idx:04d}.wav"
            cmd = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "warning",
                "-i",
                str(current),
                "-i",
                str(next_batch),
                "-filter_complex",
                f"[0:a][1:a]acrossfade=d={crossfade_sec}:c1=tri:c2=tri",
                "-ar",
                str(sample_rate),
                "-ac",
                "1",
                "-c:a",
                preferred_subtype,
                str(merged_out),
            ]
            run_ffmpeg(cmd, f"crossfade merge {merge_idx}", logs_dir)
            if current not in wavs:
                try:
                    current.unlink()
                except Exception:
                    pass
            current = merged_out

        # Move/convert final merged file to out_wav using ffmpeg to ensure
        # consistent sample-rate/bit-depth/mono channel layout (preserve)
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "warning",
                "-i",
                str(current),
                "-ar",
                str(sample_rate),
                "-ac",
                "1",
                "-c:a",
                preferred_subtype,
                str(out_wav),
            ]
            run_ffmpeg(cmd, f"final convert {out_wav.name}", logs_dir)
            LOG.info("Merged WAV created: %s", out_wav)
            return out_wav
        except Exception:
            # Last resort: attempt raw copy if conversion fails
            try:
                shutil.copy(current, out_wav)
                LOG.warning(
                    "Final ffmpeg convert failed; raw-copied merged file to %s",
                    out_wav,
                )
                return out_wav
            except Exception:
                raise

    finally:
        # Clean up temp_root unless caller requested to keep it
        if not keep_temp:
            try:
                for p in temp_root.glob("*"):
                    try:
                        p.unlink()
                    except Exception:
                        pass
                temp_root.rmdir()
            except Exception:
                pass


def encode_mp3_from_wav(
    wav_path: Path,
    mp3_path: Path,
    sample_rate: int = 24000,
    bitrate: str = "128k",
) -> None:
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    # Use an explicit .mp3.tmp temp suffix and specify output format so ffmpeg
    # does not reject a non-standard extension on Windows.
    temp_mp3 = mp3_path.with_suffix(".mp3.tmp")
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "warning",
        "-i",
        str(wav_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "libmp3lame",
        "-b:a",
        str(bitrate),
        "-f",
        "mp3",
        str(temp_mp3),
    ]
    run_ffmpeg(cmd, "manual final mp3 encode", logs_dir)
    shutil.move(temp_mp3, mp3_path)
    LOG.info("MP3 encoded: %s", mp3_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="Directory containing enhanced_*.wav files. If omitted, use --file-id to locate phase4_tts/audio_chunks/<file-id>",
    )
    parser.add_argument(
        "--file-id",
        type=str,
        default=None,
        help="File id folder under phase4_tts/audio_chunks to use when --input-dir is omitted",
    )
    parser.add_argument(
        "--output-wav",
        type=str,
        default=None,
        help="Path to write merged WAV (default: <input-dir>/merged.wav)",
    )
    parser.add_argument(
        "--encode-mp3",
        action="store_true",
        help="Also encode MP3 from the merged WAV",
    )
    parser.add_argument(
        "--mp3-bitrate", type=str, default="128k", help="MP3 bitrate to use"
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=None,
        help="Sample rate for final outputs (auto-detect if omitted)",
    )
    parser.add_argument(
        "--crossfade-sec",
        type=float,
        default=0.05,
        help="Crossfade seconds when merging batches",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size for concat demuxer (auto if omitted)",
    )
    parser.add_argument(
        "--temp-dir", type=str, default=None, help="Optional temp dir to use"
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary batch files (for debugging)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="If merged output exists, reuse it and skip merging",
    )
    parser.add_argument(
        "--use-pipeline-json",
        action="store_true",
        help="Use pipeline.json to obtain ordered chunk paths for the given --file-id",
    )
    parser.add_argument(
        "--pipeline-json",
        type=str,
        default=None,
        help="Path to pipeline.json to use when --use-pipeline-json is set",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="List detected enhanced WAVs and exit (dry run)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Determine repo root and Resolve input dir: use explicit --input-dir if
    # provided, otherwise try --file-id. When a file-id is provided prefer the
    # Phase 5 processed folder (phase5_enhancement/processed/<something>) if
    # present — many projects use a processed folder with human-readable names
    # (spaces) so we attempt a flexible match.
    repo_root = Path(__file__).resolve().parents[3]
    if args.input_dir:
        input_dir = Path(args.input_dir).resolve()
    else:
        # Try to resolve from --file-id or environment
        file_id = args.file_id or os.environ.get("PHASE5_FILE_ID")
        if not file_id:
            LOG.error(
                "No --input-dir provided and no --file-id/PHASE5_FILE_ID available to locate audio chunks"
            )
            return 2

        # 1) Prefer Phase 5 processed directory if available
        processed_root = repo_root / "phase5_enhancement" / "processed"
        input_dir = None
        if processed_root.exists() and processed_root.is_dir():
            # look for folder names that startwith or contain the file_id
            candidates = []
            import re

            for p in processed_root.iterdir():
                if not p.is_dir():
                    continue
                name = p.name
                # flexible matching: direct contains/startswith, underscore/dash -> space
                name_norm = name.replace("_", " ").replace("-", " ").lower()
                file_norm = file_id.replace("_", " ").replace("-", " ").lower()
                if (
                    name.startswith(file_id)
                    or file_id in name
                    or file_norm in name_norm
                    or name_norm.startswith(file_norm)
                ):
                    candidates.append(p)
                else:
                    # accept matches where leading digits match and rest is title
                    m_name = re.match(r"^(\d+)", name)
                    m_file = re.match(r"^(\d+)", file_id)
                    if (
                        m_name
                        and m_file
                        and m_name.group(1) == m_file.group(1)
                    ):
                        candidates.append(p)
            if candidates:
                # prefer exact startswith match, else first candidate
                starts = [c for c in candidates if c.name.startswith(file_id)]
                input_dir = (starts[0] if starts else candidates[0]).resolve()

        # 2) Fallback to legacy phase4 audio_chunks location
        if input_dir is None:
            legacy = repo_root / "phase4_tts" / "audio_chunks" / file_id
            if legacy.exists():
                input_dir = legacy.resolve()
            else:
                # if neither found, error
                LOG.error(
                    "Could not locate audio directory for file-id %s (checked %s and %s)",
                    file_id,
                    processed_root,
                    legacy,
                )
                return 2

    if not input_dir.exists():
        LOG.error("Input directory not found: %s", input_dir)
        return 2

    out_wav = (
        Path(args.output_wav) if args.output_wav else input_dir / "merged.wav"
    )
    out_wav = out_wav.resolve()

    wavs = find_enhanced_wavs(input_dir)
    # Dry-run: just list files and exit
    if args.list_only:
        for p in wavs:
            print(str(p))
        return 0
    # If using pipeline.json to construct order, try to load explicit chunk ordering
    if args.use_pipeline_json and args.file_id:
        try:
            pj = (
                Path(args.pipeline_json)
                if args.pipeline_json
                else Path("pipeline.json")
            )
            if pj.exists():
                import json

                data = json.loads(pj.read_text(encoding="utf-8"))
                phase4_files = data.get("phase4", {}).get("files", {})
                entry = phase4_files.get(args.file_id) or {}
                chunk_paths = (
                    entry.get("chunk_audio_paths")
                    or entry.get("artifacts", {}).get("chunk_audio_paths")
                    or []
                )
                ordered = []
                for pth in chunk_paths:
                    # pth can be absolute or relative; prefer an enhanced_{num} in input_dir
                    cand_path = None
                    try:
                        # If pipeline.json stored absolute path and file exists, use it
                        pabs = Path(pth)
                        if pabs.is_absolute() and pabs.exists():
                            cand_path = pabs
                        else:
                            # extract chunk number and look for enhanced_{num:04d}.wav in input_dir
                            num = extract_chunk_number_from_filename(str(pth))
                            if num:
                                cand = input_dir / f"enhanced_{num:04d}.wav"
                                if cand.exists():
                                    cand_path = cand
                                else:
                                    # fallback: check for original named path inside input_dir
                                    cand2 = input_dir / Path(pth).name
                                    if cand2.exists():
                                        cand_path = cand2
                            else:
                                # last resort: check for the basename in input_dir
                                cand3 = input_dir / Path(pth).name
                                if cand3.exists():
                                    cand_path = cand3
                    except Exception:
                        cand_path = None
                    if cand_path is not None:
                        ordered.append(cand_path)
                if ordered:
                    wavs = ordered
                    LOG.info(
                        "Using %d ordered enhanced WAVs from pipeline.json",
                        len(wavs),
                    )
        except Exception as e:
            LOG.warning("Failed to load pipeline.json ordering: %s", e)
    if not wavs:
        LOG.error("No enhanced WAV files found in %s", input_dir)
        return 3

    # Auto-detect sample rate from first WAV if not provided
    sample_rate = args.sample_rate
    if sample_rate is None:
        try:
            info = sf.info(str(wavs[0]))
            sample_rate = int(info.samplerate)
            LOG.info(
                "Auto-detected sample rate %d from %s", sample_rate, wavs[0]
            )
        except Exception:
            sample_rate = 24000
            LOG.warning(
                "Failed to autodetect sample rate; defaulting to %d",
                sample_rate,
            )

    # Adaptive batch size when not specified: keep commands small for many files
    batch_size = args.batch_size
    total_wavs = len(wavs)
    if batch_size is None:
        if total_wavs > 2000:
            batch_size = 40
        elif total_wavs > 1000:
            batch_size = 60
        elif total_wavs > 500:
            batch_size = 100
        elif total_wavs > 200:
            batch_size = 120
        else:
            batch_size = 200
        LOG.info(
            "Adaptive batch_size chosen: %d for %d files",
            batch_size,
            total_wavs,
        )

    LOG.info("Found %d enhanced WAVs; merging into %s", total_wavs, out_wav)

    # Resume check: if merged exists and --resume passed, try to validate and reuse
    if args.resume and out_wav.exists():
        try:
            sf.info(str(out_wav))
            LOG.info(
                "Reusing existing merged WAV at %s (resume enabled)", out_wav
            )
            merged = out_wav
        except Exception:
            LOG.warning("Existing merged WAV present but invalid; re-creating")
            merged = None
    else:
        merged = None

    if merged is None:
        temp_root = Path(args.temp_dir) if args.temp_dir else None
        try:
            merged = build_and_concat_batches(
                wavs,
                out_wav,
                sample_rate=sample_rate,
                crossfade_sec=args.crossfade_sec,
                batch_size=batch_size,
                temp_root=temp_root,
                keep_temp=args.keep_temp,
            )
        except Exception as e:
            LOG.error("Merge failed: %s", e)
            return 4

    if args.encode_mp3:
        mp3_path = out_wav.parent / "audiobook.mp3"
        try:
            encode_mp3_from_wav(
                merged,
                mp3_path,
                sample_rate=sample_rate,
                bitrate=args.mp3_bitrate,
            )
        except Exception as e:
            LOG.error("MP3 encode failed: %s", e)
            return 5

        # Also copy MP3 into repository `audiobooks/<foldername>` for publishing
        try:
            audiobooks_root = repo_root / "audiobooks"
            target_dir = audiobooks_root / input_dir.name
            target_dir.mkdir(parents=True, exist_ok=True)
            # choose filename: prefer <file-id>.mp3 when available
            filename = (
                (args.file_id + ".mp3") if args.file_id else mp3_path.name
            )
            final_mp3 = target_dir / filename
            shutil.copy(mp3_path, final_mp3)
            LOG.info("Copied MP3 to audiobooks folder: %s", final_mp3)
        except Exception as e:
            LOG.warning("Failed to copy MP3 to audiobooks folder: %s", e)

    LOG.info("Done. Merged WAV: %s", merged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
