"""
G6 verification harness.

Runs three micro-book passes through Phases 1-4, captures override diffs,
performs integrity checks, and ends with the FF7 victory fanfare.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from pipeline_common import PipelineState

ROOT = Path(".").resolve()
PIPELINE_JSON = ROOT.parent / "pipeline.json"
OVERRIDES_PATH = ROOT / ".pipeline" / "tuning_overrides.json"
BOOKS_DIR = ROOT / "g6_test_books"
DIFF_DIR = ROOT / "g6_verify_diffs"
ALLOWED_OVERRIDE_KEYS = {
    "chunk_size",
    "engine_prefs",
    "voice_stability",
    "history",
    "overrides",
    "runtime_state",
    "version",
}
PHASE4_AUDIO_DIR = ROOT / "phase4_tts" / "audio_chunks"
BOOK_ORDER = [
    ("book_simple.txt", "book_simple"),
    ("book_medium.txt", "book_medium"),
    ("book_complex.txt", "book_complex"),
]
MICRO_BOOKS = {
    "book_simple.txt": (
        "This is a simple test run. "
        "Clear words and short thoughts keep articulation crisp.\n\n"
        "The narrator should sound calm and stable throughout."
    ),
    "book_medium.txt": (
        "The quick brown fox jumps over the lazy dog, yet the sentence continues, "
        "adding commas, clauses, and pauses to exercise moderate linguistic flow.\n\n"
        "A second paragraph mixes cadence shifts and punctuation diversity."
    ),
    "book_complex.txt": (
        "Adaptive text-to-speech pipelines juggle acoustics, pacing, and semantics "
        "while obeying tight latency budgets.\n\n"
        "Advisor heuristics and tuning overrides should remain calm during this "
        "micro-run, nudging chunk sizes without overreacting."
    ),
}


def reset_overrides() -> None:
    overrides_path = OVERRIDES_PATH
    overrides_path.parent.mkdir(parents=True, exist_ok=True)
    if overrides_path.exists():
        overrides_path.unlink()
    overrides_path.write_text(
        json.dumps({"chunk_size": {}, "engine_prefs": {}, "voice_stability": {}}, indent=2),
        encoding="utf-8",
    )


def prepare_dirs() -> None:
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    if DIFF_DIR.exists():
        shutil.rmtree(DIFF_DIR)
    DIFF_DIR.mkdir(parents=True, exist_ok=True)


def write_micro_books() -> Dict[str, Path]:
    mapping: Dict[str, Path] = {}
    for name, text in MICRO_BOOKS.items():
        book_path = BOOKS_DIR / name
        book_path.write_text(text.strip() + "\n", encoding="utf-8")
        mapping[name] = book_path
    return mapping


def load_overrides() -> Dict[str, Any]:
    try:
        return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def diff_overrides(before: Dict[str, Any], after: Dict[str, Any]) -> str:
    before_lines = json.dumps(before, indent=2, sort_keys=True).splitlines()
    after_lines = json.dumps(after, indent=2, sort_keys=True).splitlines()
    return "\n".join(
        difflib.unified_diff(before_lines, after_lines, fromfile="before", tofile="after", lineterm="")
    )


def run_orchestrator(book_path: Path, run_id: int) -> Dict[str, Any]:
    print(f"\n=== Running pipeline for: {book_path.name} ===")
    cmd = [
        sys.executable,
        "-m",
        "phase6_orchestrator.orchestrator",
        str(book_path),
        "--no-resume",
        "--phases",
        "1",
        "2",
        "3",
        "4",
    ]
    env = os.environ.copy()
    current_py_path = env.get("PYTHONPATH", "")
    repo_path = str(ROOT)
    if current_py_path:
        env["PYTHONPATH"] = f"{repo_path}{os.pathsep}{current_py_path}"
    else:
        env["PYTHONPATH"] = repo_path
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    stdout = result.stdout
    stderr = result.stderr
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Run {run_id} for {book_path.name} failed (exit {result.returncode})")
    combined_output = "\n".join(part for part in (stdout, stderr) if part)
    advisor_lines = [
        line.strip()
        for line in combined_output.splitlines()
        if "Policy " in line or "advisor" in line.lower()
    ]
    rtf_match = re.findall(r"RT avg ([0-9.]+)x", combined_output)
    rtf_value = float(rtf_match[-1]) if rtf_match else None
    return {
        "book": book_path.stem,
        "stdout": stdout,
        "advisor_lines": advisor_lines,
        "rtf": rtf_value,
    }


def extract_chunk_delta(data: Dict[str, Any]) -> Any:
    try:
        return (
            data["overrides"]["phase3"]["chunk_size"]["delta_percent"]
            if isinstance(data.get("overrides"), dict)
            else None
        )
    except (KeyError, TypeError):
        return None


def extract_voice_streak(data: Dict[str, Any]) -> Any:
    try:
        return data["runtime_state"]["voice_success_streak"]
    except (KeyError, TypeError):
        return None


def perform_integrity_checks(book_stems: Sequence[str]) -> List[str]:
    anomalies: List[str] = []
    try:
        state = PipelineState(PIPELINE_JSON, validate_on_read=True)
        pipeline_data = state.read()
    except Exception as exc:
        anomalies.append(f"pipeline.json validation failed: {exc}")
        pipeline_data = {}

    log_dir = ROOT / ".pipeline" / "policy_logs"
    log_files = list(log_dir.glob("*.log"))
    if not log_files:
        anomalies.append("No policy log files found under .pipeline/policy_logs")

    overrides = load_overrides()
    extra_keys = set(overrides.keys()) - ALLOWED_OVERRIDE_KEYS
    if extra_keys:
        anomalies.append(f"Tuning overrides contain unexpected keys: {sorted(extra_keys)}")

    phase4_entries = (
        pipeline_data.get("phase4", {}).get("files", {}) if isinstance(pipeline_data, dict) else {}
    )
    for stem in book_stems:
        entry = phase4_entries.get(stem)
        if not isinstance(entry, dict):
            anomalies.append(f"No Phase 4 entry recorded for {stem}")
            continue
        chunk_paths = entry.get("chunk_audio_paths") or entry.get("artifacts", {}).get("chunk_audio_paths")
        if not chunk_paths:
            anomalies.append(f"No chunk_audio_paths stored for {stem}")
            continue
        missing = [
            path
            for path in chunk_paths
            if not Path(path).expanduser().resolve().exists()
        ]
        if missing:
            anomalies.append(f"Missing Phase 4 audio files for {stem}: {missing}")
    return anomalies


def save_diff(run_index: int, diff_text: str) -> None:
    target = DIFF_DIR / f"diff_run{run_index}.txt"
    target.write_text(diff_text + ("\n" if diff_text and not diff_text.endswith("\n") else ""), encoding="utf-8")


def play_victory_fanfare() -> None:
    try:
        import winsound

        melody = [
            (784, 250),
            (880, 250),
            (988, 300),
            (784, 250),
            (880, 250),
            (988, 300),
            (1319, 400),
        ]
        for freq, duration in melody:
            winsound.Beep(freq, duration)
        winsound.Beep(1175, 450)
    except Exception:
        print("Victory fanfare: please imagine the FF7 theme (audio unavailable).")


def main() -> None:
    prepare_dirs()
    reset_overrides()
    write_micro_books()

    report: List[Dict[str, Any]] = []

    for idx, (filename, file_id) in enumerate(BOOK_ORDER, start=1):
        before = load_overrides()
        run_info = run_orchestrator(BOOKS_DIR / filename, idx)
        after = load_overrides()
        diff_text = diff_overrides(before, after)
        label = f"After Run {idx}"
        print(f"\n=== DIFF - {label} ===")
        print(diff_text or "<no changes>")
        save_diff(idx, diff_text or "<no changes>\n")
        run_info["chunk_delta"] = extract_chunk_delta(after)
        run_info["voice_streak"] = extract_voice_streak(after)
        report.append(run_info)

    anomalies = perform_integrity_checks([stem for _, stem in BOOK_ORDER])

    rtf_summary = ", ".join(
        f"{entry['book']}: {entry['rtf']:.2f}x" if entry.get("rtf") else f"{entry['book']}: n/a"
        for entry in report
    )
    delta_summary = ", ".join(
        f"{entry['book']}: {entry.get('chunk_delta')}" for entry in report
    )
    advisor_signals = set()
    for entry in report:
        advisor_signals.update(entry.get("advisor_lines", []))

    print("\n=== Integrity Summary ===")
    print("G6 verification complete")
    print(f"RTF trajectory: {rtf_summary}")
    print(f"Override delta trajectory: {delta_summary}")
    if advisor_signals:
        print("Advisor signals observed:")
        for line in sorted(advisor_signals):
            print(f"  - {line}")
    else:
        print("Advisor signals observed: none")

    if anomalies:
        print("Anomalies detected:")
        for item in anomalies:
            print(f"  - {item}")
    else:
        print("Anomalies detected: none")

    play_victory_fanfare()
    print("Check g6_verify_diffs/ and .pipeline/policy_logs/ for validation.")


if __name__ == "__main__":
    main()
