"""
Phase G6 self-tuning experiment runner.

Creates three micro-books of varying complexity, resets tuning overrides,
runs the orchestrator three times, and prints diffs after each run.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import difflib


ROOT = pathlib.Path(".").resolve()
BOOKS_DIR = ROOT / "test_books"
BOOKS_DIR.mkdir(exist_ok=True)

BOOKS = {
    "book_simple.txt": (
        "This is a simple test. It has easy sentences. Testing clarity."
    ),
    "book_medium.txt": (
        "The quick brown fox jumps over the lazy dog.\n"
        "This contains moderate structure, punctuation,\n"
        "and slightly longer sentences for chunking tests."
    ),
    "book_complex.txt": (
        "In a world where computational acoustics intersect with "
        "narrative structure, adaptive text-to-speech models attempt "
        "to regulate prosodic variance while maintaining semantic integrity.\n"
        "This should trigger different advisor signals."
    ),
}


def write_books() -> None:
    for name, text in BOOKS.items():
        (BOOKS_DIR / name).write_text(text.strip(), encoding="utf-8")


def run_pipeline(book_path: pathlib.Path) -> int:
    print(f"\n=== Running pipeline for: {book_path.name} ===")
    cmd = [
        "python",
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"Run for {book_path.name} failed with exit code {result.returncode}")
    return result.returncode


def diff_json(before: dict, after: dict, label: str) -> None:
    before_lines = json.dumps(before, indent=2, sort_keys=True).splitlines()
    after_lines = json.dumps(after, indent=2, sort_keys=True).splitlines()
    print(f"\n=== DIFF - {label} ===")
    for line in difflib.unified_diff(before_lines, after_lines, lineterm=""):
        print(line)


def load_overrides(overrides_path: pathlib.Path) -> dict:
    try:
        return json.loads(overrides_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def main() -> None:
    write_books()
    print("[OK] Created test books in:", BOOKS_DIR)

    overrides_path = ROOT / ".pipeline" / "tuning_overrides.json"
    overrides_path.parent.mkdir(exist_ok=True)
    overrides_path.write_text("{}", encoding="utf-8")
    print("[OK] Reset tuning_overrides.json")

    def load() -> dict:
        return load_overrides(overrides_path)

    before1 = load()
    run_pipeline(BOOKS_DIR / "book_simple.txt")
    after1 = load()
    diff_json(before1, after1, "After Run 1 (Baseline)")

    before2 = load()
    run_pipeline(BOOKS_DIR / "book_medium.txt")
    after2 = load()
    diff_json(before2, after2, "After Run 2 (Heuristic Updates)")

    before3 = load()
    run_pipeline(BOOKS_DIR / "book_complex.txt")
    after3 = load()
    diff_json(before3, after3, "After Run 3 (Self-Tuning Effects)")

    print("\n=== Phase G6 complete ===")
    print("Check policy logs in: .pipeline/policy_logs")
    print("Check updated overrides in:", overrides_path)


if __name__ == "__main__":
    main()
